"""
Telegram Service for Support Ticket Notifications
Sends notifications when support tickets are created or updated
"""

import os
import logging
from typing import Optional, List
import telegram
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram bot service for support ticket notifications"""
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not self.bot_token:
            logger.warning("Telegram bot token not configured. Telegram notifications disabled.")
            self.enabled = False
            self.bot = None
        else:
            try:
                self.bot = telegram.Bot(token=self.bot_token)
                self.enabled = True
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {str(e)}")
                self.enabled = False
                self.bot = None
    
    def send_message(self, chat_id: str, message: str) -> bool:
        """
        Send a message to a Telegram chat
        
        Args:
            chat_id: Telegram chat ID
            message: Message text (supports HTML formatting)
        
        Returns:
            bool: True if message sent successfully
        """
        if not self.enabled:
            logger.warning(f"Telegram sending skipped (not configured): chat_id={chat_id}")
            return False
        
        try:
            self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=telegram.ParseMode.HTML
            )
            logger.info(f"Telegram message sent to chat_id: {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error sending message to {chat_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram message to {chat_id}: {str(e)}")
            return False
    
    def send_to_multiple_chats(self, chat_ids: List[str], message: str) -> int:
        """
        Send a message to multiple Telegram chats
        
        Args:
            chat_ids: List of Telegram chat IDs
            message: Message text
        
        Returns:
            int: Number of successful sends
        """
        if not self.enabled or not chat_ids:
            return 0
        
        success_count = 0
        for chat_id in chat_ids:
            if self.send_message(chat_id, message):
                success_count += 1
        
        return success_count
    
    def notify_new_support_ticket(
        self,
        ticket_data: dict,
        admin_chat_ids: List[str]
    ) -> int:
        """
        Send notification about new support ticket
        
        Args:
            ticket_data: Dict containing ticket details
            admin_chat_ids: List of admin Telegram chat IDs
        
        Returns:
            int: Number of successful notifications
        """
        ticket_id = ticket_data.get('id', 'N/A')
        subject = ticket_data.get('subject', 'No subject')
        priority = ticket_data.get('priority', 'medium')
        user_email = ticket_data.get('user_email', 'Unknown')
        message_preview = ticket_data.get('message', '')[:100]
        
        # Priority emoji
        priority_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }.get(priority, '⚪')
        
        message = f"""
🎫 <b>New Support Ticket</b>

{priority_emoji} <b>Priority:</b> {priority.upper()}
📧 <b>From:</b> {user_email}
🆔 <b>Ticket ID:</b> {ticket_id}
📋 <b>Subject:</b> {subject}

💬 <b>Message:</b>
{message_preview}{"..." if len(ticket_data.get('message', '')) > 100 else ""}

<i>Please respond promptly from the admin panel.</i>
        """
        
        return self.send_to_multiple_chats(admin_chat_ids, message.strip())
    
    def notify_ticket_reply(
        self,
        ticket_data: dict,
        reply_data: dict,
        admin_chat_ids: List[str]
    ) -> int:
        """
        Send notification about new reply to support ticket
        
        Args:
            ticket_data: Dict containing ticket details
            reply_data: Dict containing reply details
            admin_chat_ids: List of admin Telegram chat IDs
        
        Returns:
            int: Number of successful notifications
        """
        ticket_id = ticket_data.get('id', 'N/A')
        subject = ticket_data.get('subject', 'No subject')
        replier = reply_data.get('replied_by', 'User')
        reply_preview = reply_data.get('message', '')[:100]
        
        message = f"""
💬 <b>New Reply to Support Ticket</b>

🆔 <b>Ticket ID:</b> {ticket_id}
📋 <b>Subject:</b> {subject}
👤 <b>Replied by:</b> {replier}

💬 <b>Reply:</b>
{reply_preview}{"..." if len(reply_data.get('message', '')) > 100 else ""}

<i>View full conversation in the admin panel.</i>
        """
        
        return self.send_to_multiple_chats(admin_chat_ids, message.strip())
    
    def notify_ticket_status_change(
        self,
        ticket_data: dict,
        old_status: str,
        new_status: str,
        admin_chat_ids: List[str]
    ) -> int:
        """
        Send notification about ticket status change
        
        Args:
            ticket_data: Dict containing ticket details
            old_status: Previous status
            new_status: New status
            admin_chat_ids: List of admin Telegram chat IDs
        
        Returns:
            int: Number of successful notifications
        """
        ticket_id = ticket_data.get('id', 'N/A')
        subject = ticket_data.get('subject', 'No subject')
        
        # Status emoji
        status_emoji = {
            'open': '🟢',
            'in_progress': '🟡',
            'resolved': '✅',
            'closed': '🔒'
        }.get(new_status, '⚪')
        
        message = f"""
🔄 <b>Ticket Status Updated</b>

🆔 <b>Ticket ID:</b> {ticket_id}
📋 <b>Subject:</b> {subject}

📊 <b>Status Change:</b>
{old_status.upper()} → {status_emoji} {new_status.upper()}

<i>Check the admin panel for details.</i>
        """
        
        return self.send_to_multiple_chats(admin_chat_ids, message.strip())
    
    def test_connection(self, chat_id: str) -> dict:
        """
        Test Telegram connection
        
        Args:
            chat_id: Chat ID to test
        
        Returns:
            dict: Test result with status and message
        """
        if not self.enabled:
            return {
                'success': False,
                'message': 'Telegram bot not configured'
            }
        
        try:
            test_message = "✅ Telegram bot connection test successful!\n\nYou will receive support ticket notifications here."
            self.bot.send_message(
                chat_id=chat_id,
                text=test_message,
                parse_mode=telegram.ParseMode.HTML
            )
            return {
                'success': True,
                'message': 'Test message sent successfully'
            }
        except TelegramError as e:
            return {
                'success': False,
                'message': f'Telegram error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }


# Global telegram service instance
telegram_service = TelegramService()
