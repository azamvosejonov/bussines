from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, send_file, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, DateField, HiddenField, DateTimeLocalField, IntegerField, FloatField, FileField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError
from flask_wtf.file import FileAllowed
from app import db, bcrypt
from app.models import User, Business, Employee, Product, Sale, Expense, Role, UserBusinessRole, Report, Shift, Branch, KPI, \
    Notification, AlertRule, InventoryAlert, DebtReminder, Recipe, RecipeIngredient, BusinessSettings, Project, Task, \
    Customer, CustomerInteraction, Invoice, InvoiceItem, CashFlow, Document, MarketingCampaign, CampaignPerformance, \
    ContractTemplate, Contract, ContractVersion, CurrencyRate, TaxRate, InventoryItem, InventoryTransaction, Budget, \
    BudgetItem, Supplier, PurchaseOrder, PurchaseOrderItem, SalesGoal, CalendarEvent, Campaign, CampaignEmployee, \
    CampaignExpense, CampaignRevenue, CampaignTask, CampaignReport, CampaignTimeEntry, BusinessType, BUSINESS_TYPES, \
    UserPreferences, Payroll, AuditLog
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from datetime import datetime, timedelta
from app.services.business_logic import RecipeService, ProfitCalculator, AuditService
from app.services.enterprise_services import ProjectService, CRMService, PayrollService, CashFlowService, InvoiceService
try:
    from app.services.analytics import BusinessAnalytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    BusinessAnalytics = None
    ANALYTICS_AVAILABLE = False
from app.services.marketing_contracts import MarketingService, ContractService
from app.services.currency_service import CurrencyService
from app.services.tax_service import TaxService
from app.services.business_type_service import BusinessTypeService
from app.services.budget_service import BudgetService
from app.services.campaign_service import CampaignService
from werkzeug.utils import secure_filename
import os
from functools import wraps
import qrcode
import io

web_bp = Blueprint('web', __name__)

# Custom CSRF exempt decorator
def csrf_exempt_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Disable CSRF for this route
        from flask import current_app
        csrf = current_app.extensions.get('csrf')
        if csrf:
            csrf.exempt(f)
        return f(*args, **kwargs)
    return decorated_function

# Role-based access control decorators
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('web.login'))
            
            user_id = session['user_id']
            user = User.query.get(user_id)
            
            if not user:
                session.clear()
                return redirect(url_for('web.login'))
            
            # Admin has access to everything
            if user.role == 'admin':
                return f(*args, **kwargs)
            
            # Check if user has required role
            if user.role not in roles:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('web.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def business_access_required(f):
    @wraps(f)
    def decorated_function(biz_id, *args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('web.login'))
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        business = Business.query.get(biz_id)
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('web.dashboard'))
        
        # Admin and business owner have access
        if user.role == 'admin' or business.owner_id == user_id:
            return f(biz_id, *args, **kwargs)
        
        # Check business role assignments
        user_business_role = UserBusinessRole.query.filter_by(
            user_id=user_id, 
            business_id=biz_id
        ).first()
        
        if user_business_role:
            return f(biz_id, *args, **kwargs)
        
        flash('Access denied. You are not assigned to this business.', 'error')
        return redirect(url_for('web.dashboard'))
    
    return decorated_function

def get_user_permissions(user_id, business_id=None):
    """Get user permissions based on their role and business assignments"""
    user = User.query.get(user_id)
    if not user:
        return []
    
    permissions = []
    
    # System-wide permissions based on user role
    if user.role == 'admin':
        permissions.extend(['admin', 'manage_users', 'manage_businesses', 'view_all'])
    elif user.role == 'business_owner':
        permissions.extend(['manage_business', 'manage_employees', 'manage_finances', 'view_reports'])
    elif user.role == 'hr_manager':
        permissions.extend(['manage_employees', 'manage_payroll', 'view_hr_reports'])
    elif user.role == 'project_manager':
        permissions.extend(['manage_projects', 'manage_tasks', 'view_project_reports'])
    elif user.role == 'accountant':
        permissions.extend(['manage_finances', 'view_financial_reports'])
    elif user.role == 'sales_manager':
        permissions.extend(['manage_customers', 'manage_sales', 'view_sales_reports'])
    elif user.role == 'warehouse_manager':
        permissions.extend(['manage_inventory', 'manage_supplies', 'view_inventory_reports'])
    elif user.role == 'employee':
        permissions.extend(['view_personal', 'clock_in_out', 'view_tasks'])
    
    # Business-specific permissions
    if business_id:
        business_role = UserBusinessRole.query.filter_by(
            user_id=user_id, 
            business_id=business_id
        ).first()
        
        if business_role and business_role.role:
            # Add business role specific permissions
            business_permissions = business_role.role.permissions or {}
            for perm, allowed in business_permissions.items():
                if allowed:
                    permissions.append(f'business_{perm}')
    
    return list(set(permissions))  # Remove duplicates

# ... existing forms ...

class AssignRoleForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Role')

