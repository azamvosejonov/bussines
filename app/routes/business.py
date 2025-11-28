from flask import Blueprint, request, jsonify
from app import db, jwt
from app.models import Business, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.auth import role_required, business_owner_or_admin

business_bp = Blueprint('business', __name__)

@business_bp.route('/businesses', methods=['GET'])
@jwt_required()
@role_required('admin', 'owner')
def get_businesses():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        businesses = Business.query.all()
    else:
        businesses = Business.query.filter_by(owner_id=user_id).all()
    return jsonify([{'id': b.id, 'name': b.name, 'industry': b.industry} for b in businesses]), 200

@business_bp.route('/businesses', methods=['POST'])
@jwt_required()
@role_required('admin', 'owner')
def create_business():
    data = request.get_json()
    user_id = get_jwt_identity()
    business = Business(
        owner_id=user_id,
        name=data['name'],
        industry=data.get('industry'),
        country=data.get('country'),
        currency=data.get('currency', 'UZS'),
        settings=data.get('settings', {})
    )
    db.session.add(business)
    db.session.commit()
    return jsonify({'id': business.id, 'message': 'Business created'}), 201

# Assuming biz_id is passed in url, but for listing all, perhaps adjust, but for now, since url_prefix is /api, and for specific biz, in other bps.

# Actually, for multi-tenant, other routes will have biz_id in path.
