# blueprints/upload.py

from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename

from services.data_parser import DataParser
from utils.response import success_response, error_response

import io
import threading
import time
import requests
from datetime import datetime, timedelta
import pytz
from bson.objectid import ObjectId

upload_bp = Blueprint('upload', __name__)

# IST Timezone
IST = pytz.timezone('Asia/Kolkata')


def allowed_file(filename, allowed_extensions):
    """
    Check if the file has an allowed extension.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def extract_shift_start_time(shift_time):
    """
    Extract the start time from the shift time.
    Example input: "12:00-14:00", return "12:00"
    """
    return shift_time.split('-')[0].strip()  # Extract "12:00"


def schedule_api_requests(record_id, shift_datetime_ist):
    """
    Schedule two API requests for the given record:
    1. 12 hours, 1 minute, and 30 seconds before the shift time.
    2. 2 hours, 14 minutes, and 35 seconds before the shift time.
    """
    now_ist = datetime.now(IST)

    # Calculate times for the API requests
    time_before_shift_1 = shift_datetime_ist - timedelta(hours=00, minutes=36, seconds=00)
    time_before_shift_2 = shift_datetime_ist - timedelta(hours=00, minutes=34, seconds=35)

    # Convert times to seconds for delay calculations
    delay_for_first_call = (time_before_shift_1 - now_ist).total_seconds()
    delay_for_second_call = (time_before_shift_2 - now_ist).total_seconds()

    # Function to send POST request with 1-second gap
    def send_post_with_gap(record_id, followup_type, delay, previous_delay=0):
        if delay > 0:
            # Introduce a cumulative delay based on previous calls
            cumulative_delay = delay + previous_delay
            threading.Timer(cumulative_delay, send_post_request, args=[record_id, followup_type]).start()
            print(f"{followup_type} POST API request for record {record_id} scheduled in {cumulative_delay} seconds.")
            return cumulative_delay + 1  # Adding 1 second gap for the next call
        else:
            print(f"{followup_type} POST API request for record {record_id} is in the past and won't be scheduled.")
            return previous_delay

    # Initialize previous_delay to 0
    previous_delay = 0

    # Schedule the first API call
    previous_delay = send_post_with_gap(record_id, '1st follow-up', delay_for_first_call, previous_delay)

    # Schedule the second API call with a 1-second gap
    previous_delay = send_post_with_gap(record_id, '2nd follow-up', delay_for_second_call, previous_delay)


def send_post_request(record_id, followup_type):
    """
    Sends a POST request to `calls.py` to initiate the call.
    """
    print(f"Sending {followup_type} POST API request for record {record_id}")
    url = f"http://localhost:5000/make_call/{record_id}"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print(f"{followup_type} POST API request for record {record_id} successful.")
        else:
            print(f"Error: {followup_type} POST API request for record {record_id} failed with status code {response.status_code}")
    except Exception as e:
        print(f"Error sending {followup_type} POST API request for record {record_id}: {str(e)}")


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Endpoint to upload Excel files, parse them, store data in MongoDB, and schedule follow-up API calls.
    """
    if 'file' not in request.files:
        return error_response("No file part in the request", 400)

    file = request.files['file']

    if file.filename == '':
        return error_response("No file selected for uploading", 400)

    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', [])
    if not allowed_file(file.filename, allowed_extensions):
        allowed = ', '.join(allowed_extensions)
        return error_response(f"Allowed file types are {allowed}", 400)

    try:
        # Read file content into memory
        file_stream = io.BytesIO(file.read())

        # Parse the Excel file
        data_parser = DataParser()
        records = data_parser.parse_excel(file_stream, required_fields=[
            'Name', 'Number', 'Shift Name', 'Shift Timings',
            'Dress Code', 'Work Description', 'date'
        ])

        # Insert records into MongoDB
        mongo = current_app.mongo
        collection = mongo.db.champ_details

        # Enhance each record with default fields
        for record in records:
            record.update({
                "Recording SID": "",
                "12h follow-up": "",
                "2h follow-up": "",
                "Dress-update": "",
                "future-shift-interest": ""
            })

        # Insert many documents at once
        if records:
            insert_result = collection.insert_many(records)
            inserted_ids = insert_result.inserted_ids  # List of ObjectIds

            # For each inserted record, schedule follow-up API requests
            for record, inserted_id in zip(records, inserted_ids):
                shift_date = record.get("date")  # Assuming 'date' is stored as "YYYY-MM-DD"
                shift_time = record.get("Shift Timings")  # Shift time, e.g., "12:00-14:00"
                record_id = str(inserted_id)

                if shift_date and shift_time:
                    try:
                        shift_start_time = extract_shift_start_time(shift_time)
                        shift_datetime_str = f"{shift_date} {shift_start_time}"
                        shift_datetime_ist = datetime.strptime(shift_datetime_str, '%Y-%m-%d %H:%M')
                        shift_datetime_ist = IST.localize(shift_datetime_ist)

                        # Schedule the follow-up API requests
                        schedule_api_requests(record_id, shift_datetime_ist)

                    except Exception as e:
                        print(f"Error scheduling API calls for record {record_id}: {str(e)}")
                else:
                    print(f"Invalid shift date or time for record {record_id}")

            # Convert ObjectIds to strings for the response
            inserted_ids_str = [str(_id) for _id in inserted_ids]

            return success_response(
                message="File successfully uploaded, data stored, and API calls scheduled.",
                data={"inserted_ids": inserted_ids_str},
                status=201
            )
        else:
            return error_response("No valid records found in the file.", 400)

    except ValueError as ve:
        return error_response(str(ve), 400)
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)
