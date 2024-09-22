# utils/response.py

from flask import jsonify

def success_response(message, data=None, status=200):
    """
    Generate a standardized success JSON response.
    
    Args:
        message (str): Success message.
        data (dict, optional): Additional data to include.
        status (int): HTTP status code.
    
    Returns:
        Response: Flask JSON response.
    """
    payload = {
        "success": True,
        "message": message
    }
    if data:
        payload["data"] = data
    return jsonify(payload), status

def error_response(message, status=400):
    """
    Generate a standardized error JSON response.
    
    Args:
        message (str): Error message.
        status (int): HTTP status code.
    
    Returns:
        Response: Flask JSON response.
    """
    payload = {
        "success": False,
        "error": message
    }
    return jsonify(payload), status
