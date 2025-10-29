import os
import logging
from celery import Celery
from celery.schedules import crontab
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
celery_app = Celery('anonvpn', broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'monitor-pending-payments': {
            'task': 'celery_worker.monitor_pending_payments',
            'schedule': crontab(minute='*/2'),  # Every 2 minutes
        },
        'check-expiring-subscriptions': {
            'task': 'celery_worker.check_expiring_subscriptions',
            'schedule': crontab(hour='9', minute='0'),  # Daily at 9:00 AM UTC
        },
    },
)

# Database configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'anonvpn')

# NOWPayments configuration
NOWPAYMENTS_API_KEY = os.environ.get('NOWPAYMENTS_API_KEY', '')
NOWPAYMENTS_API_URL = 'https://api.nowpayments.io/v1'


async def get_db():
    """Get database connection"""
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


async def check_payment_status(payment_id: str, payment_nowpayments_id: str):
    """Check payment status from NOWPayments API"""
    try:
        headers = {'x-api-key': NOWPAYMENTS_API_KEY}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f'{NOWPAYMENTS_API_URL}/payment/{payment_nowpayments_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'NOWPayments API error: {response.status_code} - {response.text}')
                return None
    except Exception as e:
        logger.error(f'Error checking payment status: {e}')
        return None


async def activate_user_subscription(user_id: str, plan_id: str, duration_days: int):
    """Activate user subscription after payment confirmation"""
    try:
        db = await get_db()
        
        # Get plan details
        plan = await db.tariff_plans.find_one({'id': plan_id}, {'_id': 0})
        if not plan:
            logger.error(f'Plan not found: {plan_id}')
            return False
        
        # Update user subscription
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
        
        result = await db.users.update_one(
            {'id': user_id},
            {
                '$set': {
                    'current_plan_id': plan_id,
                    'plan_expires_at': expires_at.isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f'User {user_id} subscription activated with plan {plan_id} until {expires_at}')
            return True
        else:
            logger.error(f'Failed to activate subscription for user {user_id}')
            return False
    except Exception as e:
        logger.error(f'Error activating user subscription: {e}')
        return False


@celery_app.task(name='celery_worker.monitor_pending_payments')
def monitor_pending_payments():
    """
    Celery task to monitor pending payments
    Runs every 2 minutes via Celery Beat
    """
    logger.info('Starting payment monitoring task...')
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_monitor_pending_payments_async())


async def _monitor_pending_payments_async():
    """Async implementation of payment monitoring"""
    try:
        db = await get_db()
        
        # Find all pending payments
        pending_payments = await db.payments.find({
            'status': {'$in': ['waiting', 'confirming', 'sending']}
        }, {'_id': 0}).to_list(1000)
        
        logger.info(f'Found {len(pending_payments)} pending payments to check')
        
        updated_count = 0
        activated_count = 0
        
        for payment in pending_payments:
            payment_id = payment.get('id')
            nowpayments_id = payment.get('payment_id')
            user_id = payment.get('user_id')
            plan_id = payment.get('plan_id')
            billing_period = payment.get('billing_period', 'monthly')
            
            if not nowpayments_id:
                logger.warning(f'Payment {payment_id} missing NOWPayments ID')
                continue
            
            # Check status from NOWPayments
            logger.info(f'Checking payment {payment_id} (NOWPayments: {nowpayments_id})')
            payment_status = await check_payment_status(payment_id, nowpayments_id)
            
            if not payment_status:
                continue
            
            new_status = payment_status.get('payment_status')
            old_status = payment.get('status')
            
            # Update payment if status changed
            if new_status and new_status != old_status:
                logger.info(f'Payment {payment_id} status changed: {old_status} -> {new_status}')
                
                await db.payments.update_one(
                    {'id': payment_id},
                    {
                        '$set': {
                            'status': new_status,
                            'updated_at': datetime.now(timezone.utc).isoformat(),
                            'nowpayments_data': payment_status
                        }
                    }
                )
                updated_count += 1
                
                # Activate subscription if payment confirmed
                if new_status in ['finished', 'confirmed']:
                    duration_days = 365 if billing_period == 'annual' else 30
                    success = await activate_user_subscription(user_id, plan_id, duration_days)
                    if success:
                        activated_count += 1
                        logger.info(f'✅ Payment {payment_id} confirmed - Subscription activated for user {user_id}')
                        
                        # TODO: Send email notification to user
                        # await send_email_notification(user_id, payment_id, plan_id)
                elif new_status in ['failed', 'expired']:
                    logger.warning(f'❌ Payment {payment_id} failed/expired')
        
        logger.info(f'Payment monitoring completed: {updated_count} updated, {activated_count} activated')
        return {
            'checked': len(pending_payments),
            'updated': updated_count,
            'activated': activated_count
        }
        
    except Exception as e:
        logger.error(f'Error in payment monitoring task: {e}')
        raise


@celery_app.task(name='celery_worker.check_single_payment')
def check_single_payment(payment_id: str):
    """
    Celery task to check a single payment status
    Can be triggered manually or via webhook
    """
    logger.info(f'Checking single payment: {payment_id}')
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_check_single_payment_async(payment_id))


async def _check_single_payment_async(payment_id: str):
    """Async implementation of single payment check"""
    try:
        db = await get_db()
        
        # Find payment
        payment = await db.payments.find_one({'id': payment_id}, {'_id': 0})
        if not payment:
            logger.error(f'Payment not found: {payment_id}')
            return {'error': 'Payment not found'}
        
        nowpayments_id = payment.get('payment_id')
        if not nowpayments_id:
            logger.error(f'Payment {payment_id} missing NOWPayments ID')
            return {'error': 'Missing NOWPayments ID'}
        
        # Check status
        payment_status = await check_payment_status(payment_id, nowpayments_id)
        if not payment_status:
            return {'error': 'Failed to check payment status'}
        
        new_status = payment_status.get('payment_status')
        old_status = payment.get('status')
        
        # Update if status changed
        if new_status and new_status != old_status:
            await db.payments.update_one(
                {'id': payment_id},
                {
                    '$set': {
                        'status': new_status,
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                        'nowpayments_data': payment_status
                    }
                }
            )
            
            # Activate subscription if confirmed
            if new_status in ['finished', 'confirmed']:
                user_id = payment.get('user_id')
                plan_id = payment.get('plan_id')
                billing_period = payment.get('billing_period', 'monthly')
                duration_days = 365 if billing_period == 'annual' else 30
                
                await activate_user_subscription(user_id, plan_id, duration_days)
                logger.info(f'✅ Payment {payment_id} confirmed via manual check')
        
        return {
            'payment_id': payment_id,
            'old_status': old_status,
            'new_status': new_status,
            'updated': new_status != old_status
        }
        
    except Exception as e:
        logger.error(f'Error checking single payment: {e}')
        raise


# Health check task
@celery_app.task(name='celery_worker.health_check')
def health_check():
    """Health check task for Celery worker"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'worker': 'anonvpn-payment-monitor'
    }


if __name__ == '__main__':
    # For testing purposes
    logger.info('Starting Celery worker for AnonVPN payment monitoring...')
    celery_app.start()