class CreateRoleForm(FlaskForm):
    name = StringField('Role Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    view_employees = BooleanField('View Employees')
    manage_employees = BooleanField('Manage Employees')
    view_sales = BooleanField('View Sales')
    manage_sales = BooleanField('Manage Sales')
    view_expenses = BooleanField('View Expenses')
    manage_expenses = BooleanField('Manage Expenses')
    view_reports = BooleanField('View Reports')
    create_reports = BooleanField('Create Reports')
    view_payroll = BooleanField('View Payroll')
    manage_payroll = BooleanField('Manage Payroll')
    submit = SubmitField('Create Role')

class InventoryItemForm(FlaskForm):
    name = StringField('Item Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    category = StringField('Category')
    quantity = IntegerField('Quantity', default=0)
    unit_price = FloatField('Unit Price', default=0.0)
    min_stock_level = IntegerField('Min Stock Level', default=0)
    max_stock_level = IntegerField('Max Stock Level', default=1000)
    location = StringField('Location')
    supplier = StringField('Supplier')
    barcode = StringField('Barcode')
    expiry_date = DateField('Expiry Date')
    submit = SubmitField('Save Item')

class InventoryTransactionForm(FlaskForm):
    transaction_type = SelectField('Transaction Type', choices=[
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Stock Adjustment')
    ], validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    reason = StringField('Reason')
    submit = SubmitField('Process Transaction')

class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    assigned_to = SelectField('Assigned To', coerce=int)
    priority = SelectField('Priority', choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')])
    estimated_hours = StringField('Estimated Hours')
    due_date = DateTimeLocalField('Due Date')

class CustomerForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email')
    phone = StringField('Phone')
    company = StringField('Company')
    status = SelectField('Status', choices=[('potential', 'Potential'), ('active', 'Active'), ('lost', 'Lost'), ('vip', 'VIP')])
    source = StringField('Source')
    submit = SubmitField('Save Customer')

class InvoiceForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[DataRequired()])
    project_id = SelectField('Project', coerce=int)
    issue_date = DateField('Issue Date', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    discount_amount = StringField('Discount Amount', default='0')
    submit = SubmitField('Create Invoice')

class CashFlowForm(FlaskForm):
    transaction_type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    subcategory = StringField('Subcategory')
    amount = StringField('Amount', validators=[DataRequired()])
    description = TextAreaField('Description')
    transaction_date = DateField('Date', validators=[DataRequired()])
    related_customer_id = SelectField('Related Customer', coerce=int)
    related_project_id = SelectField('Related Project', coerce=int)
    submit = SubmitField('Add Transaction')

class MarketingCampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    campaign_type = SelectField('Type', choices=[
        ('social_media', 'Social Media'),
        ('google_ads', 'Google Ads'),
        ('email', 'Email Marketing'),
        ('influencer', 'Influencer Marketing'),
        ('content', 'Content Marketing'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    platform = StringField('Platform')
    target_audience = StringField('Target Audience')
    budget = StringField('Budget')
    start_date = DateField('Start Date')
    end_date = DateField('End Date')
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    manager_id = SelectField('Campaign Manager', coerce=int)
    submit = SubmitField('Create Campaign')

class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role_type = SelectField('Role Type', choices=[
        ('admin', 'System Admin'),
        ('business_owner', 'Business Owner'),
        ('hr_manager', 'HR Manager'),
        ('project_manager', 'Project Manager'),
        ('accountant', 'Accountant'),
        ('sales_manager', 'Sales Manager'),
        ('warehouse_manager', 'Warehouse Manager'),
        ('employee', 'Employee')
    ], validators=[DataRequired()])
    business_role_id = SelectField('Business Role', coerce=int)
    submit = SubmitField('Create User')

class RecipeForm(FlaskForm):
    name = StringField('Recipe Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    selling_price = StringField('Selling Price', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('food', 'Food'),
        ('drink', 'Drink'),
        ('dessert', 'Dessert'),
        ('other', 'Other')
    ], default='food')
    submit = SubmitField('Save Recipe')

class RecipeIngredientForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = StringField('Quantity', validators=[DataRequired()])
    unit = SelectField('Unit', choices=[
        ('pieces', 'Pieces'),
        ('grams', 'Grams'),
        ('ml', 'Milliliters'),
        ('kg', 'Kilograms'),
        ('liters', 'Liters')
    ], default='pieces')
    submit = SubmitField('Add Ingredient')

class BusinessSettingsForm(FlaskForm):
    currency = SelectField('Currency', choices=[('UZS', 'UZS'), ('USD', 'USD'), ('EUR', 'EUR')], default='UZS')
    business_hours_start = StringField('Business Hours Start', default='09:00')
    business_hours_end = StringField('Business Hours End', default='18:00')
    tax_rate = StringField('Tax Rate (%)', default='0')
    bonus_rate = StringField('Bonus Rate (%)', default='0')
    business_type = SelectField('Business Type', choices=[
        ('retail', 'Retail'),
        ('restaurant', 'Restaurant'),
        ('service', 'Service'),
        ('manufacturing', 'Manufacturing'),
        ('other', 'Other')
    ], default='retail')
    enable_recipes = BooleanField('Enable Recipe Management')
    enable_table_management = BooleanField('Enable Table Management')
    auto_calculate_profit = BooleanField('Auto Calculate Profit', default=True)
    submit = SubmitField('Save Settings')

class CreateKPIForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    sales_amount = StringField('Sales Amount', default='0')
    customers_served = StringField('Customers Served', default='0')
    errors_count = StringField('Errors Count', default='0')
    returns_count = StringField('Returns Count', default='0')
    attendance_score = StringField('Attendance Score (%)', default='100')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save KPI')

class CreateShiftForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int)
    planned_start = DateTimeLocalField('Start Time', validators=[DataRequired()])
    planned_end = DateTimeLocalField('End Time', validators=[DataRequired()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Create Shift')

class BudgetForm(FlaskForm):
    name = StringField('Budget Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    budget_type = SelectField('Budget Type', choices=[
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired()])
    month = SelectField('Month', choices=[(i, f'{i:02d}') for i in range(1, 13)])
    quarter = SelectField('Quarter', choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    submit = SubmitField('Create Budget')

class BudgetItemForm(FlaskForm):
    category = StringField('Category', validators=[DataRequired()])
    subcategory = StringField('Subcategory')
    budgeted_amount = FloatField('Budgeted Amount', validators=[DataRequired()])
    item_type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Add Item')

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired()])
    contact_person = StringField('Contact Person')
    email = StringField('Email')
    phone = StringField('Phone')
    address = TextAreaField('Address')
    category = StringField('Product Category')
    payment_terms = StringField('Payment Terms')
    rating = SelectField('Rating', choices=[(i, f'{i} stars') for i in range(1, 6)], coerce=int)
    submit = SubmitField('Save Supplier')

class PurchaseOrderForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    order_number = StringField('Order Number', validators=[DataRequired()])
    expected_delivery_date = DateField('Expected Delivery Date')
    notes = TextAreaField('Notes')
    submit = SubmitField('Create Order')

class PurchaseOrderItemForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    quantity = FloatField('Quantity', validators=[DataRequired()])
    unit_price = FloatField('Unit Price', validators=[DataRequired()])
    submit = SubmitField('Add Item')

class SalesGoalForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    goal_type = SelectField('Goal Type', choices=[
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], validators=[DataRequired()])
    period_year = IntegerField('Year', validators=[DataRequired()])
    period_month = SelectField('Month', choices=[(i, f'{i:02d}') for i in range(1, 13)])
    period_quarter = SelectField('Quarter', choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    target_amount = FloatField('Target Amount', validators=[DataRequired()])
    target_quantity = IntegerField('Target Quantity')
    notes = TextAreaField('Notes')
    submit = SubmitField('Set Goal')

class CampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    campaign_type = SelectField('Campaign Type', choices=[
        ('marketing', 'Marketing Campaign'),
        ('project', 'Project'),
        ('event', 'Event'),
        ('sales', 'Sales Campaign'),
        ('training', 'Training Program'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    budget = FloatField('Budget')
    start_date = DateField('Start Date')
    end_date = DateField('End Date')
    manager_id = SelectField('Campaign Manager', coerce=int)
    tags = StringField('Tags (comma separated)')
    notes = TextAreaField('Notes')
    submit = SubmitField('Create Campaign')

class CampaignExpenseForm(FlaskForm):
    category = SelectField('Category', choices=[
        ('marketing', 'Marketing'),
        ('salaries', 'Salaries'),
        ('materials', 'Materials'),
        ('travel', 'Travel'),
        ('equipment', 'Equipment'),
        ('software', 'Software'),
        ('advertising', 'Advertising'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    expense_date = DateField('Expense Date', validators=[DataRequired()])
    vendor = StringField('Vendor')
    submit = SubmitField('Add Expense')

class CampaignRevenueForm(FlaskForm):
    source = SelectField('Revenue Source', choices=[
        ('sales', 'Sales'),
        ('sponsorship', 'Sponsorship'),
        ('donations', 'Donations'),
        ('grants', 'Grants'),
        ('investments', 'Investments'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    revenue_date = DateField('Revenue Date', validators=[DataRequired()])
    customer_id = SelectField('Customer', coerce=int)
    invoice_number = StringField('Invoice Number')
    submit = SubmitField('Add Revenue')

class CampaignTaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    assigned_to = SelectField('Assigned To', coerce=int)
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    estimated_hours = FloatField('Estimated Hours')
    due_date = DateField('Due Date')
    submit = SubmitField('Create Task')

class CampaignTimeEntryForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    task_id = SelectField('Task', coerce=int)
    date = DateField('Date', validators=[DataRequired()])
    hours = FloatField('Hours', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Log Time')

class CreateReportForm(FlaskForm):
    title = StringField('Report Title', validators=[DataRequired()])
    report_type = SelectField('Report Type', choices=[
        ('sales', 'Sales Report'),
        ('expenses', 'Expenses Report'),
        ('employees', 'Employees Report'),
        ('payroll', 'Payroll Report'),
        ('profit', 'Profit & Loss Report')
    ], validators=[DataRequired()])
    date_from = DateField('From Date', validators=[DataRequired()])
    date_to = DateField('To Date', validators=[DataRequired()])
    send_to_owner = BooleanField('Send to Business Owner')
    submit = SubmitField('Generate Report')

@web_bp.route('/shifts/<int:biz_id>')
def manage_shifts(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get current week shifts
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    shifts = Shift.query.filter(
        Shift.business_id == biz_id,
        Shift.planned_start >= week_start,
        Shift.planned_end <= week_end + timedelta(days=1)
    ).order_by(Shift.planned_start).all()
    
    employees = Employee.query.filter_by(business_id=biz_id).all()
    return render_template('manage_shifts.html', business=business, shifts=shifts, employees=employees, week_start=week_start, week_end=week_end, user=user)

@web_bp.route('/roles/assign/<int:biz_id>', methods=['GET', 'POST'])
def assign_role(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_roles'))
    
    form = AssignRoleForm()
    # Populate choices
    users = User.query.all()  # In real app, filter by users who can be assigned
    roles = Role.query.filter_by(business_id=biz_id).all()
    form.user_id.choices = [(u.id, u.username) for u in users]
    form.role_id.choices = [(r.id, r.name) for r in roles]
    
    if form.validate_on_submit():
        # Check if user already has a role in this business
        existing = UserBusinessRole.query.filter_by(user_id=form.user_id.data, business_id=biz_id).first()
        if existing:
            existing.role_id = form.role_id.data
            existing.assigned_by = user_id
            existing.assigned_at = datetime.utcnow()
        else:
            ubr = UserBusinessRole(
                user_id=form.user_id.data,
                business_id=biz_id,
                role_id=form.role_id.data,
                assigned_by=user_id
            )
            db.session.add(ubr)
        db.session.commit()
        flash('Role assigned successfully', 'success')
        return redirect(url_for('web.business_roles', biz_id=biz_id))
    
    return render_template('assign_role.html', form=form, business=business, user=user)

@web_bp.route('/shifts/create/<int:biz_id>', methods=['GET', 'POST'])
def create_shift(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_shifts', biz_id=biz_id))
    
    form = CreateShiftForm()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    branches = Branch.query.filter_by(business_id=biz_id).all()
    
    form.employee_id.choices = [(e.id, e.name) for e in employees]
    form.branch_id.choices = [(b.id, b.name) for b in branches]
    form.branch_id.choices.insert(0, (0, 'No specific branch'))
    
    if form.validate_on_submit():
        shift = Shift(
            business_id=biz_id,
            employee_id=form.employee_id.data,
            branch_id=form.branch_id.data if form.branch_id.data != 0 else None,
            planned_start=form.planned_start.data,
            planned_end=form.planned_end.data,
            notes=form.notes.data
        )
        db.session.add(shift)
        db.session.commit()
        flash('Shift created successfully', 'success')
        return redirect(url_for('web.manage_shifts', biz_id=biz_id))
    
    return render_template('create_shift.html', form=form, business=business, user=user)

@web_bp.route('/shifts/clock-in/<int:shift_id>', methods=['POST'])
def clock_in(shift_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    shift = Shift.query.get(shift_id)
    if not shift:
        return jsonify({'error': 'Shift not found'}), 404
    
    # Check if employee or admin
    user_id = session['user_id']
    user = User.query.get(user_id)
    employee = Employee.query.filter_by(user_id=user_id, business_id=shift.business_id).first()
    
    if not (user.role == 'admin' or (employee and employee.id == shift.employee_id)):
        return jsonify({'error': 'Access denied'}), 403
    
    if shift.status != 'scheduled':
        return jsonify({'error': 'Cannot clock in for this shift'}), 400
    
    shift.start_time = datetime.utcnow()
    shift.status = 'in_progress'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Clocked in successfully'})

@web_bp.route('/shifts/clock-out/<int:shift_id>', methods=['POST'])
def clock_out(shift_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    shift = Shift.query.get(shift_id)
    if not shift:
        return jsonify({'error': 'Shift not found'}), 404
    
    # Check if employee or admin
    user_id = session['user_id']
    user = User.query.get(user_id)
    employee = Employee.query.filter_by(user_id=user_id, business_id=shift.business_id).first()
    
    if not (user.role == 'admin' or (employee and employee.id == shift.employee_id)):
        return jsonify({'error': 'Access denied'}), 403
    
    if shift.status != 'in_progress':
        return jsonify({'error': 'Cannot clock out for this shift'}), 400
    
    shift.end_time = datetime.utcnow()
    shift.status = 'completed'
    db.session.commit()
    
    # Calculate duration
    duration = shift.end_time - shift.start_time
    hours = duration.total_seconds() / 3600
    
    return jsonify({'success': True, 'message': f'Clocked out successfully. Worked {hours:.2f} hours'})

@web_bp.route('/employee/<int:emp_id>/time-tracking')
def employee_time_tracking(emp_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    employee = Employee.query.get(emp_id)
    
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('web.dashboard'))
    
    business = Business.query.get(employee.business_id)
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get monthly stats
    current_month = datetime.utcnow().replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    
    shifts = Shift.query.filter(
        Shift.employee_id == emp_id,
        Shift.start_time >= current_month,
        Shift.end_time < next_month,
        Shift.status == 'completed'
    ).all()
    
    total_hours = sum((s.end_time - s.start_time).total_seconds() / 3600 for s in shifts)
    total_shifts = len(shifts)
    
    return render_template('employee_time_tracking.html', employee=employee, business=business, shifts=shifts, total_hours=total_hours, total_shifts=total_shifts, user=user)

@web_bp.route('/kpi/<int:biz_id>')
def manage_kpi(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    employees = Employee.query.filter_by(business_id=biz_id).all()
    # Get KPIs for current month
    current_month = datetime.utcnow().replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    
    kpis = KPI.query.filter(
        KPI.business_id == biz_id,
        KPI.date >= current_month,
        KPI.date < next_month
    ).order_by(KPI.date.desc()).all()
    
    return render_template('manage_kpi.html', business=business, employees=employees, kpis=kpis, user=user)

@web_bp.route('/kpi/create/<int:biz_id>', methods=['GET', 'POST'])
def create_kpi(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_kpi', biz_id=biz_id))
    
    form = CreateKPIForm()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    form.employee_id.choices = [(e.id, e.name) for e in employees]
    
    if form.validate_on_submit():
        # Calculate productivity score
        sales_score = float(form.sales_amount.data) / 1000 * 40  # Max 40 points
        customer_score = int(form.customers_served.data) * 2  # 2 points per customer
        error_penalty = int(form.errors_count.data) * 5  # 5 points penalty per error
        return_penalty = int(form.returns_count.data) * 10  # 10 points penalty per return
        attendance_score = float(form.attendance_score.data)
        
        productivity_score = max(0, sales_score + customer_score - error_penalty - return_penalty + attendance_score)
        
        kpi = KPI(
            employee_id=form.employee_id.data,
            business_id=biz_id,
            date=form.date.data,
            sales_amount=float(form.sales_amount.data),
            customers_served=int(form.customers_served.data),
            errors_count=int(form.errors_count.data),
            returns_count=int(form.returns_count.data),
            attendance_score=float(form.attendance_score.data),
            productivity_score=productivity_score,
            notes=form.notes.data
        )
        db.session.add(kpi)
        db.session.commit()
        flash('KPI recorded successfully', 'success')
        return redirect(url_for('web.manage_kpi', biz_id=biz_id))
    
    return render_template('create_kpi.html', form=form, business=business, user=user)

@web_bp.route('/employee/<int:emp_id>/kpi')
def employee_kpi(emp_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    employee = Employee.query.get(emp_id)
    
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('web.dashboard'))
    
    business = Business.query.get(employee.business_id)
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get KPIs for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    kpis = KPI.query.filter(
        KPI.employee_id == emp_id,
        KPI.date >= thirty_days_ago
    ).order_by(KPI.date.desc()).all()
    
    # Calculate averages
    if kpis:
        avg_sales = sum(k.sales_amount for k in kpis) / len(kpis)
        avg_customers = sum(k.customers_served for k in kpis) / len(kpis)
        avg_productivity = sum(k.productivity_score for k in kpis) / len(kpis)
    else:
        avg_sales = avg_customers = avg_productivity = 0
    
    return render_template('employee_kpi.html', employee=employee, business=business, kpis=kpis, 
                          avg_sales=avg_sales, avg_customers=avg_customers, avg_productivity=avg_productivity, user=user)

@web_bp.route('/notifications/<int:biz_id>')
def manage_notifications(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    notifications = Notification.query.filter_by(business_id=biz_id).order_by(Notification.created_at.desc()).limit(50).all()
    return render_template('manage_notifications.html', business=business, notifications=notifications, user=user)

@web_bp.route('/alerts/<int:biz_id>')
def manage_alerts(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    alert_rules = AlertRule.query.filter_by(business_id=biz_id).all()
    debt_reminders = DebtReminder.query.filter_by(business_id=biz_id).all()
    return render_template('manage_alerts.html', business=business, alert_rules=alert_rules, debt_reminders=debt_reminders, user=user)

@web_bp.route('/alerts/create/<int:biz_id>', methods=['GET', 'POST'])
def create_alert_rule(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_alerts', biz_id=biz_id))
    
    form = AlertRuleForm()
    if form.validate_on_submit():
        # Check if rule already exists
        existing = AlertRule.query.filter_by(business_id=biz_id, alert_type=form.alert_type.data).first()
        if existing:
            existing.telegram_enabled = form.telegram_enabled.data
            existing.email_enabled = form.email_enabled.data
        else:
            rule = AlertRule(
                business_id=biz_id,
                alert_type=form.alert_type.data,
                condition={},  # Default empty condition
                telegram_enabled=form.telegram_enabled.data,
                email_enabled=form.email_enabled.data
            )
            db.session.add(rule)
        db.session.commit()
        flash('Alert rule saved successfully', 'success')
        return redirect(url_for('web.manage_alerts', biz_id=biz_id))
    
    return render_template('create_alert_rule.html', form=form, business=business, user=user)

@web_bp.route('/debts/<int:biz_id>', methods=['GET', 'POST'])
def manage_debts(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = DebtReminderForm()
    if form.validate_on_submit():
        debt = DebtReminder(
            business_id=biz_id,
            debtor_name=form.debtor_name.data,
            debtor_type=form.debtor_type.data,
            amount=float(form.amount.data),
            due_date=form.due_date.data,
            description=form.description.data
        )
        db.session.add(debt)
        db.session.commit()
        flash('Debt reminder added successfully', 'success')
        return redirect(url_for('web.manage_debts', biz_id=biz_id))
    
    debts = DebtReminder.query.filter_by(business_id=biz_id).order_by(DebtReminder.due_date).all()
    return render_template('manage_debts.html', form=form, business=business, debts=debts, user=user)

@web_bp.route('/debts/mark-paid/<int:debt_id>')
def mark_debt_paid(debt_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    debt = DebtReminder.query.get(debt_id)
    if not debt:
        flash('Debt not found', 'error')
        return redirect(url_for('web.dashboard'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(debt.business_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    debt.status = 'paid'
    db.session.commit()
    flash('Debt marked as paid', 'success')
    return redirect(url_for('web.manage_debts', biz_id=debt.business_id))

@web_bp.route('/api/alerts/toggle/<int:rule_id>', methods=['POST'])
def toggle_alert_rule(rule_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    rule = AlertRule.query.get(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(rule.business_id)

    if not business or (business.owner_id != user_id and user.role != 'admin'):
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    rule.is_active = data.get('active', False)
    db.session.commit()

    return jsonify({'success': True})

@web_bp.route('/api/notifications/recent')
def get_recent_notifications():
    if 'user_id' not in session:
        return jsonify({'notifications': []}), 200

    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return jsonify({'notifications': []}), 200

    if user.role == 'admin':
        # Admin sees all notifications
        notifications = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    else:
        # Regular users see notifications for their businesses
        businesses = Business.query.filter_by(owner_id=user_id).all()
        business_ids = [b.id for b in businesses]
        notifications = Notification.query.filter(
            Notification.business_id.in_(business_ids)
        ).order_by(Notification.created_at.desc()).limit(10).all()

    notification_data = []
    for n in notifications:
        notification_data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'priority': n.priority,
            'created_at': n.created_at.isoformat(),
            'status': n.status
        })

    return jsonify({'notifications': notification_data})

@web_bp.route('/recipes/<int:biz_id>')
def manage_recipes(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    recipes = Recipe.query.filter_by(business_id=biz_id).all()
    return render_template('manage_recipes.html', business=business, recipes=recipes, user=user)

@web_bp.route('/recipes/create/<int:biz_id>', methods=['GET', 'POST'])
def create_recipe(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_recipes', biz_id=biz_id))
    
    form = RecipeForm()
    if form.validate_on_submit():
        recipe = Recipe(
            business_id=biz_id,
            name=form.name.data,
            description=form.description.data,
            selling_price=float(form.selling_price.data),
            category=form.category.data
        )
        db.session.add(recipe)
        db.session.commit()
        
        # Audit log
        AuditService.log_data_change(biz_id, user_id, 'recipe', recipe.id, 'create',
                                   None, {'name': recipe.name, 'price': recipe.selling_price})
        
        flash('Recipe created successfully', 'success')
        return redirect(url_for('web.manage_recipes', biz_id=biz_id))
    
    return render_template('create_recipe.html', form=form, business=business, user=user)

@web_bp.route('/recipes/<int:recipe_id>/ingredients', methods=['GET', 'POST'])
def manage_recipe_ingredients(recipe_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('web.dashboard'))
    
    business = Business.query.get(recipe.business_id)
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = RecipeIngredientForm()
    products = Product.query.filter_by(business_id=business.id).all()
    form.product_id.choices = [(p.id, p.name) for p in products]
    
    if form.validate_on_submit():
        ingredient = RecipeIngredient(
            recipe_id=recipe_id,
            product_id=form.product_id.data,
            quantity=float(form.quantity.data),
            unit=form.unit.data
        )
        db.session.add(ingredient)
        
        # Recalculate recipe cost
        recipe.cost_price = RecipeService.calculate_recipe_cost(recipe)
        db.session.commit()
        
        flash('Ingredient added successfully', 'success')
        return redirect(url_for('web.manage_recipe_ingredients', recipe_id=recipe_id))
    
    ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe_id).all()
    return render_template('manage_recipe_ingredients.html', recipe=recipe, business=business,
                          form=form, ingredients=ingredients, user=user)

@web_bp.route('/settings/<int:biz_id>', methods=['GET', 'POST'])
@business_access_required
def business_settings(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get or create settings
    settings = BusinessSettings.query.filter_by(business_id=biz_id).first()
    if not settings:
        settings = BusinessSettings(business_id=biz_id)
        db.session.add(settings)
        db.session.commit()
    
    form = BusinessSettingsForm(obj=settings)
    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        
        # Audit log
        AuditService.log_data_change(biz_id, user_id, 'business_settings', settings.id, 'update',
                                   None, {'currency': settings.currency, 'business_type': settings.business_type})
        
        flash('Settings saved successfully', 'success')
        return redirect(url_for('web.business_settings', biz_id=biz_id))
    
    return render_template('business_settings.html', form=form, business=business, settings=settings, user=user)

@web_bp.route('/profit/<int:biz_id>')
def view_profit(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Calculate current month profit
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)
    
    profit_data = ProfitCalculator.calculate_business_profit(biz_id, start_of_month, today)
    
    # Calculate employee shares
    employees = Employee.query.filter_by(business_id=biz_id, is_active=True).all()
    employee_shares = []
    
    for employee in employees:
        share_data = ProfitCalculator.calculate_employee_share(biz_id, employee.id, start_of_month, today)
        if share_data['share_percentage'] > 0:
            employee_shares.append(share_data)
    
    return render_template('view_profit.html', business=business, profit_data=profit_data, employee_shares=employee_shares, user=user)

@web_bp.route('/audit/<int:biz_id>')
def view_audit_log(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get recent audit logs
    audit_logs = AuditLog.query.filter_by(business_id=biz_id).order_by(
        AuditLog.timestamp.desc()
    ).limit(100).all()
    
    return render_template('audit_log.html', business=business, audit_logs=audit_logs, user=user)

@web_bp.route('/projects/<int:biz_id>')
def manage_projects(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    projects = Project.query.filter_by(business_id=biz_id).order_by(Project.created_at.desc()).all()
    customers = Customer.query.filter_by(business_id=biz_id).all()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    
    return render_template('manage_projects.html', business=business, projects=projects, customers=customers, employees=employees, user=user)

@web_bp.route('/projects/create/<int:biz_id>', methods=['GET', 'POST'])
def create_project(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_projects', biz_id=biz_id))
    
    form = ProjectForm()
    customers = Customer.query.filter_by(business_id=biz_id).all()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    
    form.client_id.choices = [(c.id, f"{c.first_name} {c.last_name}") for c in customers]
    form.client_id.choices.insert(0, (0, 'No client'))
    form.manager_id.choices = [(e.id, f"{e.first_name} {e.last_name}") for e in employees]
    
    if form.validate_on_submit():
        project = Project(
            business_id=biz_id,
            name=form.name.data,
            description=form.description.data,
            client_id=form.client_id.data if form.client_id.data != 0 else None,
            manager_id=form.manager_id.data,
            start_date=form.start_date.data,
            deadline=form.deadline.data,
            budget=float(form.budget.data) if form.budget.data else 0
        )
        db.session.add(project)
        db.session.commit()
        
        AuditService.log_data_change(biz_id, user_id, 'project', project.id, 'create',
                                   None, {'name': project.name, 'budget': project.budget})
        
        flash('Project created successfully', 'success')
        return redirect(url_for('web.manage_projects', biz_id=biz_id))
    
    return render_template('create_project.html', form=form, business=business, user=user)

@web_bp.route('/customers/<int:biz_id>', methods=['GET', 'POST'])
def manage_customers(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            business_id=biz_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            company=form.company.data,
            status=form.status.data,
            source=form.source.data
        )
        db.session.add(customer)
        db.session.commit()
        
        # Calculate initial lifetime value
        CRMService.calculate_customer_lifetime_value(customer.id)
        
        flash('Customer added successfully', 'success')
        return redirect(url_for('web.manage_customers', biz_id=biz_id))
    
    customers = Customer.query.filter_by(business_id=biz_id).order_by(Customer.created_at.desc()).all()
    return render_template('manage_customers.html', form=form, business=business, customers=customers, user=user)

@web_bp.route('/invoices/<int:biz_id>', methods=['GET', 'POST'])
def manage_invoices(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = InvoiceForm()
    customers = Customer.query.filter_by(business_id=biz_id).all()
    projects = Project.query.filter_by(business_id=biz_id).all()
    
    form.customer_id.choices = [(c.id, f"{c.first_name} {c.last_name}") for c in customers]
    form.project_id.choices = [(p.id, p.name) for p in projects]
    form.project_id.choices.insert(0, (0, 'No project'))
    
    if form.validate_on_submit():
        invoice = Invoice(
            business_id=biz_id,
            customer_id=form.customer_id.data,
            project_id=form.project_id.data if form.project_id.data != 0 else None,
            invoice_number=InvoiceService.generate_invoice_number(biz_id),
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            discount_amount=float(form.discount_amount.data)
        )
        db.session.add(invoice)
        db.session.commit()
        
        flash('Invoice created successfully', 'success')
        return redirect(url_for('web.manage_invoices', biz_id=biz_id))
    
    invoices = Invoice.query.filter_by(business_id=biz_id).order_by(Invoice.created_at.desc()).all()
    return render_template('manage_invoices.html', form=form, business=business, invoices=invoices, user=user)

@web_bp.route('/cashflow/<int:biz_id>', methods=['GET', 'POST'])
def manage_cash_flow(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = CashFlowForm()
    customers = Customer.query.filter_by(business_id=biz_id).all()
    projects = Project.query.filter_by(business_id=biz_id).all()
    
    form.related_customer_id.choices = [(c.id, f"{c.first_name} {c.last_name}") for c in customers]
    form.related_customer_id.choices.insert(0, (0, 'No customer'))
    form.related_project_id.choices = [(p.id, p.name) for p in projects]
    form.related_project_id.choices.insert(0, (0, 'No project'))
    
    if form.validate_on_submit():
        cash_flow = CashFlow(
            business_id=biz_id,
            transaction_type=form.transaction_type.data,
            category=form.category.data,
            subcategory=form.subcategory.data,
            amount=float(form.amount.data),
            description=form.description.data,
            transaction_date=form.transaction_date.data,
            related_customer_id=form.related_customer_id.data if form.related_customer_id.data != 0 else None,
            related_project_id=form.related_project_id.data if form.related_project_id.data != 0 else None,
            created_by=user_id
        )
        db.session.add(cash_flow)
        db.session.commit()
        
        flash('Transaction added successfully', 'success')
        return redirect(url_for('web.manage_cash_flow', biz_id=biz_id))
    
    # Get current month cash flow
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)
    
    cash_flow_data = CashFlowService.get_business_cash_flow(biz_id, start_of_month, today)
    
    return render_template('manage_cash_flow.html', form=form, business=business, cash_flow_data=cash_flow_data, user=user)

@web_bp.route('/analytics/<int:biz_id>')
def business_analytics(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get analytics data
    if ANALYTICS_AVAILABLE:
        revenue_trends = BusinessAnalytics.get_revenue_trends(biz_id)
        profit_margins = BusinessAnalytics.calculate_profit_margins(biz_id)
        top_performers = BusinessAnalytics.get_top_performers(biz_id, 'revenue')
        insights = BusinessAnalytics.get_business_insights(biz_id)
    else:
        # Analytics not available (pandas/sklearn not installed)
        revenue_trends = []
        profit_margins = []
        top_performers = []
        insights = {"note": "Analytics features require additional dependencies (pandas, scikit-learn)"}
    
    return render_template('business_analytics.html', business=business, user=user,
                          revenue_trends=revenue_trends, profit_margins=profit_margins,
                          top_performers=top_performers, insights=insights)

@web_bp.route('/forecast/<int:biz_id>')
def revenue_forecast(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    forecast_error = None
    try:
        forecast = BusinessAnalytics.forecast_revenue(biz_id)
    except Exception as e:
        forecast = None
        forecast_error = str(e)
    
    return render_template('revenue_forecast.html', business=business, forecast=forecast, forecast_error=forecast_error, user=user)

@web_bp.route('/campaigns/<int:biz_id>', methods=['GET', 'POST'])
def manage_campaigns(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = MarketingCampaignForm()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    form.manager_id.choices = [(0, 'No Manager')] + [(e.id, e.name) for e in employees]
    if form.validate_on_submit():
        campaign = MarketingCampaign(
            business_id=biz_id,
            name=form.name.data,
            description=form.description.data,
            campaign_type=form.campaign_type.data,
            platform=form.platform.data,
            target_audience=form.target_audience.data,
            budget=float(form.budget.data) if form.budget.data else 0,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            priority=form.priority.data,
            manager_id=form.manager_id.data if form.manager_id.data != 0 else None
        )
        db.session.add(campaign)
        db.session.commit()
        
        flash('Campaign created successfully', 'success')
        return redirect(url_for('web.manage_campaigns', biz_id=biz_id))
    
    campaigns = MarketingCampaign.query.filter_by(business_id=biz_id).order_by(MarketingCampaign.created_at.desc()).all()
    
    # Calculate ROI for active campaigns
    for campaign in campaigns:
        if campaign.status == 'active':
            MarketingService.calculate_campaign_roi(campaign.id)
    
    return render_template('manage_campaigns.html', form=form, business=business, campaigns=campaigns, user=user)

@web_bp.route('/campaign/<int:campaign_id>/performance')
def campaign_performance(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    campaign = MarketingCampaign.query.get(campaign_id)
    if not campaign:
        flash('Campaign not found', 'error')
        return redirect(url_for('web.dashboard'))
    
    business = Business.query.get(campaign.business_id)
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    performance_data = MarketingService.get_campaign_performance(campaign_id)
    roi_data = MarketingService.calculate_campaign_roi(campaign_id)
    
    return render_template('campaign_performance.html', campaign=campaign, business=business,
                          performance_data=performance_data, roi_data=roi_data, user=user)

@web_bp.route('/contracts/<int:biz_id>', methods=['GET', 'POST'])
def manage_contracts(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = ContractForm()
    templates = ContractTemplate.query.filter_by(is_active=True).all()
    form.template_id.choices = [(t.id, t.template_name) for t in templates]
    form.template_id.choices.insert(0, (0, 'No template'))
    
    if form.validate_on_submit():
        # Generate contract content
        contract_data = {
            'party_a_name': business.name,
            'party_b_name': form.party_b_name.data,
            'effective_date': form.effective_date.data.strftime('%Y-%m-%d'),
            'contract_value': form.contract_value.data,
            'currency': form.currency.data
        }
        
        content = ""
        if form.template_id.data != 0:
            content = ContractService.generate_contract_from_template(form.template_id.data, contract_data)
        else:
            content = f"Contract between {business.name} and {form.party_b_name.data}"
        
        contract = Contract(
            business_id=biz_id,
            template_id=form.template_id.data if form.template_id.data != 0 else None,
            party_b_name=form.party_b_name.data,
            party_b_representative=form.party_b_representative.data,
            title=form.title.data,
            content=content,
            effective_date=form.effective_date.data,
            expiry_date=form.expiry_date.data,
            contract_value=float(form.contract_value.data) if form.contract_value.data else 0,
            payment_terms=form.payment_terms.data,
            currency=form.currency.data,
            auto_renewal=form.auto_renewal.data,
            renewal_period_months=form.renewal_period_months.data,
            created_by=user_id
        )
        db.session.add(contract)
        db.session.commit()
        
        flash('Contract created successfully', 'success')
        return redirect(url_for('web.manage_contracts', biz_id=biz_id))
    
    contracts = Contract.query.filter_by(business_id=biz_id).order_by(Contract.created_at.desc()).all()
    
    # Check for expiring contracts
    expiring_contracts = ContractService.check_expiring_contracts()
    expiring_ids = [c['contract_id'] for c in expiring_contracts]
    
    return render_template('manage_contracts.html', form=form, business=business, 
                          contracts=contracts, expiring_ids=expiring_ids, user=user)

@web_bp.route('/tax-calculator')
def tax_calculator():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        businesses = Business.query.all()
    else:
        businesses = Business.query.filter_by(owner_id=user_id).all()
    
    return render_template('tax_calculator.html', 
                         businesses=businesses,
                         countries=TaxService.get_available_countries(),
                         business_types=TaxService.get_business_types(),
                         user=user,
                         business_type_service=BusinessTypeService)

@web_bp.route('/tax-calculator/calculate', methods=['POST'])
@csrf_exempt_route
def calculate_tax():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        amount = data.get('amount', 0)
        country = data.get('country', 'UZ')
        business_type = data.get('business_type', 'retail')
        custom_rate = data.get('custom_rate')
        
        if not isinstance(amount, (int, float)) or amount <= 0:
            return jsonify({'error': 'Amount must be a positive number'}), 400
            
        if custom_rate and not isinstance(custom_rate, (int, float)):
            custom_rate = None
            
        tax_amount = TaxService.calculate_tax(amount, country, business_type, custom_rate)
        total_amount = amount + tax_amount
        
        return jsonify({
            'tax_amount': round(tax_amount, 2),
            'total_amount': round(total_amount, 2),
            'tax_rate': custom_rate if custom_rate else TaxService.get_tax_rate(country, business_type)
        })
        
    except Exception as e:
        print(f"Tax calculation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@web_bp.route('/currency-converter')
def currency_converter():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    return render_template('currency_converter.html', 
                         currencies=CurrencyService.get_supported_currencies(), user=user)

@web_bp.route('/currency-converter/convert', methods=['POST'])
@csrf_exempt_route
def convert_currency():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        amount = data.get('amount', 0)
        from_currency = data.get('from_currency', 'USD')
        to_currency = data.get('to_currency', 'UZS')
        
        if not isinstance(amount, (int, float)) or amount <= 0:
            return jsonify({'error': 'Amount must be a positive number'}), 400
            
        converted_amount = CurrencyService.convert_currency(amount, from_currency, to_currency)
        rate = CurrencyService.get_exchange_rate(from_currency, to_currency)
        
        return jsonify({
            'converted_amount': round(converted_amount, 2),
            'exchange_rate': round(rate, 4),
            'formatted_result': CurrencyService.format_currency(converted_amount, to_currency)
        })
    except Exception as e:
        print(f"Currency conversion error: {e}")
        return jsonify({'error': 'Conversion failed'}), 500

@web_bp.route('/currency-rates/update')
def update_currency_rates():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    try:
        CurrencyService.update_currency_rates()
        flash('Currency rates updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating currency rates: {str(e)}', 'error')
    
    return redirect(url_for('web.currency_converter'))

@web_bp.route('/currencies')
def currency_rates():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    try:
        # Update currency rates
        CurrencyService.update_currency_rates()
        
        # Get latest rates
        today = datetime.utcnow().date()
        rates = CurrencyRate.query.filter_by(date=today).all()
        
        return render_template('currency_rates.html', rates=rates, user=user)
    except Exception as e:
        # If there's a database error, rollback and try again
        db.session.rollback()
        flash(f'Error loading currency rates: {str(e)}', 'error')
        return redirect(url_for('web.dashboard'))

@web_bp.route('/users/<int:biz_id>', methods=['GET', 'POST'])
@business_access_required
def manage_users(biz_id):
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    form = CreateUserForm()
    business_roles = Role.query.filter_by(business_id=biz_id).all()
    form.business_role_id.choices = [(r.id, r.name) for r in business_roles]
    form.business_role_id.choices.insert(0, (0, 'No specific role'))
    
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'error')
            return redirect(url_for('web.manage_users', biz_id=biz_id))
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'error')
            return redirect(url_for('web.manage_users', biz_id=biz_id))
        
        # Create new user
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            role=form.role_type.data
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Assign business role if selected
        if form.business_role_id.data != 0:
            business_role_assignment = UserBusinessRole(
                user_id=new_user.id,
                business_id=biz_id,
                role_id=form.business_role_id.data,
                assigned_by=user_id
            )
            db.session.add(business_role_assignment)
            db.session.commit()
        
        flash(f'User {new_user.username} created successfully with role {form.role_type.data}', 'success')
        return redirect(url_for('web.manage_users', biz_id=biz_id))
    
    # Get all users for this business (users who have access or were created for this business)
    business_users = []
    
    # Get users assigned to business roles
    role_assignments = UserBusinessRole.query.filter_by(business_id=biz_id).all()
    for assignment in role_assignments:
        if assignment.user not in business_users:
            business_users.append(assignment.user)
    
    # Include business owner if not already included
    business_owner = User.query.get(business.owner_id)
    if business_owner and business_owner not in business_users:
        business_users.append(business_owner)
    
    # Include admin users (they have access to all businesses)
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        if admin not in business_users:
            business_users.append(admin)
    
    # Also include recently created users that might not have business roles yet
    # This helps with the case where a user was created but business role wasn't assigned
    recent_users = User.query.filter(User.created_at >= business.created_at).limit(50).all()
    for recent_user in recent_users:
        if recent_user not in business_users:
            business_users.append(recent_user)
    
    return render_template('manage_users.html', form=form, business=business, users=business_users, user=user)

@web_bp.route('/analytics/<int:biz_id>')
def business_analytics_dashboard(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Temporarily allow all logged-in users to access analytics
    print(f"Debug: User {user_id} accessing analytics for business {biz_id}")
    
    business = Business.query.get(biz_id)
    if not business:
        print(f"Debug: Business {biz_id} not found")
        flash('Business not found', 'error')
        return redirect(url_for('web.dashboard'))
    
    print(f"Debug: Access granted for user {user_id} to business {biz_id}")
    
    # Get comprehensive analytics data
    if ANALYTICS_AVAILABLE:
        try:
            revenue_trends = BusinessAnalytics.get_revenue_trends(biz_id)
        except Exception as e:
            print(f"Error getting revenue trends: {e}")
            revenue_trends = []
        
        try:
            profit_margins = BusinessAnalytics.calculate_profit_margins(biz_id)
        except Exception as e:
            print(f"Error calculating profit margins: {e}")
            profit_margins = []
        
        try:
            top_products = BusinessAnalytics.get_top_performers(biz_id, 'revenue')
        except Exception as e:
            print(f"Error getting top products: {e}")
            top_products = []
        
        try:
            top_employees = BusinessAnalytics.get_top_performers(biz_id, 'employees')
        except Exception as e:
            print(f"Error getting top employees: {e}")
            top_employees = []
        
        try:
            insights = BusinessAnalytics.get_business_insights(biz_id)
        except Exception as e:
            print(f"Error getting insights: {e}")
            insights = {}
    else:
        # Analytics not available (pandas/sklearn not installed)
        revenue_trends = []
        profit_margins = []
        top_products = []
        top_employees = []
        insights = {"note": "Analytics features require additional dependencies (pandas, scikit-learn)"}
    
    # Get current month profit data
    try:
        today = datetime.utcnow().date()
        start_of_month = today.replace(day=1)
        profit_data = ProfitCalculator.calculate_business_profit(biz_id, start_of_month, today)
    except Exception as e:
        print(f"Error calculating profit: {e}")
        profit_data = None
    
    # Get customer and project counts
    customers = Customer.query.filter_by(business_id=biz_id).all()
    projects = Project.query.filter_by(business_id=biz_id).all()
    
    return render_template('business_analytics_dashboard.html', 
                          business=business, 
                          revenue_trends=revenue_trends,
                          profit_margins=profit_margins,
                          top_products=top_products,
                          top_employees=top_employees,
                          insights=insights,
                          profit_data=profit_data,
                          customers=customers,
                          projects=projects,
                          user=user)

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Regexp(r'.*@gmail\.com$', message="Email must be a Gmail address.")])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    business_name = StringField('Business Name', validators=[DataRequired()])
    business_type_id = SelectField('Business Type', coerce=int, validators=[DataRequired()])
    industry = StringField('Industry')
    country = StringField('Country', default='Uzbekistan')
    currency = SelectField('Currency', choices=[('UZS', 'UZS'), ('USD', 'USD'), ('EUR', 'EUR')], default='UZS')
    submit = SubmitField('Register Business')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateRoleForm(FlaskForm):
    name = StringField('Role Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    # Permissions checkboxes
    view_employees = BooleanField('View Employees')
    manage_employees = BooleanField('Manage Employees')
    view_sales = BooleanField('View Sales')
    manage_sales = BooleanField('Manage Sales')
    view_expenses = BooleanField('View Expenses')
    manage_expenses = BooleanField('Manage Expenses')
    view_reports = BooleanField('View Reports')
    create_reports = BooleanField('Create Reports')
    view_payroll = BooleanField('View Payroll')
    manage_payroll = BooleanField('Manage Payroll')
    submit = SubmitField('Create Role')

class AssignRoleForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Role')

class DebtReminderForm(FlaskForm):
    debtor_name = StringField('Debtor Name', validators=[DataRequired()])
    debtor_type = SelectField('Type', choices=[('customer', 'Customer'), ('supplier', 'Supplier')], validators=[DataRequired()])
    amount = StringField('Amount', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Add Debt Reminder')

class AlertRuleForm(FlaskForm):
    alert_type = SelectField('Alert Type', choices=[
        ('salary_due', 'Salary Due'),
        ('inventory_low', 'Low Inventory'),
        ('debt_overdue', 'Debt Overdue'),
        ('expense_reminder', 'Expense Reminder'),
        ('report_time', 'Report Time')
    ], validators=[DataRequired()])
    telegram_enabled = BooleanField('Enable Telegram')
    email_enabled = BooleanField('Enable Email')
    submit = SubmitField('Save Alert Rule')

@web_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))
    return redirect(url_for('web.login'))

@web_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('web.login'))
        
    user = User.query.get(user_id)
    if not user:
        session.clear()  # Clear invalid session
        return redirect(url_for('web.login'))
    
    if user.role == 'admin':
        businesses = Business.query.all()
        business_ids = [b.id for b in businesses]
    else:
        businesses = Business.query.filter_by(owner_id=user_id).all()
        business_ids = [b.id for b in businesses]
    
    # Calculate total employees for user's businesses
    from app.models import Employee
    total_employees = Employee.query.filter(Employee.business_id.in_(business_ids)).count() if business_ids else 0
    
    # Get top businesses (by creation date for now, since revenue not stored)
    top_businesses = Business.query.order_by(Business.created_at.desc()).limit(5).all()
    
    # Get top users by number of businesses
    top_users = db.session.query(User, func.count(Business.id).label('business_count')).\
        outerjoin(Business, User.id == Business.owner_id).\
        group_by(User.id).\
        order_by(func.count(Business.id).desc()).\
        limit(5).all()
    
    return render_template('dashboard.html', businesses=businesses, user=user, business_type_service=BusinessTypeService, top_businesses=top_businesses, top_users=top_users, total_employees=total_employees)

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            session.permanent = True  # Make session permanent
            flash('Logged in successfully', 'success')
            return redirect(url_for('web.dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html', form=form)

@web_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    # Populate business type choices
    business_types = BusinessType.query.filter_by(is_active=True).all()
    form.business_type_id.choices = [(bt.id, bt.name) for bt in business_types]

    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'error')
            return redirect(url_for('web.register'))
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'error')
            return redirect(url_for('web.register'))

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, role='owner')
        db.session.add(user)
        db.session.commit()

        business = Business(
            owner_id=user.id,
            name=form.business_name.data,
            industry=form.industry.data,
            business_type_id=form.business_type_id.data,
            country=form.country.data,
            currency=form.currency.data
        )
        db.session.add(business)
        db.session.commit()

        session['user_id'] = user.id
        session['role'] = user.role
        session['username'] = user.username
        session.permanent = True  # Make session permanent
        flash('Business registered successfully', 'success')
        return redirect(url_for('web.dashboard'))
    return render_template('register.html', form=form)

@web_bp.route('/roles')
def manage_roles():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        businesses = Business.query.all()
    else:
        businesses = Business.query.filter_by(owner_id=user_id).all()
    
    return render_template('roles.html', businesses=businesses, user=user, business_type_service=BusinessTypeService)

@web_bp.route('/business/<int:biz_id>/roles')
def business_roles(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_roles'))
    
    roles = Role.query.filter_by(business_id=biz_id).all()
    return render_template('business_roles.html', business=business, roles=roles, user=user)

@web_bp.route('/roles/create/<int:biz_id>', methods=['GET', 'POST'])
def create_role(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_roles'))
    
    form = CreateRoleForm()
    if form.validate_on_submit():
        permissions = {
            'view_employees': form.view_employees.data,
            'manage_employees': form.manage_employees.data,
            'view_sales': form.view_sales.data,
            'manage_sales': form.manage_sales.data,
            'view_expenses': form.view_expenses.data,
            'manage_expenses': form.manage_expenses.data,
            'view_reports': form.view_reports.data,
            'create_reports': form.create_reports.data,
            'view_payroll': form.view_payroll.data,
            'manage_payroll': form.manage_payroll.data,
        }
        
        role = Role(
            business_id=biz_id,
            name=form.name.data,
            description=form.description.data,
            permissions=permissions
        )
        db.session.add(role)
        db.session.commit()
        flash('Role created successfully', 'success')
        return redirect(url_for('web.business_roles', biz_id=biz_id))
    
    return render_template('create_role.html', form=form, business=business, user=user)

@web_bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
def edit_role(role_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    role = Role.query.get_or_404(role_id)
    business = Business.query.get(role.business_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.business_roles', biz_id=role.business_id))
    
    form = CreateRoleForm()
    if form.validate_on_submit():
        role.name = form.name.data
        role.description = form.description.data
        role.permissions = {
            'view_employees': form.view_employees.data,
            'manage_employees': form.manage_employees.data,
            'view_sales': form.view_sales.data,
            'manage_sales': form.manage_sales.data,
            'view_expenses': form.view_expenses.data,
            'manage_expenses': form.manage_expenses.data,
            'view_reports': form.view_reports.data,
            'create_reports': form.create_reports.data,
            'view_payroll': form.view_payroll.data,
            'manage_payroll': form.manage_payroll.data,
        }
        db.session.commit()
        flash('Role updated successfully', 'success')
        return redirect(url_for('web.business_roles', biz_id=business.id))
    
    # Pre-fill form with existing data
    form.name.data = role.name
    form.description.data = role.description
    if role.permissions:
        form.view_employees.data = role.permissions.get('view_employees', False)
        form.manage_employees.data = role.permissions.get('manage_employees', False)
        form.view_sales.data = role.permissions.get('view_sales', False)
        form.manage_sales.data = role.permissions.get('manage_sales', False)
        form.view_expenses.data = role.permissions.get('view_expenses', False)
        form.manage_expenses.data = role.permissions.get('manage_expenses', False)
        form.view_reports.data = role.permissions.get('view_reports', False)
        form.create_reports.data = role.permissions.get('create_reports', False)
        form.view_payroll.data = role.permissions.get('view_payroll', False)
        form.manage_payroll.data = role.permissions.get('manage_payroll', False)
    
    return render_template('edit_role.html', form=form, role=role, business=business, user=user)

@web_bp.route('/inventory/<int:biz_id>')
@business_access_required
def manage_inventory(biz_id):
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    inventory_items = InventoryItem.query.filter_by(business_id=biz_id).all()
    low_stock_items = [item for item in inventory_items if item.quantity <= item.min_stock_level]
    
    return render_template('manage_inventory.html', 
                         business=business, 
                         inventory_items=inventory_items,
                         low_stock_items=low_stock_items,
                         form=InventoryItemForm(),
                         user=user)

@web_bp.route('/inventory/<int:biz_id>/add', methods=['GET', 'POST'])
@business_access_required
def add_inventory_item(biz_id):
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    form = InventoryItemForm()
    if form.validate_on_submit():
        item = InventoryItem(
            business_id=biz_id,
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data,
            min_stock_level=form.min_stock_level.data,
            max_stock_level=form.max_stock_level.data,
            location=form.location.data,
            supplier=form.supplier.data,
            barcode=form.barcode.data,
            expiry_date=form.expiry_date.data,
            total_value=form.quantity.data * form.unit_price.data
        )
        
        # Generate QR code data
        item.qr_code_data = item.generate_qr_data()
        
        db.session.add(item)
        db.session.commit()
        
        flash('Inventory item added successfully!', 'success')
        return redirect(url_for('web.manage_inventory', biz_id=biz_id))
    
    return render_template('add_inventory_item.html', form=form, business=business, user=user)

@web_bp.route('/inventory/<int:biz_id>/qr/<int:item_id>')
@business_access_required
def generate_qr_code(biz_id, item_id):
    item = InventoryItem.query.filter_by(id=item_id, business_id=biz_id).first()
    if not item:
        return "Item not found", 404
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(item.qr_code_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png', as_attachment=True, download_name=f'qr_{item.name}.png')

@web_bp.route('/inventory/<int:biz_id>/scan', methods=['GET', 'POST'])
@business_access_required
def scan_qr_code(biz_id):
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if request.method == 'POST':
        qr_data = request.form.get('qr_data')
        if qr_data and qr_data.startswith('INV-'):
            # Parse QR data: INV-{business_id}-{item_id}-{name}-{quantity}
            parts = qr_data.split('-')
            if len(parts) >= 5:
                scanned_biz_id = int(parts[1])
                item_id = int(parts[2])
                
                if scanned_biz_id == biz_id:
                    item = InventoryItem.query.filter_by(id=item_id, business_id=biz_id).first()
                    if item:
                        return render_template('scan_result.html', 
                                             business=business, 
                                             item=item,
                                             form=InventoryTransactionForm(),
                                             user=user)
        
        flash('Invalid QR code or item not found', 'error')
        return redirect(url_for('web.scan_qr_code', biz_id=biz_id))
    
    return render_template('scan_qr.html', business=business, user=user)

@web_bp.route('/inventory/<int:biz_id>/transaction/<int:item_id>', methods=['POST'])
@business_access_required
def process_inventory_transaction(biz_id, item_id):
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    item = InventoryItem.query.filter_by(id=item_id, business_id=biz_id).first()
    if not item:
        flash('Item not found', 'error')
        return redirect(url_for('web.manage_inventory', biz_id=biz_id))
    
    form = InventoryTransactionForm()
    if form.validate_on_submit():
        previous_quantity = item.quantity
        
        if form.transaction_type.data == 'in':
            item.quantity += form.quantity.data
        elif form.transaction_type.data == 'out':
            if item.quantity >= form.quantity.data:
                item.quantity -= form.quantity.data
            else:
                flash('Insufficient stock', 'error')
                return redirect(url_for('web.scan_qr_code', biz_id=biz_id))
        elif form.transaction_type.data == 'adjustment':
            item.quantity = form.quantity.data
        
        item.total_value = item.quantity * item.unit_price
        item.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = InventoryTransaction(
            inventory_item_id=item_id,
            transaction_type=form.transaction_type.data,
            quantity=form.quantity.data,
            previous_quantity=previous_quantity,
            new_quantity=item.quantity,
            reason=form.reason.data,
            performed_by=user_id
        )
        
        # Update QR code data
        item.qr_code_data = item.generate_qr_data()
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Inventory transaction completed successfully! New quantity: {item.quantity}', 'success')
        return redirect(url_for('web.manage_inventory', biz_id=biz_id))
    
    return redirect(url_for('web.scan_qr_code', biz_id=biz_id))

@web_bp.route('/reports/create/<int:biz_id>', methods=['GET', 'POST'])
def create_report(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_roles'))
    
    form = CreateReportForm()
    if form.validate_on_submit():
        # Generate report content based on type
        content = generate_report_content(biz_id, form.report_type.data, form.date_from.data, form.date_to.data)
        
        report = Report(
            business_id=biz_id,
            created_by=user_id,
            title=form.title.data,
            report_type=form.report_type.data,
            content=content,
            date_from=form.date_from.data,
            date_to=form.date_to.data,
            sent_to_owner=form.send_to_owner.data
        )
        db.session.add(report)
        db.session.commit()
        flash('Report generated successfully', 'success')
        return redirect(url_for('web.business_reports', biz_id=biz_id))
    
    return render_template('create_report.html', form=form, business=business, user=user)

@web_bp.route('/business/<int:biz_id>/reports')
def business_reports(biz_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(biz_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.manage_roles'))
    
    reports = Report.query.filter_by(business_id=biz_id).order_by(Report.created_at.desc()).all()
    return render_template('business_reports.html', business=business, reports=reports, user=user)

def generate_report_content(biz_id, report_type, date_from, date_to):
    from sqlalchemy import func, extract
    # Placeholder for report generation - make it more detailed
    if report_type == 'sales':
        sales = Sale.query.filter(Sale.business_id == biz_id, Sale.sale_date >= date_from, Sale.sale_date <= date_to).all()
        total = sum(s.total for s in sales)
        avg_sale = total / len(sales) if sales else 0
        content = f"""
        Sales Report ({date_from} to {date_to})
        ===================================
        Total Transactions: {len(sales)}
        Total Revenue: ${total:.2f}
        Average Sale: ${avg_sale:.2f}
        
        This report covers sales activities for the specified period.
        """
        return content.strip()
    
    elif report_type == 'expenses':
        expenses = Expense.query.filter(Expense.business_id == biz_id, Expense.expense_date >= date_from, Expense.expense_date <= date_to).all()
        total = sum(e.amount for e in expenses)
        categories = {}
        for e in expenses:
            categories[e.category] = categories.get(e.category, 0) + e.amount
        
        content = f"""
        Expenses Report ({date_from} to {date_to})
        ===================================
        Total Expenses: ${total:.2f}
        Number of Expenses: {len(expenses)}
        
        Breakdown by Category:
        """
        for cat, amt in categories.items():
            content += f"- {cat}: ${amt:.2f}\n"
        content += "\nThis report helps track business expenses and identify cost-saving opportunities."
        return content.strip()
    
    elif report_type == 'employees':
        employees = Employee.query.filter_by(business_id=biz_id).all()
        active_employees = [e for e in employees if e.status == 'active']
        total_salary = sum(float(e.salary) for e in active_employees if e.salary)
        
        content = f"""
        Employees Report
        ================
        Total Employees: {len(employees)}
        Active Employees: {len(active_employees)}
        Total Monthly Salary Cost: ${total_salary:.2f}
        
        This report provides an overview of your workforce and labor costs.
        """
        return content.strip()
    
    elif report_type == 'payroll':
        payrolls = Payroll.query.filter(Payroll.business_id == biz_id, 
                                      Payroll.period_end >= date_from, 
                                      Payroll.period_start <= date_to).all()
        total_paid = sum(p.total_salaries for p in payrolls)
        
        content = f"""
        Payroll Report ({date_from} to {date_to})
        ===================================
        Total Payroll Payments: {len(payrolls)}
        Total Amount Paid: ${total_paid:.2f}
        
        This report tracks salary and wage payments for the period.
        """
        return content.strip()
    
    elif report_type == 'profit':
        sales_total = db.session.query(func.sum(Sale.total)).filter(Sale.business_id == biz_id, Sale.sale_date >= date_from, Sale.sale_date <= date_to).scalar() or 0
        expenses_total = db.session.query(func.sum(Expense.amount)).filter(Expense.business_id == biz_id, Expense.expense_date >= date_from, Expense.expense_date <= date_to).scalar() or 0
        profit = sales_total - expenses_total
        
        content = f"""
        Profit & Loss Report ({date_from} to {date_to})
        ===============================================
        Total Revenue: ${sales_total:.2f}
        Total Expenses: ${expenses_total:.2f}
        Net Profit/Loss: ${profit:.2f}
        
        This report shows the financial performance for the period.
        """
        return content.strip()
    
    return "Report content placeholder"

@web_bp.route('/api/dashboard/stats')
def dashboard_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if user.role == 'admin':
        businesses = Business.query.all()
        business_ids = [b.id for b in businesses]
    else:
        businesses = Business.query.filter_by(owner_id=user_id).all()
        business_ids = [b.id for b in businesses]
    
    # Total employees
    total_employees = Employee.query.filter(Employee.business_id.in_(business_ids)).count()
    
    # Total revenue (sum of sales)
    total_revenue = db.session.query(func.sum(Sale.total)).filter(Sale.business_id.in_(business_ids)).scalar() or 0
    
    # Sales data for chart (last 30 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    sales_data = db.session.query(
        func.date(Sale.sale_date).label('date'),
        func.sum(Sale.total).label('total')
    ).filter(
        Sale.business_id.in_(business_ids),
        Sale.sale_date >= start_date
    ).group_by(func.date(Sale.sale_date)).order_by(func.date(Sale.sale_date)).all()
    
    labels = [str(s.date) for s in sales_data]
    values = [float(s.total) for s in sales_data]
    
    return jsonify({
        'total_businesses': len(businesses),
        'total_employees': total_employees,
        'total_revenue': float(total_revenue),
        'sales_labels': labels,
        'sales_values': values
    })

@web_bp.route('/welcome/<int:business_id>')
def business_welcome(business_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(business_id)
    
    if not business or business.owner_id != user_id:
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get business type information
    business_type_info = BusinessTypeService.get_business_type_info(business_id)
    business_features = BusinessTypeService.get_business_features(business_id)
    
    return render_template('business_welcome.html', 
                         business=business, 
                         business_type_info=business_type_info,
                         business_features=business_features,
                         user=user,
                         businesses=[business],
                         business_type_service=BusinessTypeService)

@web_bp.route('/features')
def features_overview():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    return render_template('features_overview.html', user=user)

@web_bp.route('/notifications/all')
def all_notifications():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get all notifications for the user (could be filtered by business ownership)
    if user.role == 'admin':
        notifications = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    else:
        # For regular users, get notifications from businesses they own or are assigned to
        businesses = Business.query.filter_by(owner_id=user_id).all()
        business_ids = [b.id for b in businesses]
        notifications = Notification.query.filter(Notification.business_id.in_(business_ids)).order_by(Notification.created_at.desc()).limit(100).all()
    
    return render_template('all_notifications.html', notifications=notifications, user=user)

@web_bp.route('/reports/<int:report_id>/view')
def view_report(report_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    report = Report.query.get_or_404(report_id)
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(report.business_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    return render_template('view_report.html', report=report, business=business, user=user)

@web_bp.route('/reports/<int:report_id>/download')
def download_report_pdf(report_id):
    if 'user_id' not in session:
        return redirect(url_for('web.login'))
    
    report = Report.query.get_or_404(report_id)
    user_id = session['user_id']
    user = User.query.get(user_id)
    business = Business.query.get(report.business_id)
    
    if not business or (business.owner_id != user_id and user.role != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Generate PDF content
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
    )
    
    content_style = styles['Normal']
    
    story = []
    
    # Title
    story.append(Paragraph(f"Report: {report.title}", title_style))
    story.append(Spacer(1, 12))
    
    # Report details
    story.append(Paragraph(f"Business: {business.name}", content_style))
    story.append(Paragraph(f"Report Type: {report.report_type.title()}", content_style))
    story.append(Paragraph(f"Period: {report.date_from} to {report.date_to}", content_style))
    story.append(Paragraph(f"Created: {report.created_at.strftime('%Y-%m-%d %H:%M')}", content_style))
    story.append(Spacer(1, 20))
    
    # Content
    for line in report.content.split('\n'):
        if line.strip():
            story.append(Paragraph(line, content_style))
        else:
            story.append(Spacer(1, 6))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(buffer, 
                    as_attachment=True, 
                    download_name=f"{report.title.replace(' ', '_')}.pdf",
                    mimetype='application/pdf')

@web_bp.route('/set_language/<lang>')
def set_language(lang):
    """Set the user's preferred language."""
    if lang in ['en', 'uz', 'ru']:
        session['lang'] = lang
        # Also update user preferences if user is logged in
        if 'user_id' in session:
            user_id = session['user_id']
            user = User.query.get(user_id)
            if user:
                preferences = UserPreferences.query.filter_by(user_id=user_id).first()
                if not preferences:
                    preferences = UserPreferences(user_id=user_id)
                    db.session.add(preferences)
                preferences.language = lang
                db.session.commit()
    
    # Redirect back to the page they came from
    from flask import request
    return redirect(request.referrer or url_for('web.dashboard'))

# Budget Management Routes
@web_bp.route('/budgets/<int:biz_id>')
@business_access_required
def manage_budgets(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)
    
    budgets = Budget.query.filter_by(business_id=biz_id).order_by(Budget.created_at.desc()).all()
    
    # Get expense analysis
    expense_analysis = BudgetService.get_expense_analysis(biz_id)
    
    return render_template('manage_budgets.html', 
                         business=business, 
                         budgets=budgets,
                         expense_analysis=expense_analysis,
                         form=BudgetForm(),
                         user=user)

@web_bp.route('/budgets/create/<int:biz_id>', methods=['GET', 'POST'])
@business_access_required
def create_budget(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)
    
    form = BudgetForm()
    if form.validate_on_submit():
        budget = BudgetService.create_budget(
            business_id=biz_id,
            name=form.name.data,
            budget_type=form.budget_type.data,
            year=form.year.data,
            month=form.month.data if form.budget_type.data == 'monthly' else None,
            quarter=form.quarter.data if form.budget_type.data == 'quarterly' else None,
            description=form.description.data,
            user_id=user_id
        )
        
        AuditService.log_data_change(biz_id, user_id, 'budget', budget.id, 'create')
        flash('Budget created successfully', 'success')
        return redirect(url_for('web.manage_budgets', biz_id=biz_id))
    
    return render_template('create_budget.html', form=form, business=business, user=user)

@web_bp.route('/budgets/<int:budget_id>')
@business_access_required
def view_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    user_id = session['user_id']
    business = Business.query.get(budget.business_id)
    
    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    analysis = BudgetService.get_budget_analysis(budget_id)
    
    return render_template('view_budget.html', 
                         business=business, 
                         budget=budget,
                         analysis=analysis,
                         form=BudgetItemForm(),
                         user=user)

@web_bp.route('/budgets/<int:budget_id>/add-item', methods=['POST'])
@business_access_required
def add_budget_item(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    user_id = session['user_id']
    business = Business.query.get(budget.business_id)
    
    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))
    
    form = BudgetItemForm()
    if form.validate_on_submit():
        item = BudgetService.add_budget_item(
            budget_id=budget_id,
            category=form.category.data,
            subcategory=form.subcategory.data,
            budgeted_amount=form.budgeted_amount.data,
            item_type=form.item_type.data,
            description=form.description.data
        )
        
        AuditService.log_data_change(business.id, user_id, 'budget_item', item.id, 'create')
        flash('Budget item added successfully', 'success')
    
    return redirect(url_for('web.view_budget', budget_id=budget_id))

# Supplier Management Routes
@web_bp.route('/suppliers/<int:biz_id>')
@business_access_required
def manage_suppliers(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)
    
    suppliers = Supplier.query.filter_by(business_id=biz_id).order_by(Supplier.name).all()
    
    return render_template('manage_suppliers.html', 
                         business=business, 
                         suppliers=suppliers,
                         form=SupplierForm(),
                         user=user)

@web_bp.route('/suppliers/create/<int:biz_id>', methods=['GET', 'POST'])
@business_access_required
def create_supplier(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)
    
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            business_id=biz_id,
            name=form.name.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            category=form.category.data,
            payment_terms=form.payment_terms.data,
            rating=form.rating.data
        )
        db.session.add(supplier)
        db.session.commit()
        
        AuditService.log_data_change(biz_id, user_id, 'supplier', supplier.id, 'create')
        flash('Supplier added successfully', 'success')
        return redirect(url_for('web.manage_suppliers', biz_id=biz_id))
    
    return render_template('create_supplier.html', form=form, business=business, user=user)

# Sales Goals Routes
@web_bp.route('/sales-goals/<int:biz_id>')
@business_access_required
def manage_sales_goals(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)
    
    employees = Employee.query.filter_by(business_id=biz_id).all()
    sales_goals = SalesGoal.query.filter_by(business_id=biz_id).order_by(SalesGoal.created_at.desc()).all()
    
    return render_template('manage_sales_goals.html', 
                         business=business, 
                         employees=employees,
                         sales_goals=sales_goals,
                         form=SalesGoalForm(),
                         user=user)

@web_bp.route('/sales-goals/create/<int:biz_id>', methods=['POST'])
@business_access_required
def create_sales_goal(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)
    
    form = SalesGoalForm()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    form.employee_id.choices = [(e.id, e.name) for e in employees]
    
    if form.validate_on_submit():
        sales_goal = SalesGoal(
            business_id=biz_id,
            employee_id=form.employee_id.data,
            goal_type=form.goal_type.data,
            period_year=form.period_year.data,
            period_month=form.period_month.data if form.goal_type.data == 'monthly' else None,
            period_quarter=form.period_quarter.data if form.goal_type.data == 'quarterly' else None,
            target_amount=form.target_amount.data,
            target_quantity=form.target_quantity.data,
            notes=form.notes.data,
            created_by=user_id
        )
        db.session.add(sales_goal)
        db.session.commit()
        
        AuditService.log_data_change(biz_id, user_id, 'sales_goal', sales_goal.id, 'create')
        flash('Sales goal set successfully', 'success')
    
    return redirect(url_for('web.manage_sales_goals', biz_id=biz_id))

# Campaign Management Routes
@web_bp.route('/campaigns/<int:biz_id>')
@business_access_required
def campaign_management(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)

    campaigns = Campaign.query.filter_by(business_id=biz_id).order_by(Campaign.created_at.desc()).all()
    campaign_summary = CampaignService.get_campaigns_summary(biz_id)

    return render_template('manage_campaigns.html',
                         business=business,
                         campaigns=campaigns,
                         campaign_summary=campaign_summary,
                         form=CampaignForm(),
                         user=user)

@web_bp.route('/campaigns/create/<int:biz_id>', methods=['GET', 'POST'])
@business_access_required
def create_campaign(biz_id):
    user_id = session['user_id']
    business = Business.query.get(biz_id)

    form = CampaignForm()
    employees = Employee.query.filter_by(business_id=biz_id).all()
    form.manager_id.choices = [(0, 'No Manager')] + [(e.id, e.name) for e in employees]

    if form.validate_on_submit():
        campaign = CampaignService.create_campaign(
            business_id=biz_id,
            name=form.name.data,
            campaign_type=form.campaign_type.data,
            manager_id=form.manager_id.data if form.manager_id.data != 0 else None,
            budget=form.budget.data or 0.0,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data,
            user_id=user_id
        )

        AuditService.log_data_change(biz_id, user_id, 'campaign', campaign.id, 'create')
        flash('Campaign created successfully', 'success')
        return redirect(url_for('web.campaign_management', biz_id=biz_id))

    return render_template('create_campaign.html', form=form, business=business, user=user)

@web_bp.route('/campaigns/<int:campaign_id>')
@business_access_required
def view_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    # Get profit/loss analysis
    profit_loss = CampaignService.get_campaign_profit_loss(campaign_id)

    # Get analytics
    analytics = CampaignService.get_campaign_analytics(campaign_id)

    return render_template('view_campaign.html',
                         business=business,
                         campaign=campaign,
                         profit_loss=profit_loss,
                         analytics=analytics)

@web_bp.route('/campaigns/<int:campaign_id>/employees', methods=['GET', 'POST'])
@business_access_required
def manage_campaign_employees(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    form = CampaignEmployeeForm()
    # Get employees not already assigned to this campaign
    existing_employee_ids = [ce.employee_id for ce in campaign.employees]
    available_employees = Employee.query.filter(
        Employee.business_id == business.id,
        ~Employee.id.in_(existing_employee_ids)
    ).all()
    form.employee_id.choices = [(e.id, e.name) for e in available_employees]

    if form.validate_on_submit():
        assignment = CampaignService.add_employee_to_campaign(
            campaign_id=campaign_id,
            employee_id=form.employee_id.data,
            role=form.role.data,
            hourly_rate=form.hourly_rate.data or 0.0
        )

        AuditService.log_data_change(business.id, user_id, 'campaign_employee', assignment.id, 'create')
        flash('Employee added to campaign successfully', 'success')
        return redirect(url_for('web.manage_campaign_employees', campaign_id=campaign_id))

    return render_template('manage_campaign_employees.html',
                         business=business,
                         campaign=campaign,
                         form=form)

@web_bp.route('/campaigns/<int:campaign_id>/expenses', methods=['GET', 'POST'])
@business_access_required
def manage_campaign_expenses(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    form = CampaignExpenseForm()
    expenses = CampaignExpense.query.filter_by(campaign_id=campaign_id).order_by(CampaignExpense.expense_date.desc()).all()

    if form.validate_on_submit():
        expense = CampaignService.add_campaign_expense(
            campaign_id=campaign_id,
            category=form.category.data,
            description=form.description.data,
            amount=form.amount.data,
            expense_date=form.expense_date.data,
            vendor=form.vendor.data,
            user_id=user_id
        )

        AuditService.log_data_change(business.id, user_id, 'campaign_expense', expense.id, 'create')
        flash('Expense added successfully', 'success')
        return redirect(url_for('web.manage_campaign_expenses', campaign_id=campaign_id))

    return render_template('manage_campaign_expenses.html',
                         business=business,
                         campaign=campaign,
                         expenses=expenses,
                         form=form)

@web_bp.route('/campaigns/<int:campaign_id>/revenue', methods=['GET', 'POST'])
@business_access_required
def manage_campaign_revenue(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    form = CampaignRevenueForm()
    customers = Customer.query.filter_by(business_id=business.id).all()
    form.customer_id.choices = [(0, 'No Customer')] + [(c.id, c.first_name + ' ' + c.last_name) for c in customers]

    revenues = CampaignRevenue.query.filter_by(campaign_id=campaign_id).order_by(CampaignRevenue.revenue_date.desc()).all()

    if form.validate_on_submit():
        revenue = CampaignService.add_campaign_revenue(
            campaign_id=campaign_id,
            source=form.source.data,
            description=form.description.data,
            amount=form.amount.data,
            revenue_date=form.revenue_date.data,
            customer_id=form.customer_id.data if form.customer_id.data != 0 else None,
            user_id=user_id
        )

        AuditService.log_data_change(business.id, user_id, 'campaign_revenue', revenue.id, 'create')
        flash('Revenue added successfully', 'success')
        return redirect(url_for('web.manage_campaign_revenue', campaign_id=campaign_id))

    return render_template('manage_campaign_revenue.html',
                         business=business,
                         campaign=campaign,
                         revenues=revenues,
                         form=form)

@web_bp.route('/campaigns/<int:campaign_id>/tasks', methods=['GET', 'POST'])
@business_access_required
def manage_campaign_tasks(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    form = CampaignTaskForm()
    campaign_employees = [ce.employee_id for ce in campaign.employees]
    employees = Employee.query.filter(Employee.id.in_(campaign_employees)).all()
    form.assigned_to.choices = [(0, 'Unassigned')] + [(e.id, e.name) for e in employees]

    tasks = CampaignTask.query.filter_by(campaign_id=campaign_id).order_by(CampaignTask.created_at.desc()).all()

    if form.validate_on_submit():
        task = CampaignTask(
            campaign_id=campaign_id,
            title=form.title.data,
            description=form.description.data,
            assigned_to=form.assigned_to.data if form.assigned_to.data != 0 else None,
            priority=form.priority.data,
            estimated_hours=form.estimated_hours.data or 0.0,
            due_date=form.due_date.data,
            created_by=user_id
        )
        db.session.add(task)
        db.session.commit()

        AuditService.log_data_change(business.id, user_id, 'campaign_task', task.id, 'create')
        flash('Task created successfully', 'success')
        return redirect(url_for('web.manage_campaign_tasks', campaign_id=campaign_id))

    return render_template('manage_campaign_tasks.html',
                         business=business,
                         campaign=campaign,
                         tasks=tasks,
                         form=form)

@web_bp.route('/campaigns/<int:campaign_id>/time-tracking', methods=['GET', 'POST'])
@business_access_required
def campaign_time_tracking(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    form = CampaignTimeEntryForm()
    campaign_employees = [ce.employee_id for ce in campaign.employees]
    employees = Employee.query.filter(Employee.id.in_(campaign_employees)).all()
    form.employee_id.choices = [(e.id, e.name) for e in employees]

    tasks = CampaignTask.query.filter_by(campaign_id=campaign_id).all()
    form.task_id.choices = [(0, 'General')] + [(t.id, t.title) for t in tasks]

    time_entries = CampaignTimeEntry.query.filter_by(campaign_id=campaign_id).order_by(
        CampaignTimeEntry.date.desc()
    ).all()

    if form.validate_on_submit():
        time_entry = CampaignService.log_time_entry(
            campaign_id=campaign_id,
            employee_id=form.employee_id.data,
            hours=form.hours.data,
            date=form.date.data,
            description=form.description.data,
            task_id=form.task_id.data if form.task_id.data != 0 else None,
            user_id=user_id
        )

        AuditService.log_data_change(business.id, user_id, 'campaign_time_entry', time_entry.id, 'create')
        flash('Time logged successfully', 'success')
        return redirect(url_for('web.campaign_time_tracking', campaign_id=campaign_id))

    return render_template('campaign_time_tracking.html',
                         business=business,
                         campaign=campaign,
                         time_entries=time_entries,
                         form=form,
                         user=user)

@web_bp.route('/campaigns/<int:campaign_id>/reports')
@business_access_required
def campaign_reports(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    user_id = session['user_id']
    business = Business.query.get(campaign.business_id)

    if not business or (business.owner_id != user_id and session.get('role') != 'admin'):
        flash('Access denied', 'error')
        return redirect(url_for('web.dashboard'))

    reports = CampaignReport.query.filter_by(campaign_id=campaign_id).order_by(
        CampaignReport.uploaded_at.desc()
    ).all()

    return render_template('campaign_reports.html',
                         business=business,
                         campaign=campaign,
                         reports=reports)

# User Settings Routes
class UserSettingsForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Length(min=6)])
    confirm_password = PasswordField('Confirm New Password')
    telegram_chat_id = StringField('Telegram Chat ID')
    submit = SubmitField('Save Settings')

    def validate_email(self, field):
        if field.data and not field.data.endswith('@gmail.com'):
            raise ValidationError('Email must be a Gmail address.')

    def validate_confirm_password(self, field):
        if self.new_password.data and field.data != self.new_password.data:
            raise ValidationError('New passwords must match.')

class UserCustomizationForm(FlaskForm):
    theme = SelectField('Theme', choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('custom', 'Custom')
    ], default='light')
    background_image_file = FileField('Background Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')])
    background_color = StringField('Background Color', default='#ffffff', validators=[Regexp(r'^#[0-9a-fA-F]{6}$', message='Must be a valid hex color')])
    navbar_color = StringField('Navbar Color', default='#007bff', validators=[Regexp(r'^#[0-9a-fA-F]{6}$', message='Must be a valid hex color')])
    nav_link_color = StringField('Navigation Link Color', default='#ffffff', validators=[Regexp(r'^#[0-9a-fA-F]{6}$', message='Must be a valid hex color')])
    accent_color = StringField('Accent Color', default='#28a745', validators=[Regexp(r'^#[0-9a-fA-F]{6}$', message='Must be a valid hex color')])
    custom_css = TextAreaField('Custom CSS')
    submit = SubmitField('Save Customization')

@web_bp.route('/user/settings', methods=['GET', 'POST'])
def user_settings():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect(url_for('web.login'))

    form = UserSettingsForm(obj=user)

    if form.validate_on_submit():
        # Check current password
        if not bcrypt.check_password_hash(user.password_hash, form.current_password.data):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('web.user_settings'))

        # Check if username is already taken by another user
        if form.username.data != user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('Username already exists', 'error')
                return redirect(url_for('web.user_settings'))

        # Check if email is already taken by another user
        if form.email.data != user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Email already exists', 'error')
                return redirect(url_for('web.user_settings'))

        # Update user data
        user.username = form.username.data
        user.email = form.email.data
        user.telegram_chat_id = form.telegram_chat_id.data

        # Update password if provided
        if form.new_password.data:
            user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')

        db.session.commit()

        # Update session username
        session['username'] = user.username

        flash('Settings saved successfully', 'success')
        return redirect(url_for('web.user_settings'))

    return render_template('user_settings.html', form=form, user=user)

@web_bp.route('/user/customization', methods=['GET', 'POST'])
def user_customization():
    if 'user_id' not in session:
        return redirect(url_for('web.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect(url_for('web.login'))

    # Get or create user preferences
    preferences = UserPreferences.query.filter_by(user_id=user_id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user_id)
        db.session.add(preferences)
        db.session.commit()

    form = UserCustomizationForm(obj=preferences)

    if form.validate_on_submit():
        # Handle file upload
        if form.background_image_file.data:
            file = form.background_image_file.data
            filename = secure_filename(f"{user_id}_{file.filename}")
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'backgrounds')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            preferences.background_image = f'/static/uploads/backgrounds/{filename}'

        # Update other fields manually to avoid overwriting background_image
        preferences.theme = form.theme.data
        preferences.background_color = form.background_color.data
        preferences.navbar_color = form.navbar_color.data
        preferences.nav_link_color = form.nav_link_color.data
        preferences.accent_color = form.accent_color.data
        preferences.custom_css = form.custom_css.data

        db.session.commit()

        flash('Customization settings saved successfully', 'success')
        return redirect(url_for('web.user_customization'))

    return render_template('user_customization.html', form=form, user=user, preferences=preferences)

@web_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('web.login'))
