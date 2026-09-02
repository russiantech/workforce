# v3
"""
Workforce — Roles, System Roles, Temp Tasks API  (v3)
======================================================
Register:
    from web.apis.roles import roles_bp
    app.register_blueprint(roles_bp, url_prefix='/api')

Endpoints
─────────
GET    /api/roles                          list role definitions
POST   /api/roles                          create role definition
GET    /api/roles/<id>                     get single role
PUT    /api/roles/<id>                     update role
DELETE /api/roles/<id>                     deactivate role

GET    /api/roles/defaulters               users with no job-role assignment
GET    /api/roles/assignments              all active job-role assignments
POST   /api/roles/<id>/assign             assign job role to users
DELETE /api/roles/assignments/<id>        remove assignment

GET    /api/my-role                        current user's assignment + colleagues
GET    /api/roles/departments              distinct department names
GET    /api/roles/kpi-hints               KPI examples per category
GET    /api/roles/department-stats        per-dept aggregate stats

GET    /api/system-roles                   list system permission role definitions
PUT    /api/users/<uid>/system-roles      replace user's system roles (array)
PATCH  /api/users/<uid>/system-role       (legacy) assign single system role

GET    /api/temp-tasks                     list temp tasks
POST   /api/temp-tasks                     create temp task
PUT    /api/temp-tasks/<id>               update temp task
DELETE /api/temp-tasks/<id>               soft-delete temp task
"""

import traceback
from datetime import datetime

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

roles_bp = Blueprint('roles_api', __name__)

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


# ─────────────────────────────────────────────────────────────────────────────
# KPI HINTS
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/roles/kpi-hints', methods=['GET'])
@login_required
@csrf.exempt
def kpi_hints():
    """
    Returns KPI hint examples.
    ?category=dev|hr|sales  → category-specific + global hints combined.
    No category             → all categories as dict.
    """
    category = request.args.get('category', '').lower().strip()
    if category:
        hints = KPI_HINTS.get('_global', []) + KPI_HINTS.get(category, [])
        return jsonify({'hints': hints, 'category': category}), 200
    return jsonify({'all': KPI_HINTS}), 200


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM ROLES  (User.roles — many-to-many via user_roles / Role model)
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/system-roles', methods=['GET'])
@login_required
@csrf.exempt
def list_system_roles():
    """Returns the available system permission roles with metadata."""
    return jsonify({'system_roles': SYSTEM_ROLES}), 200


@roles_bp.route('/users/<int:uid>/system-roles', methods=['PUT'])
@login_required
@csrf.exempt
def set_system_roles(uid):
    """
    Replace all system permission roles for a user.
    Admin only.  Cannot change your own roles.

    Body: { "roles": ["admin", "dev"] }
          Pass an empty list to strip all roles.
    """
    if not has_role(current_user, ['admin', 'dev']):
        return jsonify({'error': 'Only admins can assign system roles'}), 403

    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        return jsonify({'error': 'You cannot change your own system roles'}), 400

    data = request.get_json(force=True) or {}
    print(data)
    raw_keys = data.get('roles', [])
    if not isinstance(raw_keys, list):
        return jsonify({'error': '"roles" must be a list'}), 400

    new_keys  = [str(k).strip().lower() for k in raw_keys]
    valid_keys = {r['key'] for r in SYSTEM_ROLES}
    invalid = [k for k in new_keys if k not in valid_keys]
    if invalid:
        return jsonify({
            'error': f'Invalid system role(s): {invalid}. Valid values: {sorted(valid_keys)}'
        }), 400

    old_keys = user.my_roles

    # Build Role objects — create any that don't yet exist in the Role table
    new_role_objs = [_get_or_create_role_obj(k) for k in new_keys]

    # Replace the relationship (SQLAlchemy handles the join-table rows)
    user.roles = new_role_objs

    if set(old_keys) != set(new_keys):
        label = ', '.join(new_keys) if new_keys else 'none'
        _notify(
            uid,
            'System Roles Updated',
            f'{_dn(current_user)} updated your system roles to: {label}.',
        )

    db.session.commit()
    return jsonify({
        'message':   'System roles updated',
        'user_id':   uid,
        'old_roles': old_keys,
        'new_roles': new_keys,
    }), 200


