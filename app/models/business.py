from app import db
from datetime import datetime

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(50))
    business_type_id = db.Column(db.Integer, db.ForeignKey('business_type.id'))
    country = db.Column(db.String(50))
    currency = db.Column(db.String(10), default='UZS')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settings = db.Column(db.JSON)  # For multi-tenant settings

    # Relationships
    business_type_obj = db.relationship('BusinessType', overlaps="businesses")

    # All other relationships are defined in the related models with backrefs
