from app import db
from datetime import datetime

class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    total_salaries = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
