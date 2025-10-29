"""
Email Service using SendGrid
Handles payment confirmations and subscription notifications
"""

import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    """SendGrid email service for VPN notifications"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SENDGRID_API_KEY')
        self.sender_email = os.getenv('SENDER_EMAIL', 'noreply@anonvpn.com')
        
        if not self.api_key:
            logger.warning("SendGrid API key not configured. Email notifications disabled.")
            self.enabled = False
        else:
            self.client = SendGridAPIClient(self.api_key)
            self.enabled = True
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Internal method to send email via SendGrid"""
        if not self.enabled:
            logger.warning(f"Email sending skipped (not configured): {to_email}")
            return False
        
        try:
            message = Mail(
                from_email=self.sender_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def send_payment_confirmation(
        self,
        user_email: str,
        payment_data: dict
    ) -> bool:
        """
        Send payment confirmation email
        
        Args:
            user_email: Recipient email address
            payment_data: Dict containing payment details (amount, currency, plan_name, etc.)
        """
        subject = "✅ Payment Confirmed - AnonVPN"
        
        amount = payment_data.get('amount', 0)
        currency = payment_data.get('currency', 'USD')
        plan_name = payment_data.get('plan_name', 'VPN Plan')
        payment_id = payment_data.get('payment_id', 'N/A')
        crypto_currency = payment_data.get('crypto_currency', 'BTC')
        crypto_amount = payment_data.get('crypto_amount', 0)
        expires_at = payment_data.get('expires_at', 'N/A')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; 
                             border-bottom: 1px solid #eee; }}
                .label {{ font-weight: bold; color: #667eea; }}
                .value {{ color: #333; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
                .success-icon {{ font-size: 48px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">✅</div>
                    <h1>Payment Confirmed!</h1>
                    <p>Your VPN subscription is now active</p>
                </div>
                <div class="content">
                    <h2>Thank you for your payment!</h2>
                    <p>We've successfully received your cryptocurrency payment. Your VPN service is now active and ready to use.</p>
                    
                    <div class="details">
                        <h3>Payment Details</h3>
                        <div class="detail-row">
                            <span class="label">Plan:</span>
                            <span class="value">{plan_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Amount Paid:</span>
                            <span class="value">{crypto_amount} {crypto_currency} (${amount} {currency})</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Payment ID:</span>
                            <span class="value">{payment_id}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Valid Until:</span>
                            <span class="value">{expires_at}</span>
                        </div>
                    </div>
                    
                    <h3>What's Next?</h3>
                    <ul>
                        <li>Download your VPN configuration from the dashboard</li>
                        <li>Connect to any of our 55+ servers worldwide</li>
                        <li>Enjoy anonymous and secure browsing</li>
                    </ul>
                    
                    <p><strong>Need help?</strong> Visit our support center or create a support ticket from your dashboard.</p>
                </div>
                <div class="footer">
                    <p>AnonVPN - Anonymous VPN Service</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(user_email, subject, html_content)
    
    def send_subscription_expiry_warning(
        self,
        user_email: str,
        days_remaining: int,
        plan_name: str
    ) -> bool:
        """
        Send subscription expiry warning email
        
        Args:
            user_email: Recipient email address
            days_remaining: Number of days until subscription expires
            plan_name: Name of the current plan
        """
        subject = f"⚠️ Your VPN Subscription Expires in {days_remaining} Days"
        
        urgency_color = "#ff6b6b" if days_remaining <= 3 else "#ffa500"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {urgency_color}; color: white; padding: 30px; 
                          text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .warning-box {{ background: #fff3cd; border-left: 4px solid {urgency_color}; 
                              padding: 15px; margin: 20px 0; }}
                .cta-button {{ background: #667eea; color: white; padding: 15px 30px; 
                             text-decoration: none; border-radius: 5px; display: inline-block; 
                             margin: 20px 0; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Subscription Expiring Soon</h1>
                    <p style="font-size: 24px; font-weight: bold;">{days_remaining} Days Remaining</p>
                </div>
                <div class="content">
                    <h2>Your VPN protection is about to expire</h2>
                    
                    <div class="warning-box">
                        <p><strong>Current Plan:</strong> {plan_name}</p>
                        <p><strong>Days Remaining:</strong> {days_remaining}</p>
                        <p>Your VPN service will be deactivated when your subscription expires.</p>
                    </div>
                    
                    <h3>Why Renew Now?</h3>
                    <ul>
                        <li>✅ Uninterrupted VPN protection</li>
                        <li>✅ Maintain access to all premium features</li>
                        <li>✅ Continue using your saved server configurations</li>
                        <li>✅ 10% crypto discount on all plans</li>
                    </ul>
                    
                    <div style="text-align: center;">
                        <a href="https://anonvpn.com/dashboard/payments" class="cta-button">
                            Renew Subscription Now
                        </a>
                    </div>
                    
                    <p style="margin-top: 30px; color: #666;">
                        <strong>Need a different plan?</strong> Upgrade or downgrade anytime from your dashboard.
                    </p>
                </div>
                <div class="footer">
                    <p>AnonVPN - Anonymous VPN Service</p>
                    <p>This is an automated reminder. You can disable these notifications in your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(user_email, subject, html_content)
    
    def send_subscription_expired(
        self,
        user_email: str,
        plan_name: str
    ) -> bool:
        """
        Send subscription expired notification
        
        Args:
            user_email: Recipient email address
            plan_name: Name of the expired plan
        """
        subject = "❌ Your VPN Subscription Has Expired"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 30px; 
                          text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: #fff; border: 2px solid #dc3545; 
                           padding: 15px; margin: 20px 0; border-radius: 8px; }}
                .cta-button {{ background: #28a745; color: white; padding: 15px 30px; 
                             text-decoration: none; border-radius: 5px; display: inline-block; 
                             margin: 20px 0; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Subscription Expired</h1>
                    <p>Your VPN service has been deactivated</p>
                </div>
                <div class="content">
                    <div class="info-box">
                        <p><strong>Expired Plan:</strong> {plan_name}</p>
                        <p><strong>Status:</strong> Inactive</p>
                        <p>Your VPN connections have been disabled due to subscription expiration.</p>
                    </div>
                    
                    <h3>Reactivate Your VPN Protection</h3>
                    <p>Continue enjoying secure and anonymous browsing by renewing your subscription today.</p>
                    
                    <ul>
                        <li>🔒 Military-grade encryption</li>
                        <li>🌍 55+ servers worldwide</li>
                        <li>🚀 Unlimited bandwidth</li>
                        <li>💰 10% discount with crypto payments</li>
                    </ul>
                    
                    <div style="text-align: center;">
                        <a href="https://anonvpn.com/dashboard/payments" class="cta-button">
                            Renew Now
                        </a>
                    </div>
                    
                    <p style="margin-top: 30px; color: #666;">
                        <strong>Questions?</strong> Our support team is here to help. Contact us anytime.
                    </p>
                </div>
                <div class="footer">
                    <p>AnonVPN - Anonymous VPN Service</p>
                    <p>This is an automated notification.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(user_email, subject, html_content)


# Global email service instance
email_service = EmailService()
