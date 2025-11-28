from flask import Blueprint, request, jsonify
from app import db
from app.models import Sale, SaleItem, User, Business
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

sales_bp = Blueprint('sales', __name__)

def check_business_access(biz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        return True
    business = Business.query.get(biz_id)
    return business and business.owner_id == user.id

@sales_bp.route('/sales', methods=['GET'])
@jwt_required()
def get_sales(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    query = Sale.query.filter_by(business_id=biz_id)
    if from_date:
        query = query.filter(Sale.sale_date >= from_date)
    if to_date:
        query = query.filter(Sale.sale_date <= to_date)
    sales = query.all()
    return jsonify([{
        'id': s.id,
        'total': s.total,
        'sale_date': s.sale_date.isoformat(),
        'items': [{'product_id': i.product_id, 'quantity': i.quantity, 'unit_price': i.unit_price} for i in s.items]
    } for s in sales]), 200

@sales_bp.route('/sales', methods=['POST'])
@jwt_required()
def create_sale(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    branch_id = data['branch_id']
    items = data['items']
    cashier_id = data['cashier_id']
    sale_date = data.get('date', datetime.utcnow())

    total = 0
    sale = Sale(business_id=biz_id, branch_id=branch_id, cashier_id=cashier_id, sale_date=sale_date, total=0)
    db.session.add(sale)
    db.session.flush()  # To get sale.id

    for item in items:
        product_id = item['product_id']
        quantity = item['quantity']
        unit_price = item['price']
        subtotal = quantity * unit_price
        total += subtotal
        sale_item = SaleItem(sale_id=sale.id, product_id=product_id, quantity=quantity, unit_price=unit_price)
        db.session.add(sale_item)

    sale.total = total
    db.session.commit()
    return jsonify({'id': sale.id, 'message': 'Sale created'}), 201
