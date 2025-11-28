from app import db
from datetime import datetime

class ProfitDistribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    net_profit = db.Column(db.Float, nullable=False)
    distribution_mode = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, nullable=False)  # {user_id: payout, ...}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
