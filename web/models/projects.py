
# v3
"""
Workforce — Project & Tasks Management Extension Models
------------------------------------------------
Place this file at:  web/models_extension.py

ALSO update these two relationships in your existing models.py
(the new Task.assigned_to_id FK creates ambiguity SQLAlchemy can't resolve
automatically — foreign_keys must be explicit on both sides):

    # Class User  →  replace the tasks relationship with:
    tasks = db.relationship(
        'Task', foreign_keys='Task.user_id',
        back_populates='user', lazy=True
    )

    # Class Task  →  replace the user relationship with:
    user = db.relationship(
        'User', foreign_keys='[Task.user_id]',
        back_populates='tasks'
    )
"""

from datetime import date, datetime

from sqlalchemy.sql import func
from web.models import db


# ─────────────────────────────────────────────────────────────────────────────
# JUNCTION TABLE
# keep_existing=True makes it safe to import this module more than once
# ─────────────────────────────────────────────────────────────────────────────

task_label_map = db.Table(
    'task_label_map',
    db.Column('task_id',  db.Integer, db.ForeignKey('task.id'),       primary_key=True),
    db.Column('label_id', db.Integer, db.ForeignKey('task_label.id'), primary_key=True),
    keep_existing=True
)


# ─────────────────────────────────────────────────────────────────────────────
# TASK  (replaces the Task class in models.py entirely)
# ─────────────────────────────────────────────────────────────────────────────

# class Task(db.Model):
#     __tablename__ = 'task'

#     id          = db.Column(db.Integer, primary_key=True)
#     description = db.Column(db.String(500), nullable=False)
#     status      = db.Column(db.String(50),  nullable=False, default='pending')
#     timestamp   = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())

#     # ── FKs ──────────────────────────────────────────────────────────────────
#     user_id        = db.Column(db.Integer, db.ForeignKey('user.id'),      nullable=False)
#     project_id     = db.Column(db.Integer, db.ForeignKey('project.id'),   nullable=True)
#     assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'),      nullable=True)
#     milestone_id   = db.Column(db.Integer, db.ForeignKey('milestone.id'), nullable=True)

#     # ── Extension columns ────────────────────────────────────────────────────
#     priority      = db.Column(db.String(20), default='medium')
#     due_date      = db.Column(db.Date,    nullable=True)
#     estimated_hrs = db.Column(db.Float,   nullable=True)
#     logged_hrs    = db.Column(db.Float,   default=0.0)
#     position      = db.Column(db.Integer, default=0)

#     created = db.Column(db.DateTime(timezone=True), default=func.now())
#     updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
#     deleted = db.Column(db.Boolean, default=False)

#     # ── Relationships ─────────────────────────────────────────────────────────
#     # Task has TWO FKs to user (user_id, assigned_to_id).
#     # foreign_keys must be explicit on every relationship that touches `user`.

#     user = db.relationship(
#         'User',
#         foreign_keys=[user_id],      # the creator / owner
#         back_populates='tasks'
#     )
#     # user = db.relationship(
#     #     'User', foreign_keys='[Task.user_id]',
#     #     back_populates='tasks'
#     # )
#     assigned_to = db.relationship(
#         'User',
#         foreign_keys=[assigned_to_id],
#         # backref=db.backref('assigned_tasks', lazy='dynamic')
#         # back_populates='assigned_tasks'
#         back_populates='tasks'
#     )
    
#     project = db.relationship(
#         'Project',
#         foreign_keys=[project_id],
#         backref=db.backref('tasks', lazy='dynamic')
#     )
#     milestone = db.relationship(
#         'Milestone',
#         foreign_keys=[milestone_id],
#         backref=db.backref('tasks', lazy='dynamic')
#     )
#     comments = db.relationship(
#         'TaskComment',
#         foreign_keys='TaskComment.task_id',
#         back_populates='task',
#         lazy='dynamic'
#     )
#     activities = db.relationship(
#         'TaskActivity',
#         foreign_keys='TaskActivity.task_id',
#         back_populates='task',
#         lazy='dynamic'
#     )
#     labels = db.relationship(
#         'TaskLabel',
#         secondary=task_label_map,
#         back_populates='tasks'
#     )

