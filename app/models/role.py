from app import db
from datetime import datetime

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # e.g., Manager, Cashier, Waiter
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, nullable=False)  # List of permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='roles')
