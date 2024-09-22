# services/twilio_service.py

from twilio.rest import Client
from flask import current_app
import logging

class TwilioService:
    def __init__(self):
        self.account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
        self.auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")
        self.from_number = current_app.config.get("TWILIO_PHONE_NUMBER")
        self.client = Client(self.account_sid, self.auth_token)

    def initiate_call(self, to_number, twiml_url, status_callback_url):
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=twiml_url,
                status_callback=status_callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                record=True  # Enable recording
            )
            return call.sid
        except Exception as e:
            logging.error(f"Twilio Error initiating call to {to_number}: {str(e)}")
            raise e

    def fetch_recording_sid(self, call_sid):
        try:
            recordings = self.client.recordings.list(call_sid=call_sid)
            if recordings:
                return recordings[0].sid
            else:
                return None
        except Exception as e:
            logging.error(f"Twilio Error fetching recording for CallSid {call_sid}: {str(e)}")
            raise e
