# # web/models/notifications.py

from sqlalchemy import func
from web.models import db

# JOBS & RESPONSIBILITIES
class JobDescription(db.Model):
    __tablename__ = 'job_descriptions'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='job_descriptions')

    title = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100))
    employment_type = db.Column(db.String(50))
    location = db.Column(db.String(100))

    description = db.Column(db.Text)
    requirements = db.Column(db.Text)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, onupdate=func.now())


class JobResponsibility(db.Model):
    __tablename__ = 'job_responsibilities'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'), nullable=False)

    job = db.relationship(
        'JobDescription',
        backref=db.backref('responsibilities', cascade='all, delete-orphan')
    )

    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)  # ordering

    created_at = db.Column(db.DateTime, default=func.now())
