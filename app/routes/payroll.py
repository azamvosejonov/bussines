from flask import Blueprint, request, jsonify
from app import db
from app.models import Sale, Expense, Employee, Payroll, ProfitDistribution, User, Business
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.utils.profit_calc import calculate_profit_distribution

payroll_bp = Blueprint('payroll', __name__)

def check_business_access(biz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        return True
    business = Business.query.get(biz_id)
    return business and business.owner_id == user.id

@payroll_bp.route('/compute-profit', methods=['POST'])
@jwt_required()
def compute_profit(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    from_date = data['from']
    to_date = data['to']
    distribution_mode = data['distribution_mode']
    mode_params = data.get('mode_params', {})

    # Calculate total revenue
    sales = Sale.query.filter(Sale.business_id == biz_id, Sale.sale_date >= from_date, Sale.sale_date <= to_date).all()
    total_revenue = sum(s.total for s in sales)

    # Total expenses (excluding salaries if handled separately)
    expenses = Expense.query.filter(Expense.business_id == biz_id, Expense.expense_date >= from_date, Expense.expense_date <= to_date).all()
    total_expenses = sum(e.amount for e in expenses)

    # Assume salaries are separate, but for now, include if category == 'salary' or something. Spec says if salaries in expenses, don't double.

    # For simplicity, assume expenses include salaries.

    gross_profit = total_revenue - total_expenses

    # Employees for distribution
    employees = Employee.query.filter_by(business_id=biz_id, is_active=True).all()

    # Calculate distribution
    distribution = calculate_profit_distribution(gross_profit, employees, distribution_mode, mode_params)

    return jsonify({
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'gross_profit': gross_profit,
        'distribution': distribution
    }), 200

@payroll_bp.route('/commit-distribution', methods=['POST'])
@jwt_required()
def commit_distribution(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    from_date = data['from']
    to_date = data['to']
    distribution_mode = data['distribution_mode']
    mode_params = data.get('mode_params', {})

    # Similar calculation
    sales = Sale.query.filter(Sale.business_id == biz_id, Sale.sale_date >= from_date, Sale.sale_date <= to_date).all()
    total_revenue = sum(s.total for s in sales)
    expenses = Expense.query.filter(Expense.business_id == biz_id, Expense.expense_date >= from_date, Expense.expense_date <= to_date).all()
    total_expenses = sum(e.amount for e in expenses)
    gross_profit = total_revenue - total_expenses
    employees = Employee.query.filter_by(business_id=biz_id, is_active=True).all()
    distribution = calculate_profit_distribution(gross_profit, employees, distribution_mode, mode_params)

    # Assume net_profit = gross_profit, since salaries included in expenses

    # Save Payroll
    payroll = Payroll(
        business_id=biz_id,
        period_start=from_date,
        period_end=to_date,
        total_salaries=0,  # Adjust if needed
        status='paid'
    )
    db.session.add(payroll)

    # Save ProfitDistribution
    profit_dist = ProfitDistribution(
        business_id=biz_id,
        period_start=from_date,
        period_end=to_date,
        net_profit=gross_profit,
        distribution_mode=distribution_mode,
        details=distribution
    )
    db.session.add(profit_dist)
    db.session.commit()

    return jsonify({'message': 'Distribution committed', 'payroll_id': payroll.id, 'distribution_id': profit_dist.id}), 200

@payroll_bp.route('/profit-distributions', methods=['GET'])
@jwt_required()
def get_profit_distributions(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    query = ProfitDistribution.query.filter_by(business_id=biz_id)
    if from_date:
        query = query.filter(ProfitDistribution.period_start >= from_date)
    if to_date:
        query = query.filter(ProfitDistribution.period_end <= to_date)
    dists = query.all()
    return jsonify([{
        'id': d.id,
        'period_start': d.period_start.isoformat(),
        'period_end': d.period_end.isoformat(),
        'net_profit': d.net_profit,
        'distribution_mode': d.distribution_mode,
        'details': d.details
    } for d in dists]), 200
