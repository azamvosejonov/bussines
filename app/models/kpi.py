from app import db
from datetime import datetime

class KPI(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    sales_amount = db.Column(db.Float, default=0)
    customers_served = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    returns_count = db.Column(db.Integer, default=0)
    attendance_score = db.Column(db.Float, default=100)  # Percentage
    productivity_score = db.Column(db.Float, default=0)  # Calculated score
    notes = db.Column(db.Text)

    # Relationships
    employee = db.relationship('Employee', backref='kpis')
    business = db.relationship('Business', backref='kpis')
