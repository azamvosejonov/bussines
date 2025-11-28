from app import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, owner
    telegram_chat_id = db.Column(db.String(50))  # For Telegram notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    businesses = db.relationship('Business', backref='owner', lazy=True)
    user_business_roles = db.relationship('UserBusinessRole', foreign_keys='UserBusinessRole.user_id', backref='assigned_user', lazy=True)
    preferences = db.relationship('UserPreferences', backref='user', lazy=True)
