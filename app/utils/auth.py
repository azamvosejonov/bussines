from flask_jwt_extended import get_jwt_identity
from app.models import User, Business
from functools import wraps
from flask import jsonify

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or user.role not in roles:
                return jsonify({'message': 'Access denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def business_owner_or_admin(business_id):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404
            if user.role == 'admin':
                return f(*args, **kwargs)
            business = Business.query.get(business_id)
            if not business or business.owner_id != user.id:
                return jsonify({'message': 'Access denied to business'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
