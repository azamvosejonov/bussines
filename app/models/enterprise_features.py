from app import db
from datetime import datetime

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    status = db.Column(db.String(20), default='new')  # new, in_progress, completed, cancelled
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    start_date = db.Column(db.Date)
    deadline = db.Column(db.Date)
    budget = db.Column(db.Float, default=0)
    actual_cost = db.Column(db.Float, default=0)
    profit = db.Column(db.Float, default=0)
    progress_percentage = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='projects')
    client = db.relationship('Customer', backref='projects')
    manager = db.relationship('Employee', backref='managed_projects')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey('employee.id'))
    status = db.Column(db.String(20), default='backlog')  # backlog, todo, doing, done, blocked
    priority = db.Column(db.String(20), default='medium')
    estimated_hours = db.Column(db.Float, default=0)
    actual_hours = db.Column(db.Float, default=0)
    start_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref='project_tasks')
    assignee = db.relationship('Employee', backref='assigned_tasks')

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(100))
    status = db.Column(db.String(20), default='potential')  # potential, active, lost, vip
    source = db.Column(db.String(50))  # website, referral, social_media, etc.
    total_purchases = db.Column(db.Float, default=0)
    total_spent = db.Column(db.Float, default=0)
    lifetime_value = db.Column(db.Float, default=0)
    last_visit = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='customers')

class CustomerInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    interaction_type = db.Column(db.String(50))  # call, email, meeting, purchase, complaint
    description = db.Column(db.Text)
    outcome = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', backref='interactions')
    creator = db.relationship('User', backref='customer_interactions')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    invoice_number = db.Column(db.String(50), unique=True)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, overdue
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='invoices')
    customer = db.relationship('Customer', backref='invoices')
    project = db.relationship('Project', backref='invoices')
    creator = db.relationship('User', foreign_keys='Invoice.created_by', backref='created_invoices')

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    # Relationships
    invoice = db.relationship('Invoice', backref='invoice_items')

class CashFlow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # income, expense
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    transaction_date = db.Column(db.Date, nullable=False)
    related_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    related_project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='cash_flows')
    customer = db.relationship('Customer', backref='cash_flows')
    project = db.relationship('Project', backref='cash_flows')
    creator = db.relationship('User', backref='cash_flow_transactions')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    document_type = db.Column(db.String(50))  # contract, invoice, passport, photo, etc.
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500))
    file_url = db.Column(db.String(500))
    related_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    related_employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    related_project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='documents')
    customer = db.relationship('Customer', backref='documents')
    employee = db.relationship('Employee', backref='documents')
    project = db.relationship('Project', backref='documents')
    uploader = db.relationship('User', backref='uploaded_documents')
