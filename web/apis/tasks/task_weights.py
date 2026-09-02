

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import select

from web import csrf, db
from web.apis.utils.resolve_Weights import _resolve_weight
from web.models.task_weight_config import TaskWeightDefault
from web.models.users import User, Role
from web.models.projects import TemporaryTask,TEMP_TASK_PRIORITIES, TEMP_TASK_STATUSES
from web.models.staff_roles import (
    StaffRole, StaffRoleAssignment,
    SYSTEM_ROLES, KPI_HINTS, 
)
from web.models import Notification
from web.utils.user_role import has_role

weight_bp = Blueprint('task_weight_api', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _dn(user):
    """Display name for a user."""
    if not user:
        return 'Unknown'
    return (user.name or '').strip() or user.username or str(user.id)


def _is_admin(user):
    return has_role(user, ['admin', 'md', 'hr', 'dev'])


def _can_manage(user):
    return has_role(user, ['admin', 'md', 'hr', 'dev', 'manager'])


def _notify(user_id, title, message, path='/roles/my-role'):
    if not user_id or user_id == current_user.id:
        return
    db.session.add(Notification(
        user_id=user_id, title=title, message=message,
        file_path=path, image=current_user.photo or '',
    ))


def _parse_list(data, key):
    """Accept a JSON array or newline/pipe-separated string."""
    val = data.get(key)
    if val is None:
        return None
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    import re
    return [s.strip() for s in re.split(r'[\|\n]', str(val)) if s.strip()]


def _get_or_create_role_obj(type_key):
    """
    Return the Role ORM object for the given type key, creating it if needed.
    Role.type is the unique permission key (e.g. 'admin', 'dev').
    """
    obj = Role.query.filter_by(type=type_key).first()
    if not obj:
        obj = Role(type=type_key)
        db.session.add(obj)
        db.session.flush()
    return obj


@weight_bp.route('/task-weight-defaults', methods=['GET'])
@login_required
@csrf.exempt
def list_weight_defaults():
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    rows = TaskWeightDefault.query.all()
    return jsonify({'defaults': [
        {'id': r.id, 'scope': r.scope, 'scope_key': r.scope_key,
         'priority': r.priority, 'weight': r.weight,
         'max_weight': r.max_weight, 'locked_by_default': r.locked_by_default}
        for r in rows
    ]}), 200


@weight_bp.route('/task-weight-defaults', methods=['PUT'])
@login_required
@csrf.exempt
def set_weight_default():
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    data = request.get_json(force=True) or {}
    priority = data.get('priority', 'medium')
    scope = data.get('scope', 'global')
    scope_key = data.get('scope_key') or None

    row = TaskWeightDefault.query.filter_by(
        scope=scope, scope_key=scope_key, priority=priority
    ).first()
    if not row:
        row = TaskWeightDefault(scope=scope, scope_key=scope_key, priority=priority)
        db.session.add(row)

    row.weight = max(1, min(int(data.get('weight', 3)), 10))
    row.max_weight = max(1, min(int(data.get('max_weight', 10)), 10))
    row.locked_by_default = bool(data.get('locked_by_default', False))
    row.created_by = current_user.id

    db.session.commit()
    return jsonify({'message': 'Default updated', 'default': {
        'priority': priority, 'weight': row.weight,
        'max_weight': row.max_weight, 'locked': row.locked_by_default
    }}), 200