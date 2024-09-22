# blueprints/calls.py 

from flask import Blueprint, request, current_app, url_for, Response
from services.twilio_service import TwilioService
from utils.response import success_response, error_response
from bson.objectid import ObjectId
from datetime import datetime
import logging
import openai
import requests
from io import BytesIO
from twilio.twiml.voice_response import VoiceResponse  # Ensure this import is present


calls_bp = Blueprint('calls', __name__)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@calls_bp.route('/make_call/<string:record_id>', methods=['POST'])
def make_call(record_id):
    """
    Initiate a call using Twilio by passing the record ID.
    """
    try:
        # Fetch the record from MongoDB using record_id
        mongo = current_app.mongo
        champ_details = mongo.db.champ_details
        record = champ_details.find_one({"_id": ObjectId(record_id)})

        if not record:
            return error_response("Record not found", 404)

        phone_number = record.get("Number")
        name = record.get("Name", "")
        shift_timings = record.get("Shift Timings", "")
        work_description = record.get("Work Description", "")
        dress_code = record.get("Dress Code", "")
        sheet_name = record.get("sheet_name", "")

        if not phone_number:
            return error_response("Phone number not found in the record", 400)

        # Initialize Twilio Service
        twilio_service = TwilioService()

        # TwiML and Status Callback URLs using Ngrok
        ngrok_url = current_app.config.get("NGROK_URL")
        if not ngrok_url:
            return error_response("NGROK_URL is not configured in environment variables", 500)

        twiml_url = f"{ngrok_url}{url_for('calls.voice')}"
        status_callback_url = f"{ngrok_url}{url_for('calls.call_status_callback')}"

        # Initiate the call
        call_sid = twilio_service.initiate_call(
            to_number=phone_number,
            twiml_url=twiml_url,
            status_callback_url=status_callback_url
        )

        # Store call initiation data in MongoDB
        call_logs = mongo.db.call_logs
        call_log = {
            "Name": name,
            "Number": phone_number,
            "call_initiated_timestamp": datetime.utcnow(),
            "call_status": "initiated",
            "Work Description": work_description,
            "sheet_name": sheet_name,
            "call_sid": call_sid,
            "Recording SID": "",
            "Transcription_Hindi": "",
            "Transcription_English": "",
            "Intent": "",
            "future_notify_interest": "",
            "Call Start Time": "",
            "Call End Time": "",
            "Called Number": phone_number,
            "Call Date": datetime.utcnow().strftime('%Y-%m-%d'),
            "Call Duration (seconds)": 0,
            "Timestamp": datetime.utcnow()
        }
        call_logs.insert_one(call_log)

        return success_response(
            "Call initiated successfully",
            data={"record_id": record_id, "call_sid": call_sid},
            status=200
        )

    except Exception as e:
        logger.error(f"Error in make_call endpoint: {str(e)}")
        return error_response(f"An error occurred: {str(e)}", 500)

def initiate_call_from_scheduler(record_id):
    """
    Function to initiate a call using Twilio, to be called from the scheduler.
    """
    try:
        with current_app.app_context():
            # Fetch the record from MongoDB using record_id
            mongo = current_app.mongo
            champ_details = mongo.db.champ_details
            record = champ_details.find_one({"_id": ObjectId(record_id)})

            if not record:
                logger.error(f"Record not found for id: {record_id}")
                return None

            # Initiate the call (this logic is already in place)
            phone_number = record.get("Number")
            name = record.get("Name", "")
            shift_timings = record.get("Shift Timings", "")
            work_description = record.get("Work Description", "")
            dress_code = record.get("Dress Code", "")
            sheet_name = record.get("sheet_name", "")

            if not phone_number:
                logger.error(f"Phone number not found for record_id {record_id}")
                return None

            # Initialize Twilio Service
            twilio_service = TwilioService()

            # TwiML and Status Callback URLs using Ngrok
            ngrok_url = current_app.config.get("NGROK_URL")
            if not ngrok_url:
                logger.error("NGROK_URL is not configured.")
                return None

            twiml_url = f"{ngrok_url}{url_for('calls.voice')}"
            status_callback_url = f"{ngrok_url}{url_for('calls.call_status_callback')}"

            # Initiate the call via Twilio
            call_sid = twilio_service.initiate_call(
                to_number=phone_number,
                twiml_url=twiml_url,
                status_callback_url=status_callback_url
            )

            if call_sid:
                logger.info(f"Call initiated successfully for record_id {record_id}, call_sid {call_sid}")
                
                # Log call initiation in MongoDB
                call_logs = mongo.db.call_logs
                call_logs.insert_one({
                    "record_id": record_id,
                    "call_sid": call_sid,
                    "status": "initiated",
                    "initiated_at": datetime.utcnow()
                })
            else:
                logger.error(f"Failed to initiate call for record_id {record_id}")

            return call_sid

    except Exception as e:
        logger.error(f"Error initiating call for record_id {record_id}: {str(e)}")
        return None


