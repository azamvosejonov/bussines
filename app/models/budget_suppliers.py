from app import db
from datetime import datetime

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    budget_type = db.Column(db.String(20), nullable=False)  # 'yearly', 'monthly', 'quarterly'
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer)  # For monthly budgets
    quarter = db.Column(db.Integer)  # For quarterly budgets
    total_budgeted_income = db.Column(db.Float, default=0.0)
    total_budgeted_expenses = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='draft')  # 'draft', 'active', 'completed'
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('BudgetItem', backref='budget', lazy=True, cascade='all, delete-orphan')
    business = db.relationship('Business', backref='budgets')
    creator = db.relationship('User', backref='created_budgets')

class BudgetItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100))
    budgeted_amount = db.Column(db.Float, nullable=False, default=0.0)
    actual_amount = db.Column(db.Float, default=0.0)
    item_type = db.Column(db.String(20), nullable=False)  # 'income', 'expense'
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    category = db.Column(db.String(100))  # Product category they supply
    payment_terms = db.Column(db.String(200))  # e.g., "Net 30", "Cash on delivery"
    rating = db.Column(db.Float, default=0.0)  # Supplier rating 1-5
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)
    business = db.relationship('Business', backref='suppliers')

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.DateTime)
    actual_delivery_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade='all, delete-orphan')
    business = db.relationship('Business', backref='purchase_orders')
    creator = db.relationship('User', backref='purchase_orders')

class PurchaseOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    received_quantity = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='ordered')  # 'ordered', 'received', 'cancelled'

class SalesGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    goal_type = db.Column(db.String(20), nullable=False)  # 'monthly', 'quarterly', 'yearly'
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer)  # For monthly goals
    period_quarter = db.Column(db.Integer)  # For quarterly goals
    target_amount = db.Column(db.Float, nullable=False)
    target_quantity = db.Column(db.Integer, default=0)
    achieved_amount = db.Column(db.Float, default=0.0)
    achieved_quantity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # 'active', 'completed', 'cancelled'
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='sales_goals')
    employee = db.relationship('Employee', backref='sales_goals')
    creator = db.relationship('User', backref='created_sales_goals')

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50), nullable=False)  # 'meeting', 'training', 'event', 'reminder', 'vacation', 'sick_leave'
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(200))
    attendees = db.Column(db.Text)  # JSON string of attendee IDs
    reminder_minutes = db.Column(db.Integer, default=15)  # Minutes before event to remind
    status = db.Column(db.String(20), default='scheduled')  # 'scheduled', 'confirmed', 'cancelled', 'completed'
    recurrence = db.Column(db.String(50))  # 'daily', 'weekly', 'monthly', 'yearly'
    recurrence_end = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='calendar_events')
    creator = db.relationship('User', backref='created_events')
