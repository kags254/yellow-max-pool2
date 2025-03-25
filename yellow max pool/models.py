from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    api_token = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trades = db.relationship('Trade', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    market = db.Column(db.String(20), nullable=False)
    contract_type = db.Column(db.String(20), nullable=False)
    stake_amount = db.Column(db.Float, nullable=False)
    outcome = db.Column(db.String(10), nullable=True)  # 'win', 'loss', or None if pending
    profit_loss = db.Column(db.Float, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Trade {self.id}: {self.contract_type} on {self.market}>'

class TradingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_balance = db.Column(db.Float, nullable=False)
    current_balance = db.Column(db.Float, nullable=False)
    profit_loss = db.Column(db.Float, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<TradingSession {self.id}: P/L {self.profit_loss}>'

class DigitHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    market = db.Column(db.String(20), nullable=False)
    digit = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DigitHistory {self.market}: {self.digit}>'
