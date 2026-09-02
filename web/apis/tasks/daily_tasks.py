# web/apis/daily_tasks.py
"""
Daily Tasks API
===============
Admin-assignable, day-to-day duty tasks — tracked the same way project
tasks are (status / priority / due date / activity log), but not tied to
a project. A task can be given to more than one person; each assignee
tracks their own progress and can log exactly what they did, the same
pattern used on project tasks (TaskComment / TaskActivity).

Every assignment / status change / logged update raises BOTH an in-app
Notification and a branded email (see web/utils/email.py -
send_notification_email), so nothing gets missed just because someone
isn't looking at the app right now.

Endpoints (all under /api, see app factory):
    GET    /api/daily-tasks               list tasks (scoped by role, filterable)
    POST   /api/daily-tasks               create + assign a task   (assignees allowed for managers)
    GET    /api/daily-tasks/summary       status counts for KPI cards
    GET    /api/daily-tasks/<id>          full detail: task + assignees + logs + activity feed
    PUT    /api/daily-tasks/<id>          update task fields and/or your own progress status
    DELETE /api/daily-tasks/<id>          delete a task            (manager, or the assigner)
    POST   /api/daily-tasks/<id>/logs     add a work-log entry ("what I did")
    GET    /api/daily-tasks/<id>/logs     list the log + activity timeline for a task

Visibility rules:
    - Managers (admin / hr / dev / md) can see & manage tasks for every
      staff member.
    - Everyone else only sees tasks where they are an active assignee, and
      may only:
        * update THEIR OWN progress status
        * add work-log entries to tasks they're assigned to
      They cannot reassign, retitle, change priority/due date, or delete a
      manager-issued task.
"""

from datetime import datetime, date

from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import current_user, login_required

from web.apis.utils.resolve_Weights import _resolve_weight
from web.models.projects import Assigned_Task, DailyTaskAssignee, DailyTaskLog, DailyTaskActivity
from web.models.task_weight_config import TaskWeightDefault
from web.models.users import User
from web.models import Notification
from web.models import db
from web import csrf
from web.utils.user_role import has_role
from web.utils.email import send_notification_email

daily_task_bp = Blueprint('daily_task_api', __name__)

MANAGE_ROLES = ['admin', 'hr', 'dev', 'md']
VALID_STATUSES = ('pending', 'in_progress', 'completed', 'missed', 'cancelled')
VALID_PRIORITIES = ('low', 'medium', 'high', 'critical')


def _is_manager():
    return has_role(current_user, MANAGE_ROLES)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _notify(user_id, title, message, task_id=None, badge='Daily Task'):
    """Create an in-app notification AND send a branded email — every
    Daily Task update reaches the person both ways. Skips notifying
    yourself (no point emailing someone about their own action)."""
    if not user_id or user_id == current_user.id:
        return
    action_url = url_for('daily_task_views.daily_tasks_page', task=task_id, _external=True) if task_id \
        else url_for('daily_task_views.daily_tasks_page', _external=True)

    db.session.add(Notification(
        user_id=user_id,
        title=title,
        message=message[:250],
        file_path='/daily-tasks' + (f'?task={task_id}' if task_id else ''),
        image=current_user.photo or '',
    ))
    user = User.query.get(user_id)
    if user:
        send_notification_email(user, title, message, action_url=action_url, badge=badge)


def _log_activity(task, action, detail=None, old_value=None, new_value=None):
    db.session.add(DailyTaskActivity(
        task_id=task.id, user_id=current_user.id, action=action,
        detail=detail, old_value=old_value, new_value=new_value,
    ))


def _accessible_task_query():
    query = Assigned_Task.query.filter_by(deleted=False)
    if not _is_manager():
        query = query.join(DailyTaskAssignee).filter(
            DailyTaskAssignee.user_id == current_user.id,
            DailyTaskAssignee.deleted == False,
        )
    return query


def _get_task_or_404(task_id, require_access=True):
    task = Assigned_Task.query.filter_by(id=task_id, deleted=False).first()
    if not task:
        return None, (jsonify({'success': False, 'error': 'Task not found'}), 404)
    if require_access and not _is_manager():
        if not task.assignee_row_for(current_user.id):
            return None, (jsonify({'success': False, 'error': 'You do not have access to this task'}), 403)
    return task, None


