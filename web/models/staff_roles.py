
# v2
"""
Workforce — Roles, Responsibilities Models
=============================================================
Place at:  web/models/roles.py

Changes from v1:
  - Added TemporaryTask model (admin-assigned, any-time, any-user)
  - Added SYSTEM_ROLES constant (the actual permission roles on User.roles)
  - Added KPI_HINTS (contextual examples per role/category)
  - StaffRole.duties_raw now uses newline separator for cleaner editing
"""

from datetime import datetime, date
from web.models import db


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_ROLES = [
    {'key': 'admin',        'label': 'Administrator',  'color': '#dc2626', 'icon': 'ri-shield-star-line',      'desc': 'Full system access. Can manage users, roles, projects and all settings.'},
    {'key': 'hr',           'label': 'HR Manager',     'color': '#7c3aed', 'icon': 'ri-user-settings-line',    'desc': 'Manages staff records, roles, leave and HR workflows.'},
    {'key': 'manager',      'label': 'Manager',        'color': '#0891b2', 'icon': 'ri-briefcase-4-line',      'desc': 'Leads teams, manages projects and approves task assignments.'},
    {'key': 'dev',          'label': 'Developer',      'color': '#2563eb', 'icon': 'ri-code-s-slash-line',     'desc': 'Software development access. Can view all projects and technical resources.'},
    {'key': 'tutor',        'label': 'Tutor',          'color': '#059669', 'icon': 'ri-graduation-cap-line',   'desc': 'Teaching and mentorship role. Access to learning modules and trainee management.'},
    {'key': 'intern',       'label': 'Intern',         'color': '#d97706', 'icon': 'ri-user-star-line',        'desc': 'Limited access. Can view assigned tasks and their department resources.'},
    {'key': 'secretary',    'label': 'Secretary',      'color': '#be185d', 'icon': 'ri-calendar-event-line',   'desc': 'Administrative support. Manages schedules, correspondence and office tasks.'},
    {'key': 'receptionist', 'label': 'Receptionist',   'color': '#0f766e', 'icon': 'ri-phone-line',            'desc': 'Front-desk access. Manages visitor logs, calls and basic communications.'},
    {'key': 'staff',        'label': 'Staff',          'color': '#64748b', 'icon': 'ri-user-line',             'desc': 'Standard employee access. Can view and complete assigned tasks.'},
]

