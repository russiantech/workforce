from web.models import db

user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
    keep_existing=True
)


# ─────────────────────────────────────────────────────────────────────────────
# MANY-TO-MANY JUNCTION TABLES
# ─────────────────────────────────────────────────────────────────────────────

task_label_map = db.Table(
    'task_label_map',
    db.Column('task_id',  db.Integer, db.ForeignKey('task.id'),        primary_key=True),
    db.Column('label_id', db.Integer, db.ForeignKey('task_label.id'),  primary_key=True),
    keep_existing=True
)