# ── LIST ─────────────────────────────────────────────────────────────────
@daily_task_bp.route('/daily-tasks', methods=['GET'])
@login_required
@csrf.exempt
def list_daily_tasks():
    try:
        query = _accessible_task_query()

        if _is_manager():
            assignee_id = request.args.get('assigned_to_id', type=int)
            if assignee_id:
                query = query.join(DailyTaskAssignee).filter(
                    DailyTaskAssignee.user_id == assignee_id,
                    DailyTaskAssignee.deleted == False,
                )

        status = request.args.get('status')
        if status:
            query = query.filter(Assigned_Task.status == status)

        due = request.args.get('due_date')
        if due:
            parsed = _parse_date(due)
            if parsed:
                query = query.filter(Assigned_Task.due_date == parsed)

        tasks = query.order_by(Assigned_Task.due_date.is_(None), Assigned_Task.due_date.asc(),
                                Assigned_Task.created.desc()).distinct().all()
        return jsonify({'success': True, 'tasks': [t.get_summary(for_user_id=current_user.id) for t in tasks]}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 200


# ── SUMMARY (KPI counts) ─────────────────────────────────────────────────
# @daily_task_bp.route('/daily-tasks/summary', methods=['GET'])
# @login_required
# @csrf.exempt
# def daily_tasks_summary():
#     try:
#         tasks = _accessible_task_query().distinct().all()
#         counts = {'pending': 0, 'in_progress': 0, 'completed': 0, 'missed': 0, 'cancelled': 0}
#         today = date.today()
#         overdue = 0
#         for t in tasks:
#             counts[t.status] = counts.get(t.status, 0) + 1
#             if t.due_date and t.due_date < today and t.status not in ('completed', 'cancelled'):
#                 overdue += 1

#         return jsonify({'success': True, 'total': len(tasks), 'counts': counts, 'overdue': overdue}), 200
#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
#         return jsonify({'success': False, 'error': f'{e}'}), 200


@daily_task_bp.route('/daily-tasks/summary', methods=['GET'])
def daily_tasks_summary():
    tasks = _accessible_task_query().distinct().all()
    counts = {'pending': 0, 'in_progress': 0, 'completed': 0, 'missed': 0, 'cancelled': 0}
    weighted_counts = {'pending': 0, 'in_progress': 0, 'completed': 0, 'missed': 0}
    today = date.today()
    overdue = 0
    weighted_overdue = 0

    for t in tasks:
        w = getattr(t, 'weight', 3)
        counts[t.status] = counts.get(t.status, 0) + 1
        if t.status in weighted_counts:
            weighted_counts[t.status] += w

        if t.due_date and t.due_date < today and t.status not in ('completed', 'cancelled'):
            overdue += 1
            weighted_overdue += w

    return jsonify({
        'success': True,
        'total': len(tasks),
        'counts': counts,
        'weighted_counts': weighted_counts,
        'overdue': overdue,
        'weighted_overdue': weighted_overdue,
    }), 200

# ── DETAIL (task + assignees + logs + activity) ──────────────────────────
@daily_task_bp.route('/daily-tasks/<int:task_id>', methods=['GET'])
@login_required
@csrf.exempt
def get_daily_task(task_id):
    try:
        task, err = _get_task_or_404(task_id)
        if err:
            return err
        summary = task.get_summary(for_user_id=current_user.id)
        summary['logs'] = [l.get_summary() for l in task.logs if not l.deleted]
        summary['activities'] = [a.get_summary() for a in task.activities]
        return jsonify({'success': True, 'task': summary}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 200


# ── CREATE / ASSIGN ──────────────────────────────────────────────────────
@daily_task_bp.route('/daily-tasks', methods=['POST'])
@login_required
@csrf.exempt
def create_daily_task():
    try:
        data = request.get_json(force=True, silent=True) or {}

        detail = (data.get('detail') or data.get('title') or '').strip()
        if not detail:
            return jsonify({'success': False, 'error': 'Please provide a task description'}), 400

        # Accept either assigned_to_ids (list, preferred) or the older
        # single assigned_to_id, for backward compatibility.
        assignee_ids = data.get('assigned_to_ids')
        if not assignee_ids:
            single = data.get('assigned_to_id')
            assignee_ids = [single] if single else []
        assignee_ids = list({int(a) for a in assignee_ids if a})

        if not assignee_ids:
            assignee_ids = [current_user.id]

        if not _is_manager():
            # Non-managers may only ever create a task for themself.
            if any(a != current_user.id for a in assignee_ids):
                return jsonify({'success': False, 'error': 'You are not allowed to assign tasks to other staff'}), 403
            assignee_ids = [current_user.id]

        users = User.query.filter(User.id.in_(assignee_ids)).all()
        if not users:
            return jsonify({'success': False, 'error': 'Selected staff member(s) not found'}), 404

        priority = data.get('priority', 'medium')
        if priority not in VALID_PRIORITIES:
            priority = 'medium'

        # Resolve weight
        dept = getattr(current_user, 'department', None)
        weight, locked = _resolve_weight(data, department=dept, is_manager=_is_manager())

        new_task = Assigned_Task(
            title=(data.get('title') or '').strip() or None,
            detail=detail,
            user_id=current_user.id,
            assigned_by_id=current_user.id,
            status='pending',
            priority=priority,
            weight=weight,
            weight_locked=locked,
            due_date=_parse_date(data.get('due_date')),
        )
        db.session.add(new_task)
        db.session.flush()  # get new_task.id before adding children

        for u in users:
            db.session.add(DailyTaskAssignee(task_id=new_task.id, user_id=u.id))

        new_task.recompute_status()
        _log_activity(new_task, 'created', detail=f'Task created and assigned to {len(users)} staff member(s)')

        for u in users:
            _notify(u.id, 'New task assigned',
                    f'{current_user.name or current_user.username} assigned you: "{new_task.title or detail[:60]}"',
                    task_id=new_task.id)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Task assigned successfully', 'task': new_task.get_summary(for_user_id=current_user.id)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 400


# ── UPDATE ────────────────────────────────────────────────────────────────
@daily_task_bp.route('/daily-tasks/<int:task_id>', methods=['PUT'])
@login_required
@csrf.exempt
def update_daily_task(task_id):
    try:
        task, err = _get_task_or_404(task_id)
        if err:
            return err

        data = request.get_json(force=True, silent=True) or {}
        is_manager = _is_manager()

        if is_manager:
            if 'title' in data:
                task.title = (data.get('title') or '').strip() or None
            if 'detail' in data and data.get('detail'):
                task.detail = data['detail']
            if 'priority' in data and data.get('priority') in VALID_PRIORITIES:
                old_p = task.priority
                task.priority = data['priority']
                if old_p != task.priority:  
                    _log_activity(task, 'priority_changed', old_value=old_p, new_value=task.priority)
            
            if 'weight' in data:
                new_w = int(data['weight'])
                task.weight = max(1, min(new_w, 10))
            if 'weight_locked' in data:
                task.weight_locked = bool(data['weight_locked'])

            if 'due_date' in data:
                old_d = task.due_date.isoformat() if task.due_date else None
                task.due_date = _parse_date(data.get('due_date'))
                new_d = task.due_date.isoformat() if task.due_date else None
                if old_d != new_d:
                    _log_activity(task, 'due_date_changed', old_value=old_d, new_value=new_d)

            if 'assigned_to_ids' in data:
                new_ids = {int(a) for a in (data.get('assigned_to_ids') or []) if a}
                current_rows = {r.user_id: r for r in task.active_assignees()}
                current_ids = set(current_rows.keys())

                for uid in new_ids - current_ids:
                    u = User.query.get(uid)
                    if not u:
                        continue
                    db.session.add(DailyTaskAssignee(task_id=task.id, user_id=uid))
                    _log_activity(task, 'assigned', detail=f'{u.name or u.username} was added to this task')
                    _notify(uid, 'New task assigned',
                            f'{current_user.name or current_user.username} assigned you: "{task.title or task.detail[:60]}"',
                            task_id=task.id)

                for uid in current_ids - new_ids:
                    row = current_rows[uid]
                    row.deleted = True
                    u = User.query.get(uid)
                    _log_activity(task, 'unassigned', detail=f'{(u.name or u.username) if u else "A staff member"} was removed from this task')

                if not new_ids:
                    return jsonify({'success': False, 'error': 'A task must have at least one assignee'}), 400

        # 
        # Non-manager: weight ignored if locked
        if not is_manager and not task.weight_locked and 'weight' in data:
            _, max_w, _ = TaskWeightDefault.get_weight(task.priority, task.department)
            try:
                task.weight = max(1, min(int(data['weight']), max_w))
            except (ValueError, TypeError):
                pass

        # Anyone with access may update THEIR OWN progress status.
        if 'status' in data and data.get('status') in VALID_STATUSES:
            my_row = task.assignee_row_for(current_user.id)
            if my_row:
                old_status = my_row.status
                my_row.status = data['status']
                my_row.completed_at = func_now() if data['status'] == 'completed' else None
                if old_status != my_row.status:
                    _log_activity(task, 'status_changed', old_value=old_status, new_value=my_row.status)
                    if task.assigned_by_id:
                        _notify(task.assigned_by_id, 'Task progress updated',
                                f'{current_user.name or current_user.username} marked "{task.title or task.detail[:60]}" as {my_row.status.replace("_", " ")}',
                                task_id=task.id, badge='Progress update')
            elif is_manager:
                # Manager can update all assignees' statuses even if not an assignee themselves
                for assignee in task.active_assignees():
                    old_status = assignee.status
                    assignee.status = data['status']
                    assignee.completed_at = func_now() if data['status'] == 'completed' else None
                    if old_status != assignee.status:
                        _log_activity(task, 'status_changed', detail='Manager updated assignee status', old_value=old_status, new_value=assignee.status)

        task.recompute_status()
        db.session.commit()
        summary = task.get_summary(for_user_id=current_user.id)
        return jsonify({'success': True, 'message': 'Task updated successfully', 'task': summary}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 400


def func_now():
    from sqlalchemy.sql import func
    return func.now()


# ── WORK LOGS ──────────────────────────────────────────────────────────────
@daily_task_bp.route('/daily-tasks/<int:task_id>/logs', methods=['GET'])
@login_required
@csrf.exempt
def list_daily_task_logs(task_id):
    try:
        task, err = _get_task_or_404(task_id)
        if err:
            return err
        return jsonify({
            'success': True,
            'logs': [l.get_summary() for l in task.logs if not l.deleted],
            'activities': [a.get_summary() for a in task.activities],
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 200


@daily_task_bp.route('/daily-tasks/<int:task_id>/logs', methods=['POST'])
@login_required
@csrf.exempt
def add_daily_task_log(task_id):
    """Record exactly what the current user did towards this task, and
    optionally update their own progress status at the same time."""
    try:
        task, err = _get_task_or_404(task_id)
        is_manager = _is_manager()
        
        if err:
            return err

        data = request.get_json(force=True, silent=True) or {}
        body = (data.get('body') or '').strip()
        if not body:
            return jsonify({'success': False, 'error': 'Please describe what was done'}), 400

        log = DailyTaskLog(task_id=task.id, user_id=current_user.id, body=body)
        db.session.add(log)
        _log_activity(task, 'log_added', detail='Logged progress on this task')

        # new_status = data.get('status')
        # my_row = task.assignee_row_for(current_user.id)
        # if new_status in VALID_STATUSES and my_row:
        #     old_status = my_row.status
        #     my_row.status = new_status
        #     my_row.completed_at = func_now() if new_status == 'completed' else None
        #     if old_status != new_status:
        #         _log_activity(task, 'status_changed', old_value=old_status, new_value=new_status)
        #     task.recompute_status()

        new_status = data.get('status')
        my_row = task.assignee_row_for(current_user.id)
        if new_status in VALID_STATUSES:
            if my_row:
                old_status = my_row.status
                my_row.status = new_status
                my_row.completed_at = func_now() if new_status == 'completed' else None
                if old_status != new_status:
                    _log_activity(task, 'status_changed', old_value=old_status, new_value=new_status)
                task.recompute_status()
            elif is_manager:
                for assignee in task.active_assignees():
                    old_status = assignee.status
                    assignee.status = new_status
                    assignee.completed_at = func_now() if new_status == 'completed' else None
                    if old_status != new_status:
                        _log_activity(task, 'status_changed', detail='Manager updated assignee status', old_value=old_status, new_value=assignee.status)
                task.recompute_status()

        # Let the assigner AND every other assignee know progress was logged.
        notify_targets = set()
        if task.assigned_by_id:
            notify_targets.add(task.assigned_by_id)
        for a in task.active_assignees():
            notify_targets.add(a.user_id)
        for uid in notify_targets:
            _notify(uid, 'Task update logged',
                    f'{current_user.name or current_user.username} logged an update on "{task.title or task.detail[:60]}": “{body[:120]}”',
                    task_id=task.id, badge='Activity log')

        db.session.commit()
        return jsonify({'success': True, 'message': 'Update logged', 'log': log.get_summary(),
                         'task': task.get_summary(for_user_id=current_user.id)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 400


# ── DELETE ────────────────────────────────────────────────────────────────
@daily_task_bp.route('/daily-tasks/<int:task_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_daily_task(task_id):
    try:
        task = Assigned_Task.query.filter_by(id=task_id, deleted=False).first()
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        if not _is_manager() and task.assigned_by_id != current_user.id:
            return jsonify({'success': False, 'error': 'You cannot delete this task'}), 403

        task.deleted = True
        _log_activity(task, 'deleted', detail='Task deleted')
        db.session.commit()
        return jsonify({'success': True, 'message': 'Task deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Unhandled error in web/apis/daily_tasks.py: {e}")
        return jsonify({'success': False, 'error': f'{e}'}), 400