KPI_HINTS = {
    '_global': [
        'Attendance rate ≥ 95% per month',
        'Complete all assigned tasks on or before deadline',
        'Maintain a peer feedback score ≥ 4/5',
        'Submit weekly progress report by Friday 5 PM',
        'Zero unexcused absences per quarter',
        'Respond to communications within 24 hours',
    ],
    'admin': [
        'System uptime maintained above 99.5%',
        'User onboarding completed within 48 hours of request',
        'Security audit passed with zero critical findings',
        'All role assignments reviewed and updated monthly',
        'Support tickets resolved within agreed SLA',
    ],
    'hr': [
        'Staff onboarding cycle completed in ≤ 5 business days',
        'Employee satisfaction survey score ≥ 80%',
        'Zero unresolved grievances older than 14 days',
        'Training completion rate ≥ 90% per quarter',
        'Headcount report submitted by 3rd of each month',
        'All leave requests processed within 48 hours',
    ],
    'manager': [
        'Project milestones delivered on schedule ≥ 85% of the time',
        'Team task completion rate ≥ 90% monthly',
        'Weekly 1:1s conducted with every direct report',
        'Sprint velocity maintained within ±10% of plan',
        'Risk register updated and reviewed bi-weekly',
        'Team NPS score ≥ 7 per quarter',
    ],
    'dev': [
        'Code review turnaround within 24 hours',
        'Bug resolution rate: P1 within 4h, P2 within 24h',
        'Unit test coverage ≥ 80% on all new code',
        'Deploy frequency: at least 2 releases per sprint',
        'Zero critical security vulnerabilities in shipped code',
        'Technical documentation updated with every feature release',
    ],
    'tutor': [
        'Trainee assessment scores improve by ≥ 15% after sessions',
        'Course material prepared and shared 48h before sessions',
        'Trainee satisfaction rating ≥ 4.5/5 per cohort',
        'Session attendance tracking submitted weekly',
        'Curriculum review completed at start of each quarter',
        'Individual learning plan created for each trainee within 1 week',
    ],
    'intern': [
        'Assigned tasks completed on time ≥ 90%',
        'Weekly learning summary submitted to supervisor',
        'Attend all scheduled training and orientation sessions',
        'Mentor check-in conducted at least twice per week',
        'End-of-internship project delivered on deadline',
    ],
    'secretary': [
        'Meeting minutes circulated within 2 hours of meeting end',
        'Calendar conflicts resolved within 1 business day',
        'Correspondence responded to within 4 working hours',
        'Filing system 100% up to date at end of each week',
        'Zero missed appointment reminders per month',
    ],
    'receptionist': [
        'Visitor log 100% complete and accurate daily',
        'All calls answered within 3 rings during working hours',
        'Visitor waiting time ≤ 5 minutes',
        'Daily front-desk report submitted by 6 PM',
        'Zero unlogged visitor incidents per month',
    ],
    'engineering': [
        'Feature delivery within sprint scope ≥ 85%',
        'Mean time to recovery (MTTR) ≤ 30 minutes for P1 incidents',
        'Code review participation rate 100%',
        'On-call response time ≤ 15 minutes',
    ],
    'sales': [
        'Monthly sales target achieved ≥ 100%',
        'Lead response time ≤ 2 hours',
        'Pipeline updated in CRM within 24 hours of client interaction',
        'Customer retention rate ≥ 85%',
        'Minimum 5 qualified leads generated per week',
    ],
    'finance': [
        'Monthly reconciliation completed by the 5th of each month',
        'Budget variance reported within 3 working days',
        'Invoices processed within 48 hours of receipt',
        'Zero financial reporting errors per quarter',
        'Expense reports approved within 3 business days',
    ],
    'operations': [
        'Process SLA adherence ≥ 95% monthly',
        'Incident report filed within 1 hour of occurrence',
        'Supplier delivery rate ≥ 98%',
        'Cost-saving initiatives: minimum 1 identified per quarter',
        'Weekly operational KPI dashboard published every Monday',
    ],
    'design': [
        'Design deliverables submitted before agreed deadline ≥ 90%',
        'Design review feedback incorporated within 24 hours',
        'Brand guideline compliance on all produced assets',
        'User testing sessions conducted for every major feature',
        'Asset library updated with every new design component',
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# STAFF ROLE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class StaffRole(db.Model):
    """
    Organisational role definition — the JD/responsibility template.
    Separate from User.roles (the system permission level, many-to-many via user_roles).
    """
    __tablename__ = 'staff_role'

    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(120), nullable=False)
    department       = db.Column(db.String(80),  nullable=True)
    description      = db.Column(db.Text,        nullable=True)
    duties_raw       = db.Column(db.Text,        nullable=True, default='')
    kpis_raw         = db.Column(db.Text,        nullable=True, default='')
    requirements_raw = db.Column(db.Text,        nullable=True, default='')
    color            = db.Column(db.String(10),  nullable=False, default='#2563eb')
    icon             = db.Column(db.String(60),  nullable=False, default='ri-briefcase-line')
    is_active        = db.Column(db.Boolean,     nullable=False, default=True)
    created_by       = db.Column(db.Integer,     db.ForeignKey('user.id'), nullable=True)
    created          = db.Column(db.DateTime,    default=datetime.utcnow)
    updated          = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = db.relationship(
        'StaffRoleAssignment', back_populates='role',
        lazy='dynamic', cascade='all, delete-orphan'
    )
    creator = db.relationship('User', foreign_keys=[created_by])

    SEP = '\n'  # newline-separated lists

    @staticmethod
    def _split(raw):
        if not raw:
            return []
        return [s.strip() for s in raw.split('\n') if s.strip()]

    @staticmethod
    def _join(items):
        return '\n'.join(str(i).strip() for i in items if str(i).strip())

    @property
    def duties(self):          return self._split(self.duties_raw)
    @duties.setter
    def duties(self, v):       self.duties_raw = self._join(v) if isinstance(v, list) else (v or '')

    @property
    def kpis(self):            return self._split(self.kpis_raw)
    @kpis.setter
    def kpis(self, v):         self.kpis_raw = self._join(v) if isinstance(v, list) else (v or '')

    @property
    def requirements(self):    return self._split(self.requirements_raw)
    @requirements.setter
    def requirements(self, v): self.requirements_raw = self._join(v) if isinstance(v, list) else (v or '')

    @property
    def assigned_count(self):
        return self.assignments.filter_by(is_active=True).count()

    def get_summary(self, include_assignees=False):
        data = {
            'id': self.id, 'title': self.title, 'department': self.department,
            'description': self.description, 'duties': self.duties,
            'kpis': self.kpis, 'requirements': self.requirements,
            'color': self.color, 'icon': self.icon, 'is_active': self.is_active,
            'assigned_count': self.assigned_count,
            'created': self.created.isoformat() if self.created else None,
            'updated': self.updated.isoformat() if self.updated else None,
        }
        if include_assignees:
            data['assignees'] = [a.get_summary() for a in self.assignments.filter_by(is_active=True).all()]
        return data


# ─────────────────────────────────────────────────────────────────────────────
# STAFF ROLE ASSIGNMENT
# ─────────────────────────────────────────────────────────────────────────────

class StaffRoleAssignment(db.Model):
    __tablename__ = 'staff_role_assignment'

    id          = db.Column(db.Integer,  primary_key=True)
    user_id     = db.Column(db.Integer,  db.ForeignKey('user.id'),       nullable=False)
    role_id     = db.Column(db.Integer,  db.ForeignKey('staff_role.id'), nullable=False)
    notes       = db.Column(db.Text,     nullable=True)
    is_active   = db.Column(db.Boolean,  nullable=False, default=True)
    assigned_by = db.Column(db.Integer,  db.ForeignKey('user.id'),       nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    # user     = db.relationship('User', foreign_keys=[user_id])
    user = db.relationship(
    'User',
    foreign_keys=[user_id],
    back_populates='staff_roles'
    )
    role     = db.relationship('StaffRole', back_populates='assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by])

    @staticmethod
    def _dn(user):
        if not user: return 'Unknown'
        return (user.name or '').strip() or user.username or str(user.id)

    def get_summary(self):
        return {
            'id':               self.id,
            'user_id':           self.user_id,
            'user_name':         self._dn(self.user),
            'user_photo':        self.user.photo if self.user else None,
            'user_username':     self.user.username if self.user else None,
            'user_system_roles': self.user.my_roles if self.user else [],
            'user_department':   getattr(self.user, 'department', None),
            'role_id':          self.role_id,
            'role_title':       self.role.title if self.role else None,
            'role_color':       self.role.color if self.role else '#2563eb',
            'role_icon':        self.role.icon  if self.role else 'ri-briefcase-line',
            'department':       self.role.department if self.role else None,
            'notes':            self.notes,
            'is_active':        self.is_active,
            'assigned_by_name': self._dn(self.assigner),
            'assigned_at':      self.assigned_at.isoformat() if self.assigned_at else None,
        }