@calls_bp.route('/voice', methods=['POST'])
def voice():
    """
    TwiML endpoint to handle call flows.
    """
    try:
        response = VoiceResponse()

        # Fetch user details based on 'To' number
        to_number = request.form.get('To', '')
        mongo = current_app.mongo
        user = mongo.db.champ_details.find_one({"Number": to_number})

        if user:
            name = user.get("Name", "")
            shift_timings = user.get("Shift Timings", "")
            work_description = user.get("Work Description", "")
            dress_code = user.get("Dress Code", "")

            # Message 1
            message1 = f"हेलो {name} मैं आपर फोर यू से अनमोर पाटक बात कर रहा हूँ और मैंने आपको कॉल किया ये जानने के लिए कि आप {shift_timings} बज़े वाली शिफ्ट में आ रहे हो या नहीं आ रहे हो"
            response.say(message1, language='hi-IN')
            response.pause(length=5)

            # Message 2
            message2 = f"{work_description} के लिए आपका ड्रेस कोड {dress_code} होगा"
            response.say(message2, language='hi-IN')
            response.pause(length=5)

            # Message 3
            message3 = "क्या आप भविष्य की शिफ्ट के बारे में सूचित होना चाहते हैं?"
            response.say(message3, language='hi-IN')
            response.pause(length=5)

            # Thank You Message
            thank_you = "ओके ओके ठीक है ठीक है थेंक्स भाई"
            response.say(thank_you, language='hi-IN')
        else:
            # If user details are not found, provide a default message
            response.say("हेलो, आपका कॉल प्राप्त हुआ। धन्यवाद!", language='hi-IN')
            response.hangup()

        return Response(str(response), mimetype='application/xml')

    except Exception as e:
        logger.error(f"Error in voice endpoint: {str(e)}")
        response = VoiceResponse()
        response.say("हमें खेद है, आपके कॉल को संभालने में समस्या आई। कृपया बाद में पुनः प्रयास करें।", language='hi-IN')
        response.hangup()
        return Response(str(response), mimetype='application/xml')


