from app import db
from datetime import datetime

class MarketingCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    campaign_type = db.Column(db.String(50))  # social_media, google_ads, email, etc.
    platform = db.Column(db.String(50))  # facebook, instagram, google, etc.
    target_audience = db.Column(db.String(200))
    budget = db.Column(db.Float, default=0)
    spent_amount = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # active, completed, paused
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    manager_id = db.Column(db.Integer, db.ForeignKey('employee.id'))  # Campaign manager

    # Performance metrics
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    leads_generated = db.Column(db.Integer, default=0)
    revenue_generated = db.Column(db.Float, default=0)

    # ROI calculation
    roi_percentage = db.Column(db.Float, default=0)  # (Revenue - Spent) / Spent * 100

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='marketing_campaigns')
    manager = db.relationship('Employee', backref='marketing_campaigns_managed')

class CampaignPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaign.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    spend = db.Column(db.Float, default=0)
    revenue = db.Column(db.Float, default=0)

    # Relationships
    campaign = db.relationship('MarketingCampaign', backref='daily_performance')

class ContractTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_type = db.Column(db.String(50), nullable=False)  # retail, restaurant, it, service
    template_name = db.Column(db.String(200), nullable=False)
    template_content = db.Column(db.Text, nullable=False)  # HTML template
    variables = db.Column(db.JSON)  # Available variables for replacement
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('contract_template.id'))

    # Parties involved
    party_a_name = db.Column(db.String(200), nullable=False)  # Business name
    party_a_representative = db.Column(db.String(100))
    party_b_name = db.Column(db.String(200), nullable=False)  # Client/Partner name
    party_b_representative = db.Column(db.String(100))

    # Contract details
    contract_number = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Full contract text

    # Dates
    signing_date = db.Column(db.Date)
    effective_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)

    # Financial terms
    contract_value = db.Column(db.Float, default=0)
    payment_terms = db.Column(db.Text)
    currency = db.Column(db.String(10), default='UZS')

    # Status and tracking
    status = db.Column(db.String(20), default='draft')  # draft, active, expired, terminated
    auto_renewal = db.Column(db.Boolean, default=False)
    renewal_period_months = db.Column(db.Integer, default=12)

    # Related entities
    related_project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    related_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='contracts')
    template = db.relationship('ContractTemplate', backref='contracts')
    project = db.relationship('Project', backref='contracts')
    customer = db.relationship('Customer', backref='contracts')
    creator = db.relationship('User', backref='created_contracts')

class ContractVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    changes_description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    contract = db.relationship('Contract', backref='versions')
    creator = db.relationship('User', backref='contract_versions')

class CurrencyRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(10), nullable=False)
    to_currency = db.Column(db.String(10), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    source = db.Column(db.String(50))  # API source (e.g., 'central_bank', 'open_exchange_rates')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure unique constraint for currency pair per date
    __table_args__ = (db.UniqueConstraint('from_currency', 'to_currency', 'date', name='unique_currency_rate'),)

class TaxRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100))  # Optional region/state
    tax_type = db.Column(db.String(50), nullable=False)  # vat, income_tax, corporate_tax, etc.
    rate_percentage = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
