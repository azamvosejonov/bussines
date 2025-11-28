from flask import Blueprint, request, jsonify
from app import db, bcrypt, jwt
from app.models import User, Business, AuditLog
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token, role=user.role), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In JWT, logout is handled client-side by discarding the token
    return jsonify({'message': 'Logged out'}), 200

@auth_bp.route('/register-business', methods=['POST'])
def register_business():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    business_name = data.get('business_name')
    industry = data.get('industry')
    country = data.get('country')
    currency = data.get('currency', 'UZS')

    if not email or '@' not in email:
        return jsonify({'message': 'Invalid email format'}), 400
    if not email.endswith('@gmail.com'):
        return jsonify({'message': 'Email must be a Gmail address'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, email=email, password_hash=hashed_password, role='owner')
    db.session.add(user)
    db.session.commit()

    business = Business(owner_id=user.id, name=business_name, industry=industry, country=country, currency=currency)
    db.session.add(business)
    db.session.commit()

    # Audit log
    audit = AuditLog(business_id=business.id, user_id=user.id, action='Business registered')
    db.session.add(audit)
    db.session.commit()

    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token, business_id=business.id), 201
