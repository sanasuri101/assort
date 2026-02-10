"""
SMS service using Twilio.
"""

import logging
from twilio.rest import Client
from app.config import settings

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        try:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            self.from_number = settings.twilio_phone_number
        except Exception as e:
            logger.warning(f"Failed to initialize Twilio client: {e}")
            self.client = None

    async def send_confirmation(self, to_number: str, details: str):
        """Send appointment confirmation SMS."""
        if not self.client:
            logger.warning("SMS service not available (client init failed).")
            return

        body = (
            f"Valley Family Medicine Appointment Confirmed.\n"
            f"{details}\n"
            f"Please arrive 15 mins early. To reschedule, call us back."
        )

        try:
            # Twilio's async client is separate, but standard client is sync.
            # For low volume, running sync in async function blocks loop briefly.
            # Better to run in executor or use twilio's async http client.
            # Simplified: just run sync for now, it's fast enough for prototype.
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"SMS sent: {message.sid}")
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
