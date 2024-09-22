# blueprints/records.py

from flask import Blueprint, request, current_app
from bson.objectid import ObjectId
from bson.errors import InvalidId

from utils.response import success_response, error_response
from services.data_parser import DataParser

records_bp = Blueprint('records', __name__)

# Define allowed fields for updates
ALLOWED_UPDATE_FIELDS = {
    "Name",
    "Number",
    "Shift Name",
    "Shift Timings",
    "Dress Code",
    "Work Description",
    "date",
    "Recording SID",
    "12h follow-up",
    "2h follow-up",
    "Dress-update",
    "future-shift-interest"
}

@records_bp.route('/records', methods=['GET'])
def get_all_records():
    """
    Fetch all records from the champ_details collection.
    Optional Query Parameters:
        - page: Page number for pagination (default: 1)
        - per_page: Number of records per page (default: 20)
        - sheet_name: Filter by sheet_name
        - work_description: Filter by Work Description
    """
    try:
        mongo = current_app.mongo
        collection = mongo.db.champ_details
        
        # Fetch query parameters for filtering and pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        sheet_name = request.args.get('sheet_name')
        work_description = request.args.get('work_description')
        
        query = {}
        if sheet_name:
            query['sheet_name'] = sheet_name
        if work_description:
            query['Work Description'] = work_description
        
        # Calculate pagination
        skip = (page - 1) * per_page
        cursor = collection.find(query).skip(skip).limit(per_page)
        
        records = []
        for record in cursor:
            record['_id'] = str(record['_id'])  # Convert ObjectId to string
            records.append(record)
        
        return success_response(
            message="Records fetched successfully",
            data={
                "page": page,
                "per_page": per_page,
                "records": records
            },
            status=200
        )
    except ValueError:
        return error_response("Invalid pagination parameters", 400)
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)

@records_bp.route('/records/<string:name>', methods=['GET'])
def get_record_by_name(name):
    """
    Fetch a single record by Name.
    """
    try:
        mongo = current_app.mongo
        collection = mongo.db.champ_details
        
        record = collection.find_one({"Name": name})
        if record:
            record['_id'] = str(record['_id'])  # Convert ObjectId to string
            return success_response(
                message="Record fetched successfully",
                data={"record": record},
                status=200
            )
        else:
            return error_response("Record not found", 404)
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)

@records_bp.route('/records/sheet/<string:sheet_name>', methods=['GET'])
def get_records_by_sheet(sheet_name):
    """
    Fetch all records associated with a specific sheet_name.
    """
    try:
        mongo = current_app.mongo
        collection = mongo.db.champ_details
        
        cursor = collection.find({"sheet_name": sheet_name})
        
        records = []
        for record in cursor:
            record['_id'] = str(record['_id'])  # Convert ObjectId to string
            records.append(record)
        
        if records:
            return success_response(
                message="Records fetched successfully",
                data={"records": records},
                status=200
            )
        else:
            return error_response("No records found for the specified sheet_name", 404)
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)

@records_bp.route('/records/work-description/<string:work_description>', methods=['GET'])
def get_records_by_work_description(work_description):
    """
    Fetch all records matching the provided Work Description.
    """
    try:
        mongo = current_app.mongo
        collection = mongo.db.champ_details
        
        cursor = collection.find({"Work Description": work_description})
        
        records = []
        for record in cursor:
            record['_id'] = str(record['_id'])  # Convert ObjectId to string
            records.append(record)
        
        if records:
            return success_response(
                message="Records fetched successfully",
                data={"records": records},
                status=200
            )
        else:
            return error_response("No records found for the specified Work Description", 404)
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)

