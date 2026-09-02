# web/models/attendance.py

from sqlalchemy.sql import func

from web.models import db

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False,)
    timestamp = db.Column(db.Date, nullable=False, default=func.now() )
    status = db.Column(db.String(10), nullable=False)  # 'Present ✓' or 'Absent 〤' or Excused 〥 
    comment = db.Column(db.Text)
    sign_in_time = db.Column(db.DateTime, nullable=True)
    sign_out_time = db.Column(db.DateTime, nullable=True)
    
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now())
    deleted = db.Column(db.Boolean(), default=False)  # 0-deleted, 1-not-deleted

