from flask import Blueprint, request, jsonify
from app import db
from app.models import Employee, User, Business
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.auth import role_required

employees_bp = Blueprint('employees', __name__)

def check_business_access(biz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        return True
    business = Business.query.get(biz_id)
    return business and business.owner_id == user.id

@employees_bp.route('/employees', methods=['GET'])
@jwt_required()
def get_employees(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    employees = Employee.query.filter_by(business_id=biz_id).all()
    return jsonify([{
        'id': e.id,
        'first_name': e.first_name,
        'last_name': e.last_name,
        'position': e.position,
        'base_salary': e.base_salary,
        'is_active': e.is_active
    } for e in employees]), 200

@employees_bp.route('/employees', methods=['POST'])
@jwt_required()
def create_employee(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    user_id = get_jwt_identity()
    employee = Employee(
        business_id=biz_id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        position=data.get('position'),
        base_salary=data['base_salary'],
        salary_type=data.get('salary_type', 'monthly'),
        branch_id=data.get('branch_id'),
        custom_share_pct=data.get('custom_share_pct'),
        created_by=user_id
    )
    db.session.add(employee)
    db.session.commit()
    return jsonify({'id': employee.id, 'message': 'Employee created'}), 201

@employees_bp.route('/employees/<int:emp_id>', methods=['PUT'])
@jwt_required()
def update_employee(biz_id, emp_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    employee = Employee.query.filter_by(id=emp_id, business_id=biz_id).first()
    if not employee:
        return jsonify({'message': 'Employee not found'}), 404
    data = request.get_json()
    for key, value in data.items():
        if hasattr(employee, key):
            setattr(employee, key, value)
    db.session.commit()
    return jsonify({'message': 'Employee updated'}), 200

@employees_bp.route('/employees/<int:emp_id>', methods=['DELETE'])
@jwt_required()
def delete_employee(biz_id, emp_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    employee = Employee.query.filter_by(id=emp_id, business_id=biz_id).first()
    if not employee:
        return jsonify({'message': 'Employee not found'}), 404
    db.session.delete(employee)
    db.session.commit()
    return jsonify({'message': 'Employee deleted'}), 200
