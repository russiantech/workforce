from flask import current_app
from flask_login import UserMixin
from sqlalchemy.sql import func
from web.models import db
from web.models.associations import user_roles
import jwt
import time

# v2 (Clean & DRY)
class User(db.Model, UserMixin):
    __tablename__ = 'user'

    # ── Core Fields ─────────────────────────────────────────────
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), index=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email    = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone    = db.Column(db.String(20), unique=True, index=True)
    password = db.Column(db.String(500), nullable=False)

    photo   = db.Column(db.String(1000))
    gender  = db.Column(db.String(50))
    city    = db.Column(db.String(50))
    address = db.Column(db.String(50))
    about   = db.Column(db.String(5000))

    acct_no = db.Column(db.String(50))
    bank    = db.Column(db.String(50))
    socials = db.Column(db.JSON, default=dict)

    src      = db.Column(db.String(50))
    category = db.Column(db.String(50))

    online   = db.Column(db.Boolean(), default=False)
    status   = db.Column(db.Boolean(), default=False)
    verified = db.Column(db.Boolean(), default=False)

    ip  = db.Column(db.String(50))
    dob = db.Column(db.Date)

    # ── Professional Info ───────────────────────────────────────
    designation            = db.Column(db.String(100))
    academic_qualification = db.Column(db.String(50))
    experience_years       = db.Column(db.Integer)
    experience_level       = db.Column(db.String(50))

    refferee_type    = db.Column(db.String(50))
    refferee_email   = db.Column(db.String(100))
    refferee_phone   = db.Column(db.String(20))
    refferee_address = db.Column(db.String(200))

    reg_num           = db.Column(db.String(50))
    course            = db.Column(db.String(100))
    cert_status       = db.Column(db.String(50))
    completion_status = db.Column(db.String(50))

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now())
    deleted = db.Column(db.Boolean(), default=False)

    # ── Relationships ───────────────────────────────────────────

    notifications = db.relationship('Notification', backref='user', lazy=True)
    queries       = db.relationship('Query', backref='user', lazy=True)
    attendance    = db.relationship('Attendance', backref='user', lazy=True)

    roles = db.relationship(
        'Role',
        secondary=user_roles,
        back_populates='user',
        lazy='select'  # IMPORTANT: avoid dynamic for iteration
    )

    staff_roles = db.relationship(
        'StaffRoleAssignment',
        foreign_keys='StaffRoleAssignment.user_id',
        back_populates='user',
        lazy='dynamic'
    )

    tasks = db.relationship(
        'Task',
        foreign_keys='Task.user_id',
        back_populates='user',
        lazy=True
    )

    assigned_tasks = db.relationship(
        'Assigned_Task',
        foreign_keys='Assigned_Task.user_id',
        back_populates='user',
        lazy=True
    )

    # ── Identity ───────────────────────────────────────────────

    def get_id(self):
        return str(self.id)

    # ── Roles (SYSTEM) ─────────────────────────────────────────

    @property
    def my_roles(self):
        return [r.type for r in self.roles]

    @property
    def role(self):
        return self.my_roles[0] if self.my_roles else None

    def has_role(self, *roles):
        return any(r in self.my_roles for r in roles)

    def is_admin(self):
        return self.has_role('admin', 'dev', 'hr')

    # ── Staff Role (ORG STRUCTURE) ─────────────────────────────

    @property
    def active_staff_role(self):
        return self.staff_roles.filter_by(is_active=True).first()

    @property
    def department(self):
        role = self.active_staff_role
        return role.role.department if role and role.role else None

    @property
    def staff_role_title(self):
        role = self.active_staff_role
        return role.role.title if role and role.role else None

    # ── Auth Tokens ────────────────────────────────────────────

    def generate_token(self, exp=600, type='reset'):
        payload = {'uid': self.id, 'exp': time.time() + exp, 'type': type}
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_token(token):
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return User.query.get(data['uid']), data['type']
        except Exception:
            return None

    # ── Serialization ──────────────────────────────────────────

    def get_summary(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'photo': self.photo,
            'gender': self.gender,
            'city': self.city,
            'address': self.address,
            'about': self.about,
            'acct_no': self.acct_no,
            'bank': self.bank,
            'socials': self.socials,
            'src': self.src,
            'category': self.category,
            'online': self.online,
            'status': self.status,
            'verified': self.verified,
            'ip': self.ip,
            'dob': self.dob.isoformat() if self.dob else None,

            # Professional
            'designation': self.designation,
            'academic_qualification': self.academic_qualification,
            'experience_years': self.experience_years,
            'experience_level': self.experience_level,

            # System + Org
            'roles': self.my_roles,
            'role': self.role,
            'department': self.department,
            'staff_role': self.staff_role_title,

            'created': self.created.isoformat() if self.created else None,
            'updated': self.updated.isoformat() if self.updated else None,
        }

    def __repr__(self):
        return f"User('{self.name}', '{self.email}')"


#class Role(db.Model, RoleMixin):
class Role(db.Model):
    '''Role Table'''
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key = True)
    type = db.Column(db.String(100), unique=True)
    user = db.relationship('User', secondary=user_roles, back_populates='roles', lazy='dynamic')


class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())
    deleted = db.Column(db.Boolean(), default=False)