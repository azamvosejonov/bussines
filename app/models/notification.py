from app import db
from datetime import datetime

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Recipient
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # telegram, email, in_app
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='notifications')
    user = db.relationship('User', backref='notifications')

class AlertRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # salary_due, inventory_low, debt_overdue, expense_reminder, report_time
    condition = db.Column(db.JSON, nullable=False)  # Dynamic conditions for alerts
    is_active = db.Column(db.Boolean, default=True)
    telegram_enabled = db.Column(db.Boolean, default=True)
    email_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='alert_rules')

class InventoryAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    alert_threshold = db.Column(db.Integer, nullable=False)  # Minimum quantity to trigger alert
    current_quantity = db.Column(db.Integer, default=0)
    last_alert_sent = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='inventory_alerts')
    product = db.relationship('Product', backref='inventory_alerts')

class DebtReminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    debtor_name = db.Column(db.String(200), nullable=False)
    debtor_type = db.Column(db.String(20), nullable=False)  # customer, supplier
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, paid, overdue
    last_reminder_sent = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='debt_reminders')
