"""
Projects API  –  /api/projects/...
Handles: projects CRUD, members, board columns, milestones, project labels
"""
import traceback
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from web.models import db, User
from web.models_project import (
    Project, ProjectMember, BoardColumn, Milestone, ProjectLabel,
    project_members, create_default_columns, log_activity
)
from web import csrf

projects_bp = Blueprint('projects_api', __name__, url_prefix='/api/projects')


# ─── helpers ──────────────────────────────────────────────────────────────────

def _can_view(project):
    """True if current_user may view this project."""
    if current_user.is_admin():
        return True
    if project.owner_id == current_user.id:
        return True
    return project.members.filter_by(id=current_user.id).first() is not None


def _can_manage(project):
    """True if current_user may edit/delete the project or its settings."""
    if current_user.is_admin():
        return True
    if project.owner_id == current_user.id:
        return True
    role = project.member_role(current_user.id)
    return role in ('admin',)


def _project_or_404(project_id):
    p = Project.query.filter_by(id=project_id, deleted=False).first()
    if not p:
        return None, jsonify({'success': False, 'error': 'Project not found'}), 404
    if not _can_view(p):
        return None, jsonify({'success': False, 'error': 'Access denied'}), 403
    return p, None, None


# ─── Utilities ────────────────────────────────────────────────────────────────

def _parse_date(value):
    if not value:
        return None
    try:
        from datetime import date
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _update_fields(obj, data, fields):
    for f in fields:
        if f in data:
            setattr(obj, f, data[f])


def _member_list(project):
    rows = db.session.execute(
        project_members.select().where(project_members.c.project_id == project.id)
    ).fetchall()
    result = []
    for row in rows:
        u = User.query.get(row.user_id)
        if u:
            result.append({
                'user_id':  u.id,
                'name':     u.name,
                'username': u.username,
                'email':    u.email,
                'photo':    u.photo,
                'role':     row.role,
            })
    return result