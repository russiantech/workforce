# # web/models.py
# from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.sql import func

db = SQLAlchemy()

# Import ALL models so Alembic detects them for migrations
from web.models.payments import Payment
from web.models.jobs import JobDescription, JobResponsibility
from web.models.notifications import Notification
from web.models.task_weight_config import TaskWeightDefault
from web.models.users import User, Role
from web.models.projects import (
    Task, Assigned_Task, DailyTaskAssignee, 
    DailyTaskLog, DailyTaskActivity,
    TemporaryTask
)
from web.models.attendance import Attendance
from web.models.staff_roles import StaffRole, StaffRoleAssignment