#     def get_summary(self):
#         return {
#             'id':            self.id,
#             'description':   self.description,
#             'status':        self.status,
#             'priority':      self.priority,
#             'due_date':      self.due_date.isoformat()   if self.due_date   else None,
#             'estimated_hrs': self.estimated_hrs,
#             'logged_hrs':    self.logged_hrs   or 0.0,
#             'position':      self.position     or 0,
#             'project_id':    self.project_id,
#             'milestone_id':  self.milestone_id,
#             'user_id':       self.user_id,
#             'assigned_to':   {
#                 'id':    self.assigned_to.id,
#                 'name':  self.assigned_to.name,
#                 'photo': self.assigned_to.photo,
#             } if self.assigned_to else None,
#             'labels':        [l.get_summary() for l in self.labels],
#             'comment_count': self.comments.filter_by(deleted=False).count(),
#             'timestamp':     self.timestamp.strftime('%Y-%m-%d') if self.timestamp else None,
#             'created':       self.created.isoformat()            if self.created   else None,
#         }

# v2

class Task(db.Model):
    __tablename__ = 'task'

    id          = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    status      = db.Column(db.String(50),  nullable=False, default='pending')
    timestamp   = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())

    # ── FKs ──────────────────────────────────────────────────────────────────
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'),      nullable=False)
    project_id     = db.Column(db.Integer, db.ForeignKey('project.id'),   nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'),      nullable=True)
    milestone_id   = db.Column(db.Integer, db.ForeignKey('milestone.id'), nullable=True)

    # ── Extension columns ────────────────────────────────────────────────────
    priority      = db.Column(db.String(20), default='medium')
    due_date      = db.Column(db.Date,    nullable=True)
    estimated_hrs = db.Column(db.Float,   nullable=True)
    logged_hrs    = db.Column(db.Float,   default=0.0)
    position      = db.Column(db.Integer, default=0)

    # 
    weight       = db.Column(db.Integer, default=3, nullable=False)
    weight_locked = db.Column(db.Boolean, default=False, nullable=False)
    
    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted = db.Column(db.Boolean, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    #
    # Task has TWO FKs to user (user_id, assigned_to_id).
    # Every relationship crossing user<->task needs explicit foreign_keys.
    #
    # Rule applied here:
    #   back_populates  = both sides explicitly declared (user <-> tasks)
    #   backref         = only this side declares it    (assigned_to)

    # Creator <-> User.tasks
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='tasks'
    )

    # Assignee — auto-creates User.tasks_assigned_to_me via backref.
    # No matching declaration on User is needed or allowed.
    assigned_to = db.relationship(
        'User',
        foreign_keys=[assigned_to_id],
        backref=db.backref('tasks_assigned_to_me', lazy='dynamic')
    )

    project = db.relationship(
        'Project',
        foreign_keys=[project_id],
        backref=db.backref('tasks', lazy='dynamic')
    )
    milestone = db.relationship(
        'Milestone',
        foreign_keys=[milestone_id],
        backref=db.backref('milestone_tasks', lazy='dynamic')
    )
    comments = db.relationship(
        'TaskComment',
        foreign_keys='TaskComment.task_id',
        back_populates='task',
        lazy='dynamic'
    )
    activities = db.relationship(
        'TaskActivity',
        foreign_keys='TaskActivity.task_id',
        back_populates='task',
        lazy='dynamic'
    )
    labels = db.relationship(
        'TaskLabel',
        secondary=task_label_map,
        back_populates='tasks'
    )

    def get_summary(self):
        return {
            'id':            self.id,
            'description':   self.description,
            'status':        self.status,
            'priority':      self.priority,
            'due_date':      self.due_date.isoformat()   if self.due_date else None,
            'estimated_hrs': self.estimated_hrs,
            'logged_hrs':    self.logged_hrs             or 0.0,
            'position':      self.position               or 0,
            'project_id':    self.project_id,
            'milestone_id':  self.milestone_id,
            'user_id':       self.user_id,
            'assigned_to':   {
                'id':    self.assigned_to.id,
                'name':  self.assigned_to.name if self.assigned_to.name is not None and self.assigned_to.name != "" else self.assigned_to.username,
                'photo': self.assigned_to.photo,
            } if self.assigned_to else {},
            'labels':        [l.get_summary() for l in self.labels],
            'comment_count': self.comments.filter_by(deleted=False).count(),
            'timestamp':     self.timestamp.strftime('%Y-%m-%d') if self.timestamp else None,
            'created':       self.created.isoformat()            if self.created   else None,
        }



# ─────────────────────────────────────────────────────────────────────────────
# TEMPORARY TASK
# ─────────────────────────────────────────────────────────────────────────────

TEMP_TASK_PRIORITIES = ('low', 'medium', 'high', 'urgent')
TEMP_TASK_STATUSES   = ('pending', 'in-progress', 'done', 'cancelled')

class TemporaryTask(db.Model):
    """
    Admin-assigned ad-hoc tasks: not tied to any project or milestone.
    Can be assigned to any user at any time.
    """
    __tablename__ = 'temporary_task'

    id           = db.Column(db.Integer,  primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    detail       = db.Column(db.Text,        nullable=True)
    assigned_to  = db.Column(db.Integer,  db.ForeignKey('user.id'), nullable=False)
    assigned_by  = db.Column(db.Integer,  db.ForeignKey('user.id'), nullable=False)
    priority     = db.Column(db.String(20), nullable=False, default='medium')
    status       = db.Column(db.String(30), nullable=False, default='pending')
    due_date     = db.Column(db.Date,       nullable=True)
    completed_at = db.Column(db.DateTime,   nullable=True)
    is_deleted   = db.Column(db.Boolean,    nullable=False, default=False)
    created      = db.Column(db.DateTime,   default=datetime.utcnow)
    updated      = db.Column(db.DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)
    # 
    weight       = db.Column(db.Integer, default=3, nullable=False)
    weight_locked = db.Column(db.Boolean, default=False, nullable=False)
    
    assignee = db.relationship('User', foreign_keys=[assigned_to])
    creator  = db.relationship('User', foreign_keys=[assigned_by])

    @staticmethod
    def _dn(user):
        if not user: return 'Unknown'
        return (user.name or '').strip() or user.username or str(user.id)

    def get_summary(self):
        today    = date.today()
        due      = self.due_date
        overdue  = due and due < today and self.status not in ('done', 'cancelled')
        return {
            'id':            self.id,
            'title':         self.title,
            'detail':        self.detail,
            'priority':      self.priority,
            'status':        self.status,
            'due_date':      due.isoformat() if due else None,
            'overdue':       overdue,
            'completed_at':  self.completed_at.isoformat() if self.completed_at else None,
            'assigned_to': {
                'id':           self.assignee.id,
                'name':         self._dn(self.assignee),
                'photo':        self.assignee.photo,
                'username':     self.assignee.username,
                'system_roles': self.assignee.my_roles if self.assignee else [],
            } if self.assignee else None,
            'assigned_by': {
                'id':   self.creator.id,
                'name': self._dn(self.creator),
            } if self.creator else None,
            'created': self.created.isoformat() if self.created else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ASSIGNED TASK  (admin-issued duties; separate from project tasks)
# ─────────────────────────────────────────────────────────────────────────────

class Assigned_Task(db.Model):
    """
    Daily / duty task — admin-issued and tracked, kept separate from
    project tasks (Task) so ad-hoc day-to-day duties don't clutter a
    project board, while still following the same tracking pattern
    (status / priority / due date / activity log) used across the app.

    status   : pending | in_progress | completed | missed | cancelled
               (an aggregate rolled up from every assignee's own status —
               see recompute_status() below)
    priority : low | medium | high | critical

    A task can now be given to more than one person (see DailyTaskAssignee).
    Each assignee tracks their OWN progress independently, and anyone with
    access to the task can add a DailyTaskLog entry describing exactly what
    they did — the same pattern used for project tasks (TaskComment /
    TaskActivity), just under the Daily Tasks name.

    Backward compatibility:
      - `user_id`/`user` is kept as the original "owner" field used by the
        legacy self-service quick-task modal (assigned_tasks_modal.html).
      - `assigned_to_id` is kept in sync with the FIRST assignee, purely so
        any old code/report that still reads it directly keeps working.
      - `assigned_by_id` is who created/assigned the task.
    """
    __tablename__ = 'assigned_task'

    id       = db.Column(db.Integer, primary_key=True)
    title    = db.Column(db.String(150), nullable=True)   # short label shown on cards
    detail   = db.Column(db.String(500), nullable=False)  # full description
    duration = db.Column(db.Time)

    user_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # ── Daily-task tracking extensions ───────────────────────────────────
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status         = db.Column(db.String(20), nullable=False, default='pending')
    priority       = db.Column(db.String(20), nullable=False, default='medium')
    due_date       = db.Column(db.Date, nullable=True)
    completed_at   = db.Column(db.DateTime(timezone=True), nullable=True)

    # 
    weight       = db.Column(db.Integer, default=3, nullable=False)
    weight_locked = db.Column(db.Boolean, default=False, nullable=False)
    
    # Assigned_Task only has one FK to user, but foreign_keys is still
    # set explicitly here for consistency and to be future-proof.
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='assigned_tasks'
    )

    assigned_to = db.relationship(
        'User',
        foreign_keys=[assigned_to_id],
        backref=db.backref('daily_tasks_assigned_to_me', lazy='dynamic')
    )
    assigned_by = db.relationship(
        'User',
        foreign_keys=[assigned_by_id],
        backref=db.backref('daily_tasks_created_by_me', lazy='dynamic')
    )

    assignees = db.relationship(
        'DailyTaskAssignee',
        back_populates='task',
        cascade='all, delete-orphan',
        order_by='DailyTaskAssignee.id',
    )
    logs = db.relationship(
        'DailyTaskLog',
        back_populates='task',
        cascade='all, delete-orphan',
        order_by='DailyTaskLog.created',
    )
    activities = db.relationship(
        'DailyTaskActivity',
        back_populates='task',
        cascade='all, delete-orphan',
        order_by='DailyTaskActivity.created',
    )

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted = db.Column(db.Boolean, default=False)

    # ── Helpers ───────────────────────────────────────────────────────────
    def active_assignees(self):
        return [a for a in self.assignees if not a.deleted]

    def assignee_row_for(self, user_id):
        return next((a for a in self.active_assignees() if a.user_id == user_id), None)

    def recompute_status(self):
        """Roll every assignee's individual status up into one task-level
        status, and keep the legacy assigned_to_id in sync with the first
        active assignee so old code paths still see something sensible."""
        rows = self.active_assignees()
        if rows:
            self.assigned_to_id = rows[0].user_id
            statuses = [r.status for r in rows]
            if all(s == 'completed' for s in statuses):
                self.status = 'completed'
                self.completed_at = self.completed_at or func.now()
            elif all(s == 'cancelled' for s in statuses):
                self.status = 'cancelled'
            elif any(s in ('in_progress', 'completed') for s in statuses):
                self.status = 'in_progress'
                self.completed_at = None
            else:
                self.status = 'pending'
                self.completed_at = None

    def get_summary(self, for_user_id=None):
        rows = self.active_assignees()
        completed = sum(1 for r in rows if r.status == 'completed')
        mine = self.assignee_row_for(for_user_id) if for_user_id else None
        return {
            'id':             self.id,
            'title':          self.title or (self.detail[:60] if self.detail else ''),
            'detail':         self.detail,
            'duration':       self.duration.strftime('%H:%M') if self.duration else None,
            'status':         self.status or 'pending',
            'priority':       self.priority or 'medium',
            'due_date':       self.due_date.isoformat() if self.due_date else None,
            'assignees':      [r.get_summary() for r in rows],
            'assignee_count': len(rows),
            'completed_count': completed,
            'my_status':      mine.status if mine else None,
            'assigned_by':    {
                'id':    self.assigned_by.id,
                'name':  (self.assigned_by.name or self.assigned_by.username),
            } if self.assigned_by else None,
            'log_count':      sum(1 for l in self.logs if not l.deleted),
            'created':        self.created.isoformat() if self.created else None,
            'completed_at':   self.completed_at.isoformat() if self.completed_at else None,
        }


class DailyTaskAssignee(db.Model):
    """
    One row per (task, person). Lets a Daily Task be given to several
    people while each of them tracks their own progress independently —
    one person finishing early doesn't mark it done for everyone else.
    """
    __tablename__ = 'daily_task_assignee'

    id      = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('assigned_task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    status       = db.Column(db.String(20), nullable=False, default='pending')
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deleted      = db.Column(db.Boolean, default=False)

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    task = db.relationship('Assigned_Task', foreign_keys=[task_id], back_populates='assignees')
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('daily_task_assignments', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('task_id', 'user_id', name='uq_daily_task_assignee'),
    )

    def get_summary(self):
        return {
            'id':           self.id,
            'user_id':      self.user_id,
            'name':         (self.user.name or self.user.username) if self.user else None,
            'photo':        self.user.photo if self.user else None,
            'status':       self.status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class DailyTaskLog(db.Model):
    """
    A work-log / completion note — what an assignee actually did towards
    the task. This is the Daily Tasks equivalent of TaskComment on project
    tasks: free-text, written by whoever is doing the work.
    """
    __tablename__ = 'daily_task_log'

    id      = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('assigned_task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    body    = db.Column(db.Text, nullable=False)
    deleted = db.Column(db.Boolean, default=False)

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    task   = db.relationship('Assigned_Task', foreign_keys=[task_id], back_populates='logs')
    author = db.relationship('User', foreign_keys=[user_id], backref=db.backref('daily_task_logs', lazy='dynamic'))

    def get_summary(self):
        return {
            'id':           self.id,
            'task_id':      self.task_id,
            'body':         self.body,
            'author_id':    self.user_id,
            'author_name':  (self.author.name or self.author.username) if self.author else None,
            'author_photo': self.author.photo if self.author else None,
            'created':      self.created.isoformat() if self.created else None,
        }


class DailyTaskActivity(db.Model):
    """
    Auto-recorded activity feed for a Daily Task — created / assigned /
    unassigned / status_changed / log_added / priority_changed /
    due_date_changed / deleted — the Daily Tasks equivalent of TaskActivity
    on project tasks. Gives admins a full audit trail of who did what and
    when, without relying on anyone remembering to write a note.
    """
    __tablename__ = 'daily_task_activity'

    id      = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('assigned_task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    action    = db.Column(db.String(60), nullable=False)
    detail    = db.Column(db.String(500))
    old_value = db.Column(db.String(200))
    new_value = db.Column(db.String(200))

    created = db.Column(db.DateTime(timezone=True), default=func.now())

    task  = db.relationship('Assigned_Task', foreign_keys=[task_id], back_populates='activities')
    actor = db.relationship('User', foreign_keys=[user_id], backref=db.backref('daily_task_activities', lazy='dynamic'))

    def get_summary(self):
        return {
            'id':         self.id,
            'task_id':    self.task_id,
            'actor_name': (self.actor.name or self.actor.username) if self.actor else None,
            'actor_photo': self.actor.photo if self.actor else None,
            'action':     self.action,
            'detail':     self.detail,
            'old_value':  self.old_value,
            'new_value':  self.new_value,
            'created':    self.created.isoformat() if self.created else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT
# ─────────────────────────────────────────────────────────────────────────────

class Project(db.Model):
    """
    status: planning | active | on-hold | completed | cancelled
    priority: low | medium | high | critical
    """
    __tablename__ = 'project'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    status      = db.Column(db.String(30), nullable=False, default='active')
    priority    = db.Column(db.String(20), nullable=False, default='medium')
    color       = db.Column(db.String(10), default='#5a67d8')
    icon        = db.Column(db.String(50), default='folder')
    start_date  = db.Column(db.Date)
    due_date    = db.Column(db.Date)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner    = db.relationship(
        'User',
        foreign_keys=[owner_id],
        backref=db.backref('owned_projects', lazy='dynamic')
    )

    # Counters are kept in sync by _sync_project_counts() in the API layer
    task_count      = db.Column(db.Integer, default=0)
    completed_count = db.Column(db.Integer, default=0)

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted = db.Column(db.Boolean, default=False)

    members = db.relationship(
        'ProjectMember',
        back_populates='project',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    milestones = db.relationship(
        'Milestone',
        back_populates='project',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    activities = db.relationship(
        'TaskActivity',
        foreign_keys='TaskActivity.project_id',
        back_populates='project',
        lazy='dynamic'
    )

    @property
    def progress(self):
        if not self.task_count:
            return 0
        return round((self.completed_count / self.task_count) * 100)

    def member_ids(self):
        return [m.user_id for m in self.members]

    def get_summary(self, include_members=False):
        d = {
            'id':              self.id,
            'title':           self.title,
            'description':     self.description,
            'status':          self.status,
            'priority':        self.priority,
            'color':           self.color,
            'icon':            self.icon,
            'start_date':      self.start_date.isoformat() if self.start_date else None,
            'due_date':        self.due_date.isoformat()   if self.due_date   else None,
            'owner_id':        self.owner_id,
            'owner_name':      self.owner.name if self.owner and self.owner.name and self.owner.name != "" else self.owner.username,
            'task_count':      self.task_count,
            'completed_count': self.completed_count,
            'progress':        self.progress,
            'created':         self.created.isoformat()    if self.created    else None,
        }
        if include_members:
            d['members'] = [m.get_summary() for m in self.members]
        return d

    def __repr__(self):
        return f'<Project {self.title!r}>'


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT MEMBER
# ─────────────────────────────────────────────────────────────────────────────

class ProjectMember(db.Model):
    """role: owner | manager | contributor | viewer"""
    __tablename__ = 'project_member'
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )

    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id',    ondelete='CASCADE'), nullable=False)
    role       = db.Column(db.String(30), nullable=False, default='contributor')
    joined_at  = db.Column(db.DateTime, default=func.now())

    project = db.relationship('Project', back_populates='members')
    user    = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('project_memberships', lazy='dynamic')
    )

    def get_summary(self):
        return {
            'id':         self.id,
            'project_id': self.project_id,
            'user_id':    self.user_id,
            'user_name':  self.user.name if self.user and self.user.name is not None and self.user.name != "" else self.user.username,
            'user_photo': self.user.photo   if self.user else None,
            'role':       self.role,
            'joined_at':  self.joined_at.isoformat() if self.joined_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MILESTONE
# ─────────────────────────────────────────────────────────────────────────────

class Milestone(db.Model):
    """status: upcoming | in-progress | completed | missed"""
    __tablename__ = 'milestone'

    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date    = db.Column(db.Date)
    status      = db.Column(db.String(30), default='upcoming')

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted = db.Column(db.Boolean, default=False)

    project = db.relationship('Project', back_populates='milestones')

    def get_summary(self):
        return {
            'id':          self.id,
            'project_id':  self.project_id,
            'title':       self.title,
            'description': self.description,
            'due_date':    self.due_date.isoformat() if self.due_date else None,
            'status':      self.status,
        }


# ─────────────────────────────────────────────────────────────────────────────
# TASK COMMENT
# ─────────────────────────────────────────────────────────────────────────────

class TaskComment(db.Model):
    """Threaded comment. parent_id=None means top-level; set it for replies."""
    __tablename__ = 'task_comment'

    id        = db.Column(db.Integer, primary_key=True)
    task_id   = db.Column(db.Integer, db.ForeignKey('task.id',         ondelete='CASCADE'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'),         nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('task_comment.id'), nullable=True)
    body      = db.Column(db.Text, nullable=False)
    edited    = db.Column(db.Boolean, default=False)

    created = db.Column(db.DateTime(timezone=True), default=func.now())
    updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted = db.Column(db.Boolean, default=False)

    task = db.relationship(
        'Task',
        foreign_keys=[task_id],
        back_populates='comments'
    )
    author = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('task_comments', lazy='dynamic')
    )
    replies = db.relationship(
        'TaskComment',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )

    def get_summary(self, include_replies=False):
        d = {
            'id':           self.id,
            'task_id':      self.task_id,
            'user_id':      self.user_id,
            'author_name':  self.author.name or self.author.username  if self.author else None,
            'author_photo': self.author.photo if self.author else None,
            'parent_id':    self.parent_id,
            'body':         self.body,
            'edited':       self.edited,
            'created':      self.created.isoformat() if self.created else None,
        }
        if include_replies:
            d['replies'] = [r.get_summary() for r in self.replies.filter_by(deleted=False)]
        return d


# ─────────────────────────────────────────────────────────────────────────────
# TASK ACTIVITY  (immutable audit log — never edited or deleted)
# ─────────────────────────────────────────────────────────────────────────────

class TaskActivity(db.Model):
    """
    One entry per meaningful event on a task or project.
    action: task_created | status_changed | assigned | comment_added |
            priority_changed | due_date_changed | hours_logged |
            milestone_created | member_added | project_created …
    """
    __tablename__ = 'task_activity'

    id         = db.Column(db.Integer, primary_key=True)
    task_id    = db.Column(db.Integer, db.ForeignKey('task.id',    ondelete='CASCADE'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'),   nullable=False)

    action    = db.Column(db.String(60),  nullable=False)
    detail    = db.Column(db.String(500))
    old_value = db.Column(db.String(200))
    new_value = db.Column(db.String(200))

    created = db.Column(db.DateTime(timezone=True), default=func.now())

    task = db.relationship(
        'Task',
        foreign_keys=[task_id],
        back_populates='activities'
    )
    project = db.relationship(
        'Project',
        foreign_keys=[project_id],
        back_populates='activities'
    )
    actor = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('task_activities', lazy='dynamic')
    )

    def get_summary(self):
        return {
            'id':          self.id,
            'task_id':     self.task_id,
            'project_id':  self.project_id,
            'actor_name':  (self.actor.name or self.actor.username)  if self.actor else None,
            'actor_photo': self.actor.photo if self.actor else None,
            'action':      self.action,
            'detail':      self.detail,
            'old_value':   self.old_value,
            'new_value':   self.new_value,
            'created':     self.created.isoformat() if self.created else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# TASK LABEL
# ─────────────────────────────────────────────────────────────────────────────

class TaskLabel(db.Model):
    """
    Coloured tag applied to tasks.
    project_id=None → global label visible to all projects.
    """
    __tablename__ = 'task_label'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(60), nullable=False)
    color      = db.Column(db.String(10), default='#6c757d')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=True)

    tasks = db.relationship(
        'Task',
        secondary=task_label_map,
        back_populates='labels'
    )

    def get_summary(self):
        return {'id': self.id, 'name': self.name, 'color': self.color}


