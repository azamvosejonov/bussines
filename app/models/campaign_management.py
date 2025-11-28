from app import db
from datetime import datetime

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    campaign_type = db.Column(db.String(50), nullable=False)  # marketing, project, event, sales, etc.
    status = db.Column(db.String(20), default='planning')  # planning, active, paused, completed, cancelled
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent

    # Budget and financials
    budget = db.Column(db.Float, default=0.0)
    total_expenses = db.Column(db.Float, default=0.0)
    total_revenue = db.Column(db.Float, default=0.0)
    expected_profit = db.Column(db.Float, default=0.0)

    # Timeline
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    actual_start_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)

    # People
    manager_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Metadata
    tags = db.Column(db.String(500))  # Comma-separated tags
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='campaigns')
    manager = db.relationship('Employee', foreign_keys='Campaign.manager_id', backref='managed_campaigns')
    creator = db.relationship('User', backref='created_campaigns')

    # Dynamic relationships
    employees = db.relationship('CampaignEmployee', backref='campaign', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('CampaignExpense', backref='campaign', lazy=True, cascade='all, delete-orphan')
    revenues = db.relationship('CampaignRevenue', backref='campaign', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('CampaignTask', backref='campaign', lazy=True, cascade='all, delete-orphan')
    reports = db.relationship('CampaignReport', backref='campaign', lazy=True, cascade='all, delete-orphan')
    time_entries = db.relationship('CampaignTimeEntry', backref='campaign', lazy=True, cascade='all, delete-orphan')

class CampaignEmployee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    role = db.Column(db.String(100))  # manager, coordinator, worker, etc.
    hourly_rate = db.Column(db.Float, default=0.0)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, inactive, completed

    # Relationships
    employee = db.relationship('Employee', backref='campaign_assignments')

class CampaignExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # marketing, salaries, materials, travel, etc.
    subcategory = db.Column(db.String(100))
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    vendor = db.Column(db.String(200))
    receipt_number = db.Column(db.String(100))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    approver = db.relationship('User', foreign_keys='CampaignExpense.approved_by', backref='approved_expenses')
    creator = db.relationship('User', foreign_keys='CampaignExpense.created_by', backref='created_expenses')

class CampaignRevenue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    source = db.Column(db.String(100), nullable=False)  # sales, sponsorship, donations, etc.
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    revenue_date = db.Column(db.Date, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    invoice_number = db.Column(db.String(100))
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', backref='campaign_revenues')
    recorder = db.relationship('User', backref='recorded_revenues')

class CampaignTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey('employee.id'))
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, review, completed, cancelled
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    estimated_hours = db.Column(db.Float, default=0.0)
    actual_hours = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    progress_percentage = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignee = db.relationship('Employee', backref='campaign_tasks')
    creator = db.relationship('User', backref='created_campaign_tasks')

class CampaignReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # financial, progress, marketing, final, etc.
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    file_name = db.Column(db.String(200))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, archived, deleted

    # Relationships
    uploader = db.relationship('User', backref='uploaded_campaign_reports')

class CampaignTimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('campaign_task.id'))
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    billable = db.Column(db.Boolean, default=True)
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', backref='campaign_time_entries')
    task = db.relationship('CampaignTask', backref='time_entries')
    approver = db.relationship('User', backref='approved_time_entries')
