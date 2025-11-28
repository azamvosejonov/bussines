from app import db
from datetime import datetime

class BusinessType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # FontAwesome icon class
    is_active = db.Column(db.Boolean, default=True)

    # Feature flags
    enable_inventory = db.Column(db.Boolean, default=False)
    enable_recipes = db.Column(db.Boolean, default=False)
    enable_customers = db.Column(db.Boolean, default=False)
    enable_projects = db.Column(db.Boolean, default=False)
    enable_campaigns = db.Column(db.Boolean, default=False)
    enable_payroll = db.Column(db.Boolean, default=False)
    enable_budgets = db.Column(db.Boolean, default=False)
    enable_suppliers = db.Column(db.Boolean, default=False)
    enable_sales_goals = db.Column(db.Boolean, default=False)
    enable_time_tracking = db.Column(db.Boolean, default=False)
    enable_invoices = db.Column(db.Boolean, default=False)
    enable_contracts = db.Column(db.Boolean, default=False)
    enable_marketing = db.Column(db.Boolean, default=False)
    enable_reports = db.Column(db.Boolean, default=False)
    enable_analytics = db.Column(db.Boolean, default=False)
    enable_notifications = db.Column(db.Boolean, default=False)

    # Relationships
    businesses = db.relationship('Business', lazy=True)

    def __init__(self, name, description, icon, **features):
        self.name = name
        self.description = description
        self.icon = icon
        for feature, enabled in features.items():
            if hasattr(self, feature):
                setattr(self, feature, enabled)

# Predefined business types with their enabled features
BUSINESS_TYPES = [
    {
        'name': 'Retail Store',
        'description': 'Brick and mortar retail business with inventory management',
        'icon': 'fas fa-store',
        'enable_inventory': True,
        'enable_customers': True,
        'enable_sales_goals': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Restaurant/Cafe',
        'description': 'Food service business with recipes and table management',
        'icon': 'fas fa-utensils',
        'enable_inventory': True,
        'enable_recipes': True,
        'enable_customers': True,
        'enable_payroll': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Service Business',
        'description': 'Service-based business like consulting, repairs, etc.',
        'icon': 'fas fa-tools',
        'enable_customers': True,
        'enable_projects': True,
        'enable_invoices': True,
        'enable_time_tracking': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Manufacturing',
        'description': 'Production and manufacturing business',
        'icon': 'fas fa-cogs',
        'enable_inventory': True,
        'enable_suppliers': True,
        'enable_projects': True,
        'enable_payroll': True,
        'enable_budgets': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'E-commerce',
        'description': 'Online retail and e-commerce business',
        'icon': 'fas fa-shopping-cart',
        'enable_inventory': True,
        'enable_customers': True,
        'enable_campaigns': True,
        'enable_marketing': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Construction',
        'description': 'Construction and contracting business',
        'icon': 'fas fa-hard-hat',
        'enable_projects': True,
        'enable_suppliers': True,
        'enable_payroll': True,
        'enable_budgets': True,
        'enable_invoices': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Marketing Agency',
        'description': 'Digital marketing and advertising agency',
        'icon': 'fas fa-bullhorn',
        'enable_customers': True,
        'enable_projects': True,
        'enable_campaigns': True,
        'enable_time_tracking': True,
        'enable_invoices': True,
        'enable_contracts': True,
        'enable_marketing': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Consulting Firm',
        'description': 'Professional consulting and advisory services',
        'icon': 'fas fa-user-tie',
        'enable_customers': True,
        'enable_projects': True,
        'enable_time_tracking': True,
        'enable_invoices': True,
        'enable_contracts': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Healthcare',
        'description': 'Medical and healthcare services',
        'icon': 'fas fa-heartbeat',
        'enable_customers': True,
        'enable_payroll': True,
        'enable_inventory': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    },
    {
        'name': 'Education',
        'description': 'Educational institutions and training centers',
        'icon': 'fas fa-graduation-cap',
        'enable_customers': True,
        'enable_payroll': True,
        'enable_projects': True,
        'enable_time_tracking': True,
        'enable_reports': True,
        'enable_analytics': True,
        'enable_notifications': True,
    }
]
