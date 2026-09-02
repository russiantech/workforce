# # web/models/notifications.py

from sqlalchemy import func
from web.models import db

class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, unique=True, primary_key=True, nullable=False)
    usr_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Orderinfo->User->foreign-key
    
    txn_ref = db.Column(db.String(100)) #['dollar, naira etc]
    txn_amt = db.Column(db.Integer())
    txn_desc = db.Column(db.String(100)) 
    txn_status = db.Column(db.String(100), default='pending') #['pending','successful', 'cancelled', 'reversed']
    currency_code = db.Column(db.String(100)) #['dollar, naira, cedis etc]
    provider = db.Column(db.String(100)) #['paypal','stripe', 'visa', 'mastercard', paystack']

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now())
    deleted = db.Column(db.Boolean(), default=False)  # 0-deleted, 1-not-deleted