@records_bp.route('/records/<string:name>', methods=['PUT', 'PATCH'])
@records_bp.route('/records/id/<string:record_id>', methods=['PUT', 'PATCH'])
def update_record(name=None, record_id=None):
    """
    Update an existing record by Name or by _id.
    Supports both PUT (full update) and PATCH (partial update).
    """
    try:
        if request.method not in ['PUT', 'PATCH']:
            return error_response("Method not allowed", 405)
        
        data = request.get_json()
        if not data:
            return error_response("No data provided for update", 400)
        
        # Determine if it's an update by Name or by _id
        if record_id:
            try:
                query = {"_id": ObjectId(record_id)}
            except InvalidId:
                return error_response("Invalid record ID format", 400)
        elif name:
            query = {"Name": name}
        else:
            return error_response("Invalid request parameters", 400)
        
        # Validate the fields to be updated
        invalid_fields = set(data.keys()) - ALLOWED_UPDATE_FIELDS
        if invalid_fields:
            return error_response(f"Invalid fields for update: {', '.join(invalid_fields)}", 400)
        
        # Initialize DataParser for normalization
        parser = DataParser()
        
        # Prepare the update data
        update_data = {}
        
        for field, value in data.items():
            if field == "Number":
                normalized_number = parser.normalize_number(str(value).strip())
                update_data["Number"] = normalized_number
            elif field == "date":
                try:
                    normalized_date = parser.validate_and_normalize_date(str(value).strip())
                    update_data["date"] = normalized_date
                except ValueError as ve:
                    return error_response(str(ve), 400)
            elif field == "Shift Name":
                # Normalize Shift Name by removing ' Shift' suffix if present
                shift_name = str(value).strip()
                if shift_name.endswith(' Shift'):
                    shift_name = shift_name.replace(' Shift', '').strip()
                update_data["Shift Name"] = shift_name
            elif field == "Shift Timings":
                # Normalize Shift Timings by removing spaces around '-' and ensuring "HH:MM-HH:MM"
                shift_timings = str(value).strip().replace(' ', '')
                update_data["Shift Timings"] = shift_timings
            else:
                # For other fields, simply strip whitespace
                update_data[field] = str(value).strip()
        
        # Perform the update
        mongo = current_app.mongo
        collection = mongo.db.champ_details
        
        if request.method == 'PUT':
            # For PUT, replace the entire document except _id and sheet_name
            existing_record = collection.find_one(query)
            if not existing_record:
                return error_response("Record not found", 404)
            
            # Preserve _id and sheet_name
            updated_document = {key: existing_record[key] for key in existing_record if key not in ALLOWED_UPDATE_FIELDS}
            updated_document.update(update_data)
            
            # Replace the document
            collection.replace_one(query, updated_document)
            return success_response("Record successfully updated", status=200)
        else:
            # For PATCH, apply partial updates using $set
            result = collection.update_one(query, {"$set": update_data})
            if result.matched_count == 0:
                return error_response("Record not found", 404)
            return success_response("Record successfully updated", status=200)
    
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)

@records_bp.route('/records/id/<string:record_id>', methods=['DELETE'])
def delete_record_by_id(record_id):
    """
    Delete a single record by its MongoDB _id.
    ---
    """
    try:
        # Attempt to convert the provided record_id to a valid ObjectId
        obj_id = ObjectId(record_id)
    except InvalidId:
        return error_response("Invalid record ID format", 400)

    # Access the MongoDB collection
    mongo = current_app.mongo
    collection = mongo.db.champ_details

    # Attempt to delete the record
    result = collection.delete_one({"_id": obj_id})

    if result.deleted_count == 1:
        return success_response("Record successfully deleted", status=200)
    else:
        return error_response("Record not found", 404)


@records_bp.route('/records/sheet/<string:sheet_name>', methods=['DELETE'])
def delete_records_by_sheet_id(sheet_name):
    """
    Delete all records associated with the provided sheet_name.
    ---
    """
    try:
        # Access the MongoDB collection
        mongo = current_app.mongo
        collection = mongo.db.champ_details

        # Attempt to delete all records with the specified sheet_id
        result = collection.delete_many({"sheet_name": sheet_name})
        deleted_count = result.deleted_count

        if deleted_count > 0:
            return success_response(f"Records successfully deleted. Total records deleted: {deleted_count}", status=200)
        else:
            return error_response("No records found for the specified sheet_name", 404)
    except Exception as e:
        return error_response(f"An error occurred: {str(e)}", 500)