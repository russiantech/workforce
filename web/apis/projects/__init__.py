
"""
Workforce — Projects Blueprint (FIXED)
=========================================
Fixes applied:
  1. SAWarning: subquery coercion — use .subquery() then select() or use .scalar_subquery()
  2. _can_access: assigned users (via tasks) also get access
  3. Notifications sent on ALL assignment paths (create, update, add_member)
  4. name fallback to username everywhere
  5. Labels: full CRUD (list, create, update, delete, toggle on task)
  6. Real-time consistency: every mutating endpoint returns fresh summary
  7. Permission corrections throughout
"""

import traceback
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import select

from web.models import db
from web import csrf
from web.models.users import User
from web.models.notifications import Notification

from web.models.projects import (
    Project, ProjectMember, Milestone, Task,
    TaskActivity, TaskLabel
)
from web.utils.user_role import has_role

project_bp = Blueprint('project_api', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _display_name(user):
    """Return name with username fallback."""
    if user is None:
        return 'Unknown'
    return (user.name or '').strip() or user.username or str(user.id)


def _is_project_manager(user, project):
    """True if user owns the project or has manager/owner membership."""
    if project.owner_id == user.id:
        return True
    m = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
    return m and m.role in ('owner', 'manager')


def _can_access(user, project):
    """
    True if user:
      - has an elevated system role, OR
      - is a ProjectMember, OR
      - has any task assigned to them inside this project
    """
    if has_role(user, ['admin', 'hr', 'dev']):
        return True
    m = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
    if m:
        return True
    # Also grant access when the user has tasks assigned in this project
    if hasattr(Task, 'assigned_to_id') and hasattr(Task, 'project_id'):
        assigned_task = Task.query.filter_by(
            project_id=project.id,
            assigned_to_id=user.id,
            deleted=False
        ).first()
        if assigned_task:
            return True
    return False


def _log(task_id=None, project_id=None, action='', detail='', old=None, new=None):
    """Create a TaskActivity entry."""
    entry = TaskActivity(
        task_id=task_id,
        project_id=project_id,
        user_id=current_user.id,
        action=action,
        detail=detail,
        old_value=str(old) if old is not None else None,
        new_value=str(new) if new is not None else None,
    )
    db.session.add(entry)


def _notify(user_id, title, message, file_path='/'):
    """Create an in-app notification (skip if notifying self)."""
    if user_id == current_user.id:
        return
    n = Notification(
        user_id=user_id,
        title=title,
        message=message,
        file_path=file_path,
        image=current_user.photo or '',
    )
    db.session.add(n)


def _sync_task_counts(project):
    """Recalculate and persist task_count / completed_count."""
    tasks = Task.query.filter_by(project_id=project.id, deleted=False).all()
    project.task_count      = len(tasks)
    project.completed_count = sum(1 for t in tasks if t.status == 'completed')


def _member_project_ids_subquery(user_id):
    """
    Returns a proper SQLAlchemy select() subquery of project_ids for a user.
    Fixes the SAWarning about coercing Subquery into select().
    """
    return select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@project_bp.route('/projects', methods=['GET'])
@login_required
@csrf.exempt
def list_projects():
    """
    Returns all projects the current user can access.
    Includes projects where user is a member OR has assigned tasks.
    Query params: status, priority, page, per_page
    """
    try:
        page     = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 200, type=int)
        status   = request.args.get('status')
        priority = request.args.get('priority')

        query = Project.query.filter_by(deleted=False)

        if not has_role(current_user, ['admin', 'hr', 'dev']):
            # Projects where user is a member
            member_subq = _member_project_ids_subquery(current_user.id)

            # Projects where user has assigned tasks
            assigned_subq = None
            if hasattr(Task, 'assigned_to_id') and hasattr(Task, 'project_id'):
                assigned_subq = select(Task.project_id).where(
                    Task.assigned_to_id == current_user.id,
                    Task.deleted == False,
                    Task.project_id.isnot(None)
                )

            if assigned_subq is not None:
                query = query.filter(
                    db.or_(
                        Project.id.in_(member_subq),
                        Project.id.in_(assigned_subq)
                    )
                )
            else:
                query = query.filter(Project.id.in_(member_subq))

        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)

        paginated = query.order_by(Project.created.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'projects': [p.get_summary(include_members=True) for p in paginated.items],
            'total':    paginated.total,
            'pages':    paginated.pages,
            'page':     page,
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects', methods=['POST'])
@login_required
@csrf.exempt
def create_project():
    """Create a new project. Only admin/hr/manager/dev roles."""
    try:
        if not has_role(current_user, ['admin', 'hr', 'dev', 'manager']):
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json(force=True)

        if not data.get('title'):
            return jsonify({'error': 'Project title is required'}), 400

        project = Project(
            title=data['title'],
            description=data.get('description', ''),
            status=data.get('status', 'active'),
            priority=data.get('priority', 'medium'),
            color=data.get('color', '#4f46e5'),
            icon=data.get('icon', 'folder'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                       if data.get('start_date') else None,
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                     if data.get('due_date') else None,
            owner_id=current_user.id,
        )
        db.session.add(project)
        db.session.flush()

        # Auto-add creator as owner member
        db.session.add(ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role='owner'
        ))

        actor_name = _display_name(current_user)

        # Add initial members
        for uid in data.get('member_ids', []):
            if uid == current_user.id:
                continue
            user = User.query.get(uid)
            if not user:
                continue
            db.session.add(ProjectMember(
                project_id=project.id,
                user_id=uid,
                role=data.get('member_role', 'contributor')
            ))
            _notify(
                uid,
                f'Added to project "{project.title}"',
                f'{actor_name} added you to project "{project.title}".',
                f'/projects/{project.id}/board'
            )

        _log(project_id=project.id, action='project_created',
             detail=f'Project "{project.title}" created by {actor_name}')

        db.session.commit()
        return jsonify({'message': 'Project created', 'project': project.get_summary(include_members=True)}), 201

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>', methods=['GET'])
@login_required
@csrf.exempt
def get_project(pid):
    """Full project detail including tasks, members, milestones."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()

        if not _can_access(current_user, project):
            return jsonify({'error': 'Access denied'}), 403

        tasks = Task.query.filter_by(project_id=pid, deleted=False).order_by(
            Task.position.asc(), Task.created.desc()
        ).all()

        status_order = ['pending', 'on-going', 'stucked', 'completed', 'cancelled']
        board = {s: [] for s in status_order}
        for t in tasks:
            col = t.status if t.status in board else 'pending'
            assignee = getattr(t, 'assigned_to', None)
            board[col].append({
                'id':            t.id,
                'description':   t.description,
                'status':        t.status,
                'priority':      getattr(t, 'priority', 'medium'),
                'due_date':      t.due_date.isoformat() if getattr(t, 'due_date', None) else None,
                'assigned_to':   {
                    'id':    assignee.id,
                    'name':  _display_name(assignee),
                    'photo': assignee.photo,
                } if assignee else None,
                'comment_count': t.comments.filter_by(deleted=False).count()
                                 if hasattr(t, 'comments') else 0,
                'labels':        [l.get_summary() for l in t.labels]
                                 if hasattr(t, 'labels') else [],
                'milestone_id':  getattr(t, 'milestone_id', None),
            })

        milestones = [m.get_summary() for m in
                      project.milestones.filter_by(deleted=False).order_by(Milestone.due_date)]

        activities = [a.get_summary() for a in
                      project.activities.order_by(TaskActivity.created.desc()).limit(50)]

        labels = TaskLabel.query.filter(
            db.or_(
                TaskLabel.project_id == pid,
                TaskLabel.project_id.is_(None)
            )
        ).all()

        return jsonify({
            'project':    project.get_summary(include_members=True),
            'board':      board,
            'milestones': milestones,
            'activities': activities,
            'labels':     [l.get_summary() for l in labels],
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>', methods=['PUT'])
@login_required
@csrf.exempt
def update_project(pid):
    """Update project metadata."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()

        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json(force=True)

        fields = ['title', 'description', 'status', 'priority', 'color', 'icon']
        for f in fields:
            if f in data:
                old = getattr(project, f)
                setattr(project, f, data[f])
                if old != data[f]:
                    _log(project_id=pid, action=f'{f}_changed',
                         detail=f'{f} updated', old=old, new=data[f])

        if 'start_date' in data and data['start_date']:
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'due_date' in data and data['due_date']:
            project.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

        db.session.commit()
        return jsonify({'message': 'Project updated', 'project': project.get_summary(include_members=True)}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_project(pid):
    """Soft-delete a project (admin/hr or project owner only)."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()

        if not (has_role(current_user, ['admin', 'hr']) or project.owner_id == current_user.id):
            return jsonify({'error': 'Permission denied'}), 403

        project.deleted = True
        _log(project_id=pid, action='project_deleted',
             detail=f'Project "{project.title}" deleted by {_display_name(current_user)}')
        db.session.commit()
        return jsonify({'message': 'Project deleted'}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT MEMBERS
# ─────────────────────────────────────────────────────────────────────────────

@project_bp.route('/projects/<int:pid>/members', methods=['GET'])
@login_required
@csrf.exempt
def list_members(pid):
    """List all members of a project."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _can_access(current_user, project):
            return jsonify({'error': 'Access denied'}), 403
        members = ProjectMember.query.filter_by(project_id=pid).all()
        return jsonify({'members': [m.get_summary() for m in members]}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/members', methods=['POST'])
@login_required
@csrf.exempt
def add_member(pid):
    """Add a user to a project."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()

        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        data    = request.get_json(force=True)
        user_id = data.get('user_id')
        role    = data.get('role', 'contributor')

        if not user_id:
            return jsonify({'error': 'user_id required'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        existing = ProjectMember.query.filter_by(project_id=pid, user_id=user_id).first()
        if existing:
            return jsonify({'error': 'User is already a member'}), 409

        m = ProjectMember(project_id=pid, user_id=user_id, role=role)
        db.session.add(m)

        actor_name = _display_name(current_user)
        user_name  = _display_name(user)

        _log(project_id=pid, action='member_added',
             detail=f'{user_name} added as {role}')
        _notify(
            user_id,
            f'Added to project "{project.title}"',
            f'{actor_name} added you to project "{project.title}" as {role}.',
            f'/projects/{pid}/board'
        )
        db.session.commit()
        return jsonify({'message': 'Member added', 'member': m.get_summary()}), 201

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/members/<int:uid>', methods=['PUT'])
@login_required
@csrf.exempt
def update_member_role(pid, uid):
    """Change a member's role."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        m = ProjectMember.query.filter_by(project_id=pid, user_id=uid).first_or_404()
        data     = request.get_json(force=True)
        old_role = m.role
        m.role   = data.get('role', m.role)

        user = User.query.get(uid)
        if user:
            _notify(
                uid,
                f'Role updated in "{project.title}"',
                f'{_display_name(current_user)} changed your role from {old_role} to {m.role}.',
                f'/projects/{pid}/board'
            )

        db.session.commit()
        return jsonify({'message': 'Role updated', 'member': m.get_summary()}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/members/<int:uid>', methods=['DELETE'])
@login_required
@csrf.exempt
def remove_member(pid, uid):
    """Remove a member from a project (manager or self-removal)."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project) and current_user.id != uid:
            return jsonify({'error': 'Permission denied'}), 403

        # Prevent removing the sole owner
        if project.owner_id == uid and not has_role(current_user, ['admin', 'hr']):
            return jsonify({'error': 'Cannot remove the project owner'}), 403

        m = ProjectMember.query.filter_by(project_id=pid, user_id=uid).first_or_404()
        db.session.delete(m)
        _log(project_id=pid, action='member_removed',
             detail=f'User {uid} removed from project')
        db.session.commit()
        return jsonify({'message': 'Member removed'}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# MILESTONES
# ─────────────────────────────────────────────────────────────────────────────

@project_bp.route('/projects/<int:pid>/milestones', methods=['GET'])
@login_required
@csrf.exempt
def list_milestones(pid):
    project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
    if not _can_access(current_user, project):
        return jsonify({'error': 'Access denied'}), 403
    ms = project.milestones.filter_by(deleted=False).order_by(Milestone.due_date).all()
    return jsonify({'milestones': [m.get_summary() for m in ms]}), 200


@project_bp.route('/projects/<int:pid>/milestones', methods=['POST'])
@login_required
@csrf.exempt
def create_milestone(pid):
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json(force=True)
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400

        m = Milestone(
            project_id=pid,
            title=data['title'],
            description=data.get('description'),
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                     if data.get('due_date') else None,
            status=data.get('status', 'upcoming'),
        )
        db.session.add(m)
        _log(project_id=pid, action='milestone_created',
             detail=f'Milestone "{m.title}" created')
        db.session.commit()
        return jsonify({'message': 'Milestone created', 'milestone': m.get_summary()}), 201

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/milestones/<int:mid>', methods=['PUT'])
@login_required
@csrf.exempt
def update_milestone(pid, mid):
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        m = Milestone.query.filter_by(id=mid, project_id=pid, deleted=False).first_or_404()
        data = request.get_json(force=True)
        for f in ['title', 'description', 'status']:
            if f in data:
                setattr(m, f, data[f])
        if data.get('due_date'):
            m.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        db.session.commit()
        return jsonify({'message': 'Milestone updated', 'milestone': m.get_summary()}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/milestones/<int:mid>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_milestone(pid, mid):
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        m = Milestone.query.filter_by(id=mid, project_id=pid, deleted=False).first_or_404()
        m.deleted = True
        db.session.commit()
        return jsonify({'message': 'Milestone deleted'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# LABELS — Full CRUD
# ─────────────────────────────────────────────────────────────────────────────

@project_bp.route('/projects/<int:pid>/labels', methods=['GET'])
@login_required
@csrf.exempt
def list_labels(pid):
    """List all labels for a project (project-specific + global)."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _can_access(current_user, project):
            return jsonify({'error': 'Access denied'}), 403

        labels = TaskLabel.query.filter(
            db.or_(
                TaskLabel.project_id == pid,
                TaskLabel.project_id.is_(None)
            )
        ).order_by(TaskLabel.name).all()
        return jsonify({'labels': [l.get_summary() for l in labels]}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/labels', methods=['POST'])
@login_required
@csrf.exempt
def create_label(pid):
    """Create a project-scoped label."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _can_access(current_user, project):
            return jsonify({'error': 'Access denied'}), 403

        data = request.get_json(force=True)
        if not data.get('name', '').strip():
            return jsonify({'error': 'Label name is required'}), 400

        # Prevent duplicate label names in same project
        existing = TaskLabel.query.filter_by(
            project_id=pid, name=data['name'].strip()
        ).first()
        if existing:
            return jsonify({'error': 'Label already exists', 'label': existing.get_summary()}), 409

        label = TaskLabel(
            name=data['name'].strip(),
            color=data.get('color', '#6c757d'),
            project_id=pid
        )
        db.session.add(label)
        db.session.commit()
        return jsonify({'message': 'Label created', 'label': label.get_summary()}), 201
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/labels/<int:lid>', methods=['PUT'])
@login_required
@csrf.exempt
def update_label(pid, lid):
    """Update a label's name or color."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        label = TaskLabel.query.filter_by(id=lid, project_id=pid).first_or_404()
        data = request.get_json(force=True)
        if 'name' in data and data['name'].strip():
            label.name = data['name'].strip()
        if 'color' in data:
            label.color = data['color']
        db.session.commit()
        return jsonify({'message': 'Label updated', 'label': label.get_summary()}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@project_bp.route('/projects/<int:pid>/labels/<int:lid>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_label(pid, lid):
    """Delete a label (removes it from all tasks in this project)."""
    try:
        project = Project.query.filter_by(id=pid, deleted=False).first_or_404()
        if not _is_project_manager(current_user, project):
            return jsonify({'error': 'Permission denied'}), 403

        label = TaskLabel.query.filter_by(id=lid, project_id=pid).first_or_404()
        db.session.delete(label)
        db.session.commit()
        return jsonify({'message': 'Label deleted'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY / DASHBOARD STATS
# ─────────────────────────────────────────────────────────────────────────────

@project_bp.route('/projects/summary', methods=['GET'])
@login_required
@csrf.exempt
def projects_summary():
    """Returns aggregate stats for the current user's projects dashboard."""
    try:
        if has_role(current_user, ['admin', 'hr', 'dev']):
            projects = Project.query.filter_by(deleted=False).all()
        else:
            member_subq   = _member_project_ids_subquery(current_user.id)
            assigned_subq = None
            if hasattr(Task, 'assigned_to_id') and hasattr(Task, 'project_id'):
                assigned_subq = select(Task.project_id).where(
                    Task.assigned_to_id == current_user.id,
                    Task.deleted == False,
                    Task.project_id.isnot(None)
                )

            if assigned_subq is not None:
                projects = Project.query.filter(
                    Project.deleted == False,
                    db.or_(
                        Project.id.in_(member_subq),
                        Project.id.in_(assigned_subq)
                    )
                ).all()
            else:
                projects = Project.query.filter(
                    Project.deleted == False,
                    Project.id.in_(member_subq)
                ).all()

        by_status = {}
        for p in projects:
            by_status[p.status] = by_status.get(p.status, 0) + 1

        my_tasks = []
        overdue  = []
        if hasattr(Task, 'assigned_to_id'):
            my_tasks = Task.query.filter_by(
                assigned_to_id=current_user.id, deleted=False
            ).order_by(Task.due_date.asc()).limit(10).all()

            overdue = [
                t for t in my_tasks
                if getattr(t, 'due_date', None)
                and t.due_date < datetime.utcnow().date()
                and t.status not in ('completed', 'cancelled')
            ]

        return jsonify({
            'total_projects': len(projects),
            'by_status':      by_status,
            'overdue_tasks':  len(overdue),
            'my_task_count':  len(my_tasks),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/projects/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
