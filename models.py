from app import db
from datetime import datetime

class PostedToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    contract_address = db.Column(db.String(255), unique=True, nullable=False)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    telegram_message_id = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<PostedToken {self.name}: {self.contract_address}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contract_address': self.contract_address,
            'posted_at': self.posted_at.isoformat(),
            'telegram_message_id': self.telegram_message_id
        }

class MonitorStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_tokens_found = db.Column(db.Integer, default=0)
    total_tokens_posted = db.Column(db.Integer, default=0)
    last_check = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    is_running = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'total_tokens_found': self.total_tokens_found,
            'total_tokens_posted': self.total_tokens_posted,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'last_error': self.last_error,
            'is_running': self.is_running
        }
