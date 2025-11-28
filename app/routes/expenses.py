from flask import Blueprint, request, jsonify
from app import db
from app.models import Expense, User, Business
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__)

def check_business_access(biz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        return True
    business = Business.query.get(biz_id)
    return business and business.owner_id == user.id

@expenses_bp.route('/expenses', methods=['GET'])
@jwt_required()
def get_expenses(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    category = request.args.get('category')
    query = Expense.query.filter_by(business_id=biz_id)
    if from_date:
        query = query.filter(Expense.expense_date >= from_date)
    if to_date:
        query = query.filter(Expense.expense_date <= to_date)
    if category:
        query = query.filter_by(category=category)
    expenses = query.all()
    return jsonify([{
        'id': e.id,
        'category': e.category,
        'amount': e.amount,
        'description': e.description,
        'expense_date': e.expense_date.isoformat()
    } for e in expenses]), 200

@expenses_bp.route('/expenses', methods=['POST'])
@jwt_required()
def create_expense(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    expense = Expense(
        business_id=biz_id,
        branch_id=data.get('branch_id'),
        category=data['category'],
        amount=data['amount'],
        description=data.get('description'),
        expense_date=data.get('expense_date', datetime.utcnow())
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({'id': expense.id, 'message': 'Expense created'}), 201