@roles_bp.route('/users/<int:uid>/system-role', methods=['PATCH'])
@login_required
@csrf.exempt
def assign_system_role(uid):
    """
    Legacy single-role assignment — ADDS the given role to the user's roles.
    Admin only.  Use PUT /api/users/<uid>/system-roles for full control.

    Body: { "role": "dev" }
    """
    if not has_role(current_user, ['admin']):
        return jsonify({'error': 'Only admins can assign system roles'}), 403

    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        return jsonify({'error': 'You cannot change your own system role'}), 400

    data    = request.get_json(force=True) or {}
    new_key = data.get('role', '').strip().lower()
    valid_keys = {r['key'] for r in SYSTEM_ROLES}
    if new_key not in valid_keys:
        return jsonify({'error': f'Invalid system role. Must be one of: {sorted(valid_keys)}'}), 400

    old_keys   = user.my_roles()
    role_obj   = _get_or_create_role_obj(new_key)
    role_meta  = next((r for r in SYSTEM_ROLES if r['key'] == new_key), {})

    # Add if not already present
    if role_obj not in user.roles:
        user.roles.append(role_obj)
        _notify(
            uid,
            f'System Role Added: {role_meta.get("label", new_key)}',
            f'{_dn(current_user)} granted you the "{role_meta.get("label", new_key)}" system role.',
        )

    db.session.commit()
    return jsonify({
        'message':   'System role added',
        'user_id':   uid,
        'old_roles': old_keys,
        'new_roles': user.my_roles(),
        'role_meta': role_meta,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# STAFF ROLES — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/roles', methods=['GET'])
@login_required
@csrf.exempt
def list_roles():
    active_only       = request.args.get('active_only', 'true').lower() != 'false'
    department        = request.args.get('department')
    include_assignees = request.args.get('include_assignees', 'false').lower() == 'true'
    try:
        q = StaffRole.query
        if active_only:  q = q.filter_by(is_active=True)
        if department:   q = q.filter_by(department=department)
        roles = q.order_by(StaffRole.department, StaffRole.title).all()
        return jsonify({
            'roles': [r.get_summary(include_assignees=include_assignees) for r in roles],
            'total': len(roles),
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles/<int:rid>', methods=['GET'])
@login_required
@csrf.exempt
def get_role(rid):
    try:
        role = StaffRole.query.get_or_404(rid)
        return jsonify({'role': role.get_summary(include_assignees=True)}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles', methods=['POST'])
@login_required
@csrf.exempt
def create_role():
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        data = request.get_json(force=True) or {}
        if not data.get('title', '').strip():
            return jsonify({'error': 'Role title is required'}), 400

        role = StaffRole(
            title=data['title'].strip(),
            department=(data.get('department') or '').strip() or None,
            description=(data.get('description') or '').strip() or None,
            color=data.get('color', '#2563eb'),
            icon=data.get('icon', 'ri-briefcase-line'),
            created_by=current_user.id,
        )
        for field in ('duties', 'kpis', 'requirements'):
            val = _parse_list(data, field)
            if val is not None:
                setattr(role, field, val)

        db.session.add(role)
        db.session.commit()
        return jsonify({'message': 'Role created', 'role': role.get_summary()}), 201
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles/<int:rid>', methods=['PUT'])
@login_required
@csrf.exempt
def update_role(rid):
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        role = StaffRole.query.get_or_404(rid)
        data = request.get_json(force=True) or {}

        for f in ('title', 'department', 'description', 'color', 'icon'):
            if f in data:
                setattr(role, f, data[f])
        if 'is_active' in data:
            role.is_active = bool(data['is_active'])
        for field in ('duties', 'kpis', 'requirements'):
            val = _parse_list(data, field)
            if val is not None:
                setattr(role, field, val)

        role.updated = datetime.utcnow()
        db.session.flush()

        for a in role.assignments.filter_by(is_active=True).all():
            _notify(
                a.user_id,
                f'Your role "{role.title}" was updated',
                f'{_dn(current_user)} updated the responsibilities for "{role.title}".',
            )
        db.session.commit()
        return jsonify({'message': 'Role updated', 'role': role.get_summary(include_assignees=True)}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles/<int:rid>', methods=['DELETE'])
@login_required
@csrf.exempt
def deactivate_role(rid):
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        role = StaffRole.query.get_or_404(rid)
        role.is_active = False
        role.assignments.filter_by(is_active=True).update(
            {'is_active': False}, synchronize_session=False
        )
        db.session.commit()
        return jsonify({'message': 'Role deactivated'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULTERS
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/roles/defaulters', methods=['GET'])
@login_required
@csrf.exempt
def list_defaulters():
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        assigned_ids = select(StaffRoleAssignment.user_id).where(
            StaffRoleAssignment.is_active == True
        )
        users = (
            User.query
            .filter(User.id.notin_(assigned_ids))
            .order_by(User.name, User.username)
            .all()
        )
        return jsonify({
            'defaulters': [{
                'id':          u.id,
                'name':        _dn(u),
                'username':    u.username,
                'email':       getattr(u, 'email', None),
                'photo':       getattr(u, 'photo', None),
                # plural — list of all system role types the user holds
                'role_labels': u.my_roles,
                'department':  getattr(u, 'department', None),
            } for u in users],
            'total': len(users),
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ASSIGNMENTS
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/roles/<int:rid>/assign', methods=['POST'])
@login_required
@csrf.exempt
def assign_role(rid):
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        role = StaffRole.query.filter_by(id=rid, is_active=True).first()
        if not role:
            return jsonify({'error': 'Role not found or inactive'}), 404

        data     = request.get_json(force=True) or {}
        user_ids = data.get('user_ids', [])
        notes    = data.get('notes', '')
        if not user_ids:
            return jsonify({'error': 'user_ids is required'}), 400

        results = []
        for uid in user_ids:
            user = User.query.get(uid)
            if not user:
                continue
            # Deactivate any existing active assignment for this user
            StaffRoleAssignment.query.filter_by(
                user_id=uid, is_active=True
            ).update({'is_active': False}, synchronize_session=False)

            a = StaffRoleAssignment(
                user_id=uid, role_id=rid,
                notes=notes, assigned_by=current_user.id,
            )
            db.session.add(a)
            db.session.flush()
            _notify(
                uid,
                f'Role Assigned: {role.title}',
                f'{_dn(current_user)} assigned you the role of "{role.title}"'
                + (f' ({role.department})' if role.department else '') + '.',
            )
            results.append(a.get_summary())

        db.session.commit()
        return jsonify({
            'message':     f'{len(results)} assignment(s) created',
            'assignments': results,
        }), 201
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles/assignments', methods=['GET'])
@login_required
@csrf.exempt
def list_assignments():
    try:
        if _is_admin(current_user):
            assignments = (
                StaffRoleAssignment.query
                .filter_by(is_active=True)
                .order_by(StaffRoleAssignment.assigned_at.desc())
                .all()
            )
        else:
            assignments = StaffRoleAssignment.query.filter_by(
                user_id=current_user.id, is_active=True
            ).all()
        return jsonify({'assignments': [a.get_summary() for a in assignments]}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles/assignments/<int:aid>', methods=['DELETE'])
@login_required
@csrf.exempt
def unassign_role(aid):
    try:
        a = StaffRoleAssignment.query.get_or_404(aid)
        if not _is_admin(current_user) and a.user_id != current_user.id:
            return jsonify({'error': 'Permission denied'}), 403
        a.is_active = False
        db.session.commit()
        return jsonify({'message': 'Assignment removed'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# MY ROLE
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/my-role', methods=['GET'])
@login_required
@csrf.exempt
def my_role():
    try:
        assignment = StaffRoleAssignment.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()

        dept_colleagues = []
        if assignment and assignment.role and assignment.role.department:
            dept_assignments = StaffRoleAssignment.query.filter_by(is_active=True).all()
            dept_colleagues = [
                {
                    'id':         a.user_id,
                    'name':       _dn(a.user),
                    'user_photo': a.user.photo if a.user else None,
                    'user_name':  _dn(a.user),
                    'role_title': a.role.title if a.role else None,
                    'role_color': a.role.color if a.role else '#2563eb',
                }
                for a in dept_assignments
                if (
                    a.user_id != current_user.id
                    and a.role
                    and a.role.department == assignment.role.department
                )
            ]

        return jsonify({
            'assignment': assignment.get_summary() if assignment else None,
            'role':       assignment.role.get_summary() if assignment else None,
            'colleagues': dept_colleagues,
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# STAFF - ID DETAILS
# ─────────────────────────────────────────────────────────────────────────────
@roles_bp.route('/users/me')
@login_required
def get_user():
    try:
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        if user.deleted:
            return jsonify({'success': False, 'error': 'User has been deleted'}), 410
        
        return jsonify({'success': True, 'user': user.get_summary()})
    
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# ─────────────────────────────────────────────────────────────────────────────
# DEPARTMENTS
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/roles/departments', methods=['GET'])
@login_required
@csrf.exempt
def list_departments():
    try:
        rows = (
            db.session.query(StaffRole.department)
            .filter(StaffRole.is_active == True, StaffRole.department.isnot(None))
            .distinct()
            .order_by(StaffRole.department)
            .all()
        )
        return jsonify({'departments': [r[0] for r in rows if r[0]]}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/roles/department-stats', methods=['GET'])
@login_required
@csrf.exempt
def department_stats():
    """Aggregate stats per department."""
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        departments = (
            db.session.query(StaffRole.department)
            .filter(StaffRole.is_active == True, StaffRole.department.isnot(None))
            .distinct()
            .all()
        )
        stats = []
        for (dept,) in departments:
            roles_in_dept = StaffRole.query.filter_by(department=dept, is_active=True).all()
            role_ids      = [r.id for r in roles_in_dept]
            member_count  = (
                StaffRoleAssignment.query
                .filter(
                    StaffRoleAssignment.role_id.in_(role_ids),
                    StaffRoleAssignment.is_active == True,
                )
                .count()
            ) if role_ids else 0
            stats.append({
                'department':   dept,
                'role_count':   len(roles_in_dept),
                'member_count': member_count,
            })
        return jsonify({'stats': stats}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORARY TASKS
# ─────────────────────────────────────────────────────────────────────────────

@roles_bp.route('/temp-tasks', methods=['GET'])
@login_required
@csrf.exempt
def list_temp_tasks():
    """
    Admin/manager: all tasks (filterable).
    Staff:         only their own.
    """
    try:
        page        = request.args.get('page', 1, type=int)
        per_page    = min(request.args.get('per_page', 50, type=int), 200)
        status      = request.args.get('status')
        priority    = request.args.get('priority')
        assigned_to = request.args.get('assigned_to', type=int)

        q = TemporaryTask.query.filter_by(is_deleted=False)

        if _can_manage(current_user):
            if assigned_to:
                q = q.filter_by(assigned_to=assigned_to)
        else:
            q = q.filter_by(assigned_to=current_user.id)

        if status:   q = q.filter_by(status=status)
        if priority: q = q.filter_by(priority=priority)

        pag = q.order_by(TemporaryTask.created.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return jsonify({
            'tasks': [t.get_summary() for t in pag.items],
            'total': pag.total,
            'pages': pag.pages,
            'page':  page,
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/temp-tasks', methods=['POST'])
@login_required
@csrf.exempt
def create_temp_task():
    
    if not _can_manage(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        data = request.get_json(force=True) or {}
        if not data.get('title', '').strip():
            return jsonify({'error': 'Task title is required'}), 400

        assigned_to_id = data.get('assigned_to')
        if not assigned_to_id:
            return jsonify({'error': 'assigned_to is required'}), 400

        user = User.query.get(assigned_to_id)
        if not user:
            return jsonify({'error': 'Assignee not found'}), 404

        priority = data.get('priority', 'medium')
        if priority not in TEMP_TASK_PRIORITIES:
            return jsonify({'error': f'priority must be one of {TEMP_TASK_PRIORITIES}'}), 400

        due_date = None
        if data.get('due_date'):
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

        # 
        dept = getattr(User.query.get(assigned_to_id), 'department', None)
        weight, locked = _resolve_weight(data, department=dept, is_manager=_can_manage(current_user))
        
        task = TemporaryTask(
            title=data['title'].strip(),
            detail=(data.get('detail') or '').strip() or None,
            assigned_to=assigned_to_id,
            assigned_by=current_user.id,
            priority=priority,
            weight=weight,
            weight_locked=locked,
            status='pending',
            due_date=due_date,
        )
        db.session.add(task)
        db.session.flush()
        _notify(
            assigned_to_id,
            f'New Task: {task.title}',
            f'{_dn(current_user)} assigned you a task: "{task.title}".',
        )
        db.session.commit()
        return jsonify({'message': 'Task created', 'task': task.get_summary()}), 201
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/temp-tasks/<int:tid>', methods=['PUT'])
@login_required
@csrf.exempt
def update_temp_task(tid):
    try:
        task        = TemporaryTask.query.filter_by(id=tid, is_deleted=False).first_or_404()
        is_assignee = task.assigned_to == current_user.id
        is_manager  = _can_manage(current_user)

        if not is_assignee and not is_manager:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json(force=True) or {}

        # Status — any party can update
        if 'status' in data:
            new_status = data['status']
            if new_status not in TEMP_TASK_STATUSES:
                return jsonify({'error': f'status must be one of {TEMP_TASK_STATUSES}'}), 400
            task.status = new_status
            if new_status == 'done' and not task.completed_at:
                task.completed_at = datetime.utcnow()
            if new_status == 'done' and task.assigned_by != current_user.id:
                _notify(
                    task.assigned_by,
                    f'Task Completed: {task.title}',
                    f'{_dn(current_user)} marked "{task.title}" as done.',
                )

        # Manager-only fields
        if is_manager:
            if 'title'    in data: task.title  = data['title'].strip()
            if 'detail'   in data: task.detail = data['detail']
            if 'priority' in data:
                if data['priority'] not in TEMP_TASK_PRIORITIES:
                    return jsonify({'error': 'Invalid priority'}), 400
                task.priority = data['priority']
            
            if 'weight' in data:
                task.weight = max(1, min(int(data['weight']), 10))
            if 'weight_locked' in data:
                task.weight_locked = bool(data['weight_locked'])

            if 'due_date' in data:
                task.due_date = (
                    datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                    if data['due_date'] else None
                )
            if 'assigned_to' in data:
                old_uid = task.assigned_to
                new_uid = int(data['assigned_to'])
                task.assigned_to = new_uid
                if new_uid != old_uid:
                    _notify(
                        new_uid,
                        f'Task Assigned: {task.title}',
                        f'{_dn(current_user)} assigned you: "{task.title}".',
                    )

        if not is_manager and not task.weight_locked and 'weight' in data:
            _, max_w, _ = TaskWeightDefault.get_weight(task.priority, None)
            task.weight = max(1, min(int(data['weight']), max_w))

        task.updated = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Task updated', 'task': task.get_summary()}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@roles_bp.route('/temp-tasks/<int:tid>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_temp_task(tid):
    try:
        task = TemporaryTask.query.filter_by(id=tid, is_deleted=False).first_or_404()
        if not _can_manage(current_user) and task.assigned_by != current_user.id:
            return jsonify({'error': 'Permission denied'}), 403
        task.is_deleted = True
        db.session.commit()
        return jsonify({'message': 'Task deleted'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/staff_roles.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