@calls_bp.route('/call_status_callback', methods=['POST'])
def call_status_callback():
    """
    Receives call status updates from Twilio and updates MongoDB accordingly.
    """
    try:
        # Extract parameters from Twilio's request
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')
        to_number = request.form.get('To')
        from_number = request.form.get('From')
        call_duration = request.form.get('CallDuration', '0')
        call_start_time = request.form.get('StartTime')
        call_end_time = request.form.get('EndTime')
        call_date = call_start_time.split('T')[0] if call_start_time else ''

        # Map Twilio call statuses to your internal statuses
        status_mapping = {
            'initiated': 'initiated',
            'ringing': 'ringing',
            'answered': 'picked',
            'busy': 'denied',
            'no-answer': 'not picked',
            'failed': 'failed',
            'completed': 'completed'
        }

        mapped_status = status_mapping.get(call_status, call_status)

        # Initialize MongoDB connection
        mongo = current_app.mongo
        call_logs = mongo.db.call_logs

        # Update the corresponding call_log in MongoDB
        update_fields = {
            "call_status": mapped_status,
            "Call Duration (seconds)": int(call_duration),
            "Call Start Time": call_start_time,
            "Call End Time": call_end_time,
            "Called Number": to_number,
            "Call Date": call_date,
            "Timestamp": datetime.utcnow()
        }

        # Update based on CallSid
        result = call_logs.update_one({"call_sid": call_sid}, {"$set": update_fields})

        if result.matched_count == 1:
            logger.info(f"Call status updated for CallSid {call_sid}: {mapped_status}")

            # If call is completed or not picked, fetch recording and process transcription
            if mapped_status in ['completed', 'not picked']:
                # Fetch Recording SID
                twilio_service = TwilioService()
                recording_sid = twilio_service.fetch_recording_sid(call_sid)

                if recording_sid:
                    # Update Recording SID in MongoDB
                    call_logs.update_one({"call_sid": call_sid}, {"$set": {"Recording SID": recording_sid}})

                    # Fetch Recording URL
                    recording = twilio_service.client.recordings(recording_sid).fetch()
                    recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"

                    # Stream the recording directly to OpenAI without saving to disk
                    response = requests.get(recording_url, auth=(twilio_service.account_sid, twilio_service.auth_token))
                    if response.status_code == 200:
                        audio_stream = BytesIO(response.content)
                        # Add 'name' attribute to BytesIO object
                        audio_stream.name = "recording.mp3"

                        # Transcribe using OpenAI
                        openai_api_key = current_app.config.get("OPENAI_API_KEY")
                        openai.api_key = openai_api_key

                        # Function to transcribe audio
                        def transcribe_audio(audio_file, language='hi'):
                            try:
                                transcript = openai.Audio.transcribe("whisper-1", audio_file, language=language)
                                return transcript['text']
                            except Exception as e:
                                logger.error(f"OpenAI transcription error: {str(e)}")
                                return ""

                        # Transcribe in Hindi
                        transcription_hindi = transcribe_audio(audio_stream, language='hi')

                        # Reset the stream position
                        audio_stream.seek(0)

                        # Transcribe in English
                        transcription_english = transcribe_audio(audio_stream, language='en')

                        # Extract Intent and future_notify_interest using OpenAI GPT
                        def extract_intent(transcription):
                            try:
                                prompt = (
                                    "Firstly identify what is the intent of person, is it yes or no. "
                                    "Then give output for future_notify_interest from the transcription.\n\n"
                                    f"Transcription: {transcription}\n\n"
                                    "Intent and future_notify_interest:"
                                )
                                # Using ChatCompletion API with gpt-4
                                response = openai.ChatCompletion.create(
                                    model="gpt-4",
                                    messages=[
                                        {"role": "system", "content": "You are a helpful assistant."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    max_tokens=50,
                                    n=1,
                                    temperature=0.5,
                                )
                                result = response.choices[0].message['content'].strip()
                                return result
                            except Exception as e:
                                logger.error(f"OpenAI intent extraction error: {str(e)}")
                                return ""

                        intent_future = extract_intent(transcription_english)
                        intent, future_notify_interest = "", ""
                        if intent_future:
                            parts = intent_future.split("\n")
                            if len(parts) >= 2:
                                intent = parts[0].split(":")[-1].strip()
                                future_notify_interest = parts[1].split(":")[-1].strip()
                            elif len(parts) == 1:
                                intent = parts[0].split(":")[-1].strip()

                        # Update call_logs with transcription and intent
                        call_logs.update_one(
                            {"call_sid": call_sid},
                            {"$set": {
                                "Transcription_Hindi": transcription_hindi,
                                "Transcription_English": transcription_english,
                                "Intent": intent,
                                "future_notify_interest": future_notify_interest
                            }}
                        )
                    else:
                        logger.warning(f"Failed to fetch recording for CallSid {call_sid}")
        else:
            logger.warning(f"No call log found for CallSid {call_sid}")

        # Return a 204 No Content response to Twilio
        return ('', 204)

    except Exception as e:
        logger.error(f"OpenAI transcription error: {str(e)}")
        return error_response("An internal error occurred.", 500)
    
    
    


