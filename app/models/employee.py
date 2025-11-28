from app import db
from datetime import datetime

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(100))
    base_salary = db.Column(db.Float, nullable=False)  # Monthly
    salary_type = db.Column(db.String(20), default='monthly')  # monthly or hourly
    is_active = db.Column(db.Boolean, default=True)
    hire_date = db.Column(db.Date, default=datetime.utcnow)
    custom_share_pct = db.Column(db.Float, nullable=True)  # For custom allocations
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
