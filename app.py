# app.py

from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from config import Config
from blueprints.upload import upload_bp
from blueprints.records import records_bp
from blueprints.calls import calls_bp
# from blueprints.twili o import twilio_bp  # Import Twilio Blueprint

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Load environment variables
    load_dotenv()

    # MongoDB Configuration
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    app.config["TWILIO_ACCOUNT_SID"] = os.getenv("TWILIO_ACCOUNT_SID")
    app.config["TWILIO_AUTH_TOKEN"] = os.getenv("TWILIO_AUTH_TOKEN")
    app.config["TWILIO_PHONE_NUMBER"] = os.getenv("TWILIO_PHONE_NUMBER")
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    app.config["NGROK_URL"] = os.getenv("NGROK_URL")
    app.config["ALLOWED_EXTENSIONS"] = ['xlsx', 'xls']

    # Initialize PyMongo
    mongo = PyMongo(app)
    app.mongo = mongo

    # Register Blueprints
    app.register_blueprint(upload_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(calls_bp)
    # app.register_blueprint(twilio_bp)  # Register Twilio Blueprint

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)


# from flask import Flask
# from flask_pymongo import PyMongo
# from dotenv import load_dotenv
# import os
# from config import Config
# from blueprints.upload import upload_bp
# from blueprints.records import records_bp
# from blueprints.calls import calls_bp
# from services.scheduler_service import setup_scheduler, add_jobs_to_collection, schedule_job_checker

# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO)


# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     # Load environment variables
#     load_dotenv()

#     # MongoDB Configuration
#     app.config["MONGO_URI"] = os.getenv("MONGO_URI")
#     app.config["TWILIO_ACCOUNT_SID"] = os.getenv("TWILIO_ACCOUNT_SID")
#     app.config["TWILIO_AUTH_TOKEN"] = os.getenv("TWILIO_AUTH_TOKEN")
#     app.config["TWILIO_PHONE_NUMBER"] = os.getenv("TWILIO_PHONE_NUMBER")
#     app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
#     app.config["NGROK_URL"] = os.getenv("NGROK_URL")

#     # Initialize PyMongo
#     mongo = PyMongo(app)
#     app.mongo = mongo

#     # Register Blueprints
#     app.register_blueprint(upload_bp)
#     app.register_blueprint(records_bp)
#     app.register_blueprint(calls_bp)

#     # Initialize Scheduler with app context
#     with app.app_context():
#         setup_scheduler()  # Set up the scheduler
#         add_jobs_to_collection()  # Add jobs to the collection
#         schedule_job_checker()  # Set up periodic checks for jobs

#     return app

# # Assign the app instance to the global 'app' variable
# app = create_app()

# if __name__ == "__main__":
#     app.run(debug=True)
