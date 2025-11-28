from flask import Blueprint, request, jsonify, send_file
from app import db
from app.models import Sale, Expense, ProfitDistribution, User, Business
from flask_jwt_extended import jwt_required, get_jwt_identity
import csv
from io import StringIO, BytesIO
import openpyxl

reports_bp = Blueprint('reports', __name__)

def check_business_access(biz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        return True
    business = Business.query.get(biz_id)
    return business and business.owner_id == user.id

@reports_bp.route('/reports/daily', methods=['GET'])
@jwt_required()
def daily_report(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    date = request.args.get('date')
    if not date:
        return jsonify({'message': 'Date required'}), 400

    sales = Sale.query.filter(Sale.business_id == biz_id, Sale.sale_date == date).all()
    expenses = Expense.query.filter(Expense.business_id == biz_id, Expense.expense_date == date).all()

    data = {
        'sales': [{'id': s.id, 'total': s.total} for s in sales],
        'expenses': [{'id': e.id, 'amount': e.amount, 'category': e.category} for e in expenses],
        'total_sales': sum(s.total for s in sales),
        'total_expenses': sum(e.amount for e in expenses)
    }
    return jsonify(data), 200

@reports_bp.route('/reports/custom', methods=['GET'])
@jwt_required()
def custom_report(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    report_type = request.args.get('type', 'json')  # json, excel, pdf, csv

    sales = Sale.query.filter(Sale.business_id == biz_id, Sale.sale_date >= from_date, Sale.sale_date <= to_date).all()
    expenses = Expense.query.filter(Expense.business_id == biz_id, Expense.expense_date >= from_date, Expense.expense_date <= to_date).all()

    if report_type == 'json':
        return jsonify({
            'sales': [{'date': str(s.sale_date), 'total': s.total} for s in sales],
            'expenses': [{'date': str(e.expense_date), 'amount': e.amount, 'category': e.category} for e in expenses]
        }), 200
    elif report_type == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Type', 'Date', 'Amount/Category'])
        for s in sales:
            writer.writerow(['Sale', str(s.sale_date), s.total])
        for e in expenses:
            writer.writerow(['Expense', str(e.expense_date), f"{e.amount} ({e.category})"])
        output.seek(0)
        return send_file(BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', download_name='report.csv')
    elif report_type == 'excel':
        wb = openpyxl.Workbook()
        ws_sales = wb.active
        ws_sales.title = 'Sales'
        ws_sales.append(['Date', 'Total'])
        for s in sales:
            ws_sales.append([str(s.sale_date), s.total])
        ws_expenses = wb.create_sheet('Expenses')
        ws_expenses.append(['Date', 'Amount', 'Category'])
        for e in expenses:
            ws_expenses.append([str(e.expense_date), e.amount, e.category])
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name='report.xlsx')
    elif report_type == 'pdf':
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        output = BytesIO()
        c = canvas.Canvas(output, pagesizes=letter)
        c.drawString(100, 750, f"Sales Report from {from_date} to {to_date}")
        y = 730
        for s in sales:
            c.drawString(100, y, f"Date: {s.sale_date}, Total: {s.total}")
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        c.showPage()
        c.drawString(100, 750, "Expenses")
        y = 730
        for e in expenses:
            c.drawString(100, y, f"Date: {e.expense_date}, Amount: {e.amount}, Category: {e.category}")
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        c.save()
        output.seek(0)
        return send_file(output, mimetype='application/pdf', download_name='report.pdf')
    else:
        return jsonify({'message': 'Invalid type'}), 400
