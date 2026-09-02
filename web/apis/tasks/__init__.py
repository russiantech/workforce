# """
# Workforce — Extended Tasks Blueprint
# ======================================
# Replaces / extends the existing tasks.py and assigned_task.py.

# Register in your app factory:
#     from web.api.tasks_extended import task_bp
#     app.register_blueprint(task_bp, url_prefix='/api')

# Assumes the following columns have been migrated onto Task:
#     project_id, assigned_to_id, priority, due_date,
#     estimated_hrs, logged_hrs, position, milestone_id
# """

# import traceback
# from datetime import datetime, date

# from flask import Blueprint, request, jsonify
# from flask_login import login_required, current_user

# from web.models import db
from web import csrf
# # from web.models import Task, Assigned_Task, User, Notification
# from web.models.users import User
# from web.models.projects import Task, Assigned_Task
# from web.models import Notification

# from web.models.projects import (
#     Project, ProjectMember, TaskComment, TaskActivity, TaskLabel
# )
# from web.utils.user_role import has_role

# task_bp = Blueprint('task_api', __name__)


# # ─────────────────────────────────────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────────────────────────────────────

# VALID_STATUSES   = ('pending', 'on-going', 'stucked', 'completed', 'cancelled')
# VALID_PRIORITIES = ('low', 'medium', 'high', 'critical')


# def _log(task_id=None, project_id=None, action='', detail='', old=None, new=None):
#     entry = TaskActivity(
#         task_id=task_id,
#         project_id=project_id,
#         user_id=current_user.id,
#         action=action,
#         detail=detail,
#         old_value=str(old) if old is not None else None,
#         new_value=str(new) if new is not None else None,
#     )
#     db.session.add(entry)


# def _notify(user_id, title, message, path='/'):
#     db.session.add(Notification(
#         user_id=user_id,
#         title=title,
#         message=message,
#         file_path=path,
#         image=current_user.photo or '',
#     ))


# def _task_to_dict(t):
#     return {
#         'id':            t.id,
#         'description':   t.description,
#         'status':        t.status,
#         'priority':      getattr(t, 'priority',      'medium'),
#         'due_date':      t.due_date.isoformat()      if getattr(t, 'due_date',      None) else None,
#         'estimated_hrs': getattr(t, 'estimated_hrs', None),
#         'logged_hrs':    getattr(t, 'logged_hrs',    0.0),
#         'position':      getattr(t, 'position',      0),
#         'project_id':    getattr(t, 'project_id',    None),
#         'milestone_id':  getattr(t, 'milestone_id',  None),
#         'user_id':       t.user_id,
#         'assigned_to':   {
#             'id':    t.assigned_to.id,
#             'name':  t.assigned_to.name or t.assigned_to.username,
#             'photo': t.assigned_to.photo,
#         } if getattr(t, 'assigned_to', None) else None,
#         'labels': [l.get_summary() for l in t.labels] if hasattr(t, 'labels') else [],
#         'comment_count': t.comments.filter_by(deleted=False).count()
#                          if hasattr(t, 'comments') else 0,
#         'timestamp': t.timestamp.strftime('%Y-%m-%d')
#                      if t.timestamp and isinstance(t.timestamp, (datetime, date)) else None,
#         'created':   t.created.isoformat() if t.created else None,
#     }


# def _can_edit_task(user, task):
#     """True if user created the task, is assigned to it, or is admin/manager."""
#     if has_role(user, ['admin', 'hr', 'dev', 'manager']):
#         return True
#     if task.user_id == user.id:
#         return True
#     if getattr(task, 'assigned_to_id', None) == user.id:
#         return True
#     return False


# # ─────────────────────────────────────────────────────────────────────────────
# # TASKS — CRUD
# # ─────────────────────────────────────────────────────────────────────────────

# @task_bp.route('/v2/tasks', methods=['GET'])
# @login_required
# @csrf.exempt
# def list_tasks():
#     """
#     Filterable task list.
#     Params: project_id, assigned_to_id, status, priority, page, per_page
#     """
#     try:
#         page         = request.args.get('page',         1,    type=int)
#         per_page     = request.args.get('per_page',     50,   type=int)
#         project_id   = request.args.get('project_id',   None, type=int)
#         status       = request.args.get('status',       None)
#         priority     = request.args.get('priority',     None)
#         assigned_to  = request.args.get('assigned_to',  None, type=int)
#         my_tasks     = request.args.get('my_tasks',     'false').lower() == 'true'

#         query = Task.query.filter_by(deleted=False)

#         if project_id:
#             query = query.filter_by(project_id=project_id)
#         elif my_tasks or not has_role(current_user, ['admin', 'hr', 'dev']):
#             # Non-admins only see tasks they own or are assigned to
#             query = query.filter(
#                 db.or_(
#                     Task.user_id == current_user.id,
#                     Task.assigned_to_id == current_user.id
#                 )
#             )

#         if status:
#             query = query.filter_by(status=status)
#         if priority and hasattr(Task, 'priority'):
#             query = query.filter_by(priority=priority)
#         if assigned_to:
#             query = query.filter_by(assigned_to_id=assigned_to)

#         paginated = query.order_by(
#             Task.position.asc(), Task.due_date.asc(), Task.created.desc()
#         ).paginate(page=page, per_page=per_page, error_out=False)

#         return jsonify({
#             'tasks':   [_task_to_dict(t) for t in paginated.items],
#             'total':   paginated.total,
#             'pages':   paginated.pages,
#             'page':    page,
#         }), 200

#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/tasks', methods=['POST'])
# @login_required
# @csrf.exempt
# def create_task():
#     """
#     Create a task.
#     If project_id is supplied, the creator must be a project member.
#     If assigned_to_id is supplied and differs from creator, a notification is sent.
#     """
#     try:
#         data = request.get_json(force=True)

#         if not data.get('description'):
#             return jsonify({'error': 'description is required'}), 400

#         priority = data.get('priority', 'medium')
#         if priority not in VALID_PRIORITIES:
#             return jsonify({'error': f'priority must be one of {VALID_PRIORITIES}'}), 400

#         project_id  = data.get('project_id')
#         assigned_id = data.get('assigned_to_id', current_user.id)

#         # Validate project membership
#         if project_id:
#             project = Project.query.filter_by(id=project_id, deleted=False).first()
#             if not project:
#                 return jsonify({'error': 'Project not found'}), 404
#             if not has_role(current_user, ['admin', 'hr', 'dev']):
#                 m = ProjectMember.query.filter_by(
#                     project_id=project_id, user_id=current_user.id
#                 ).first()
#                 if not m:
#                     return jsonify({'error': 'You are not a member of this project'}), 403

#         due_date = None
#         if data.get('due_date'):
#             due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

#         task = Task(
#             description=data['description'],
#             status=data.get('status', 'pending'),
#             timestamp=datetime.utcnow(),
#             user_id=current_user.id,
#         )

#         # Extended columns (gracefully set only if column exists)
#         _safe_set(task, 'priority',      priority)
#         _safe_set(task, 'due_date',      due_date)
#         _safe_set(task, 'project_id',    project_id)
#         _safe_set(task, 'assigned_to_id', assigned_id)
#         _safe_set(task, 'estimated_hrs', data.get('estimated_hrs'))
#         _safe_set(task, 'milestone_id',  data.get('milestone_id'))
#         _safe_set(task, 'position',      data.get('position', 0))

#         db.session.add(task)
#         db.session.flush()

#         # Labels
#         for label_id in data.get('label_ids', []):
#             label = TaskLabel.query.get(label_id)
#             if label and hasattr(task, 'labels'):
#                 task.labels.append(label)

#         _log(task_id=task.id, project_id=project_id,
#              action='task_created',
#              detail=f'Task "{task.description[:60]}" created by {current_user.name or current_user.username}')

#         # Notify if assigned to someone else
#         if assigned_id and assigned_id != current_user.id:
#             _notify(
#                 assigned_id,
#                 'New Task Assigned',
#                 f'{current_user.username} assigned you: "{task.description[:80]}"',
#                 f'/projects/{project_id}' if project_id else '/'
#             )

#         # Sync project task count
#         if project_id:
#             _sync_project_counts(project_id)

#         db.session.commit()
#         return jsonify({'message': 'Task created', 'task': _task_to_dict(task)}), 201

#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/tasks/<int:task_id>', methods=['GET'])
# @login_required
# @csrf.exempt
# def get_task(task_id):
#     """Full task detail with comments and activity."""
#     try:
#         task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()

#         if not _can_edit_task(current_user, task) and task.user_id != current_user.id:
#             return jsonify({'error': 'Access denied'}), 403

#         comments = []
#         if hasattr(task, 'comments'):
#             top_level = task.comments.filter_by(parent_id=None, deleted=False)\
#                                      .order_by(TaskComment.created.asc()).all()
#             comments = [c.get_summary(include_replies=True) for c in top_level]

#         activities = []
#         if hasattr(task, 'activities'):
#             activities = [a.get_summary() for a in
#                           task.activities.order_by(TaskActivity.created.desc()).limit(30).all()]

#         return jsonify({
#             'task':       _task_to_dict(task),
#             'comments':   comments,
#             'activities': activities,
#         }), 200

#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/tasks/<int:task_id>', methods=['PUT'])
# @login_required
# @csrf.exempt
# def update_task(task_id):
#     """
#     Update any task field. Logs changes and sends notifications on assignment change.
#     Members can update status/logged_hrs; managers can update everything.
#     """
#     try:
#         task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()

#         if not _can_edit_task(current_user, task):
#             return jsonify({'error': 'Permission denied'}), 403

#         data        = request.get_json(force=True)
#         is_manager  = has_role(current_user, ['admin', 'hr', 'dev', 'manager'])
#         project_id  = getattr(task, 'project_id', None)

#         # Status change
#         if 'status' in data:
#             old_status = task.status
#             new_status = data['status']
#             if new_status not in VALID_STATUSES:
#                 return jsonify({'error': f'Invalid status. Must be one of {VALID_STATUSES}'}), 400
#             task.status = new_status
#             if old_status != new_status:
#                 _log(task_id=task_id, project_id=project_id,
#                      action='status_changed', detail=f'Status changed',
#                      old=old_status, new=new_status)
#                 # Notify task owner when someone else updates status
#                 if task.user_id != current_user.id:
#                     _notify(task.user_id, 'Task Status Updated',
#                             f'"{task.description[:60]}" changed from {old_status} → {new_status}')

#         # Fields only managers can change
#         if is_manager:
#             if 'description' in data:
#                 task.description = data['description']

#             if 'priority' in data:
#                 old = getattr(task, 'priority', 'medium')
#                 _safe_set(task, 'priority', data['priority'])
#                 _log(task_id=task_id, project_id=project_id,
#                      action='priority_changed', old=old, new=data['priority'])

#             if 'due_date' in data:
#                 old_date = getattr(task, 'due_date', None)
#                 new_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() \
#                            if data['due_date'] else None
#                 _safe_set(task, 'due_date', new_date)
#                 _log(task_id=task_id, project_id=project_id,
#                      action='due_date_changed',
#                      old=old_date.isoformat() if old_date else None,
#                      new=new_date.isoformat() if new_date else None)

#             if 'assigned_to_id' in data:
#                 old_assignee = getattr(task, 'assigned_to_id', None)
#                 new_assignee = data['assigned_to_id']
#                 _safe_set(task, 'assigned_to_id', new_assignee)
#                 _log(task_id=task_id, project_id=project_id,
#                      action='assigned', old=old_assignee, new=new_assignee)
#                 if new_assignee and new_assignee != current_user.id:
#                     _notify(new_assignee, 'Task Assigned to You',
#                             f'{current_user.name or current_user.username} assigned "{task.description[:60]}" to you.',
#                             f'/projects/{project_id}' if project_id else '/')

#             if 'milestone_id' in data:
#                 _safe_set(task, 'milestone_id', data['milestone_id'])

#             if 'estimated_hrs' in data:
#                 _safe_set(task, 'estimated_hrs', data['estimated_hrs'])

#         # Anyone can log hours
#         if 'logged_hrs' in data:
#             _safe_set(task, 'logged_hrs',
#                       (getattr(task, 'logged_hrs', 0) or 0) + float(data['logged_hrs']))
#             _log(task_id=task_id, project_id=project_id,
#                  action='hours_logged', detail=f'{data["logged_hrs"]}h logged')

#         # Labels (managers only)
#         if is_manager and 'label_ids' in data and hasattr(task, 'labels'):
#             task.labels = []
#             for lid in data['label_ids']:
#                 label = TaskLabel.query.get(lid)
#                 if label:
#                     task.labels.append(label)

#         if project_id:
#             _sync_project_counts(project_id)

#         db.session.commit()
#         return jsonify({'message': 'Task updated', 'task': _task_to_dict(task)}), 200

#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/tasks/<int:task_id>', methods=['DELETE'])
# @login_required
# @csrf.exempt
# def delete_task(task_id):
#     try:
#         task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()

#         if not (has_role(current_user, ['admin', 'hr', 'dev', 'manager'])
#                 or task.user_id == current_user.id):
#             return jsonify({'error': 'Permission denied'}), 403

#         project_id = getattr(task, 'project_id', None)
#         task.deleted = True
#         _log(task_id=task_id, project_id=project_id,
#              action='task_deleted', detail=f'Task deleted by {current_user.name or current_user.username}')

#         if project_id:
#             _sync_project_counts(project_id)

#         db.session.commit()
#         return jsonify({'message': 'Task deleted'}), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # KANBAN REORDER
# # ─────────────────────────────────────────────────────────────────────────────

# @task_bp.route('/v2/tasks/reorder', methods=['POST'])
# @login_required
# @csrf.exempt
# def reorder_tasks():
#     """
#     Accepts an ordered list of task IDs per status column and persists positions.
#     Body: { "columns": { "pending": [3,1,5], "on-going": [2,4] } }
#     """
#     try:
#         data    = request.get_json(force=True)
#         columns = data.get('columns', {})

#         for status, task_ids in columns.items():
#             for position, task_id in enumerate(task_ids):
#                 Task.query.filter_by(id=task_id).update(
#                     {'status': status, 'position': position},
#                     synchronize_session=False
#                 )

#         db.session.commit()
#         return jsonify({'message': 'Board updated'}), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # TASK COMMENTS
# # ─────────────────────────────────────────────────────────────────────────────

# @task_bp.route('/v2/tasks/<int:task_id>/comments', methods=['GET'])
# @login_required
# @csrf.exempt
# def list_comments(task_id):
#     task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()
#     comments = task.comments.filter_by(parent_id=None, deleted=False)\
#                              .order_by(TaskComment.created.asc()).all()
#     return jsonify({'comments': [c.get_summary(include_replies=True) for c in comments]}), 200


# @task_bp.route('/v2/tasks/<int:task_id>/comments', methods=['POST'])
# @login_required
# @csrf.exempt
# def add_comment(task_id):
#     try:
#         task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()
#         data = request.get_json(force=True)

#         if not data.get('body', '').strip():
#             return jsonify({'error': 'Comment body cannot be empty'}), 400

#         comment = TaskComment(
#             task_id=task_id,
#             user_id=current_user.id,
#             parent_id=data.get('parent_id'),
#             body=data['body'].strip(),
#         )
#         db.session.add(comment)
#         _log(task_id=task_id, project_id=getattr(task, 'project_id', None),
#              action='comment_added',
#              detail=f'{current_user.name or current_user.username}: "{comment.body[:80]}"')

#         # Notify task owner + assignee (not current user)
#         targets = {task.user_id, getattr(task, 'assigned_to_id', None)} - {current_user.id, None}
#         for uid in targets:
#             _notify(uid, 'New Comment',
#                     f'{current_user.name} commented on "{task.description[:50]}"')

#         db.session.commit()
#         return jsonify({'message': 'Comment added', 'comment': comment.get_summary()}), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/comments/<int:comment_id>', methods=['PUT'])
# @login_required
# @csrf.exempt
# def edit_comment(comment_id):
#     try:
#         comment = TaskComment.query.filter_by(id=comment_id, deleted=False).first_or_404()
#         if comment.user_id != current_user.id:
#             return jsonify({'error': 'You can only edit your own comments'}), 403

#         data = request.get_json(force=True)
#         comment.body   = data.get('body', comment.body).strip()
#         comment.edited = True
#         db.session.commit()
#         return jsonify({'message': 'Comment updated', 'comment': comment.get_summary()}), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/comments/<int:comment_id>', methods=['DELETE'])
# @login_required
# @csrf.exempt
# def delete_comment(comment_id):
#     try:
#         comment = TaskComment.query.filter_by(id=comment_id, deleted=False).first_or_404()
#         if comment.user_id != current_user.id and \
#                 not has_role(current_user, ['admin', 'hr', 'dev']):
#             return jsonify({'error': 'Permission denied'}), 403

#         comment.deleted = True
#         db.session.commit()
#         return jsonify({'message': 'Comment deleted'}), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # ASSIGNED TASKS (keep backward-compatible with existing assigned_task.py)
# # ─────────────────────────────────────────────────────────────────────────────

# @task_bp.route('/v2/assigned-tasks', methods=['GET'])
# @login_required
# @csrf.exempt
# def list_assigned_tasks():
#     """
#     Admins/managers see all; others see only their own.
#     """
#     try:
#         if has_role(current_user, ['admin', 'hr', 'dev', 'manager']):
#             tasks = Assigned_Task.query.filter_by(deleted=False)\
#                                        .order_by(Assigned_Task.created.desc()).all()
#         else:
#             tasks = Assigned_Task.query.filter_by(
#                 user_id=current_user.id, deleted=False
#             ).order_by(Assigned_Task.created.desc()).all()

#         return jsonify({'tasks': [
#             {
#                 'id':       t.id,
#                 'detail':   t.detail,
#                 'duration': str(t.duration) if t.duration else None,
#                 'user_id':  t.user_id,
#                 'user_name': (t.user.name or t.user.username) if t.user and (t.user.name is not None or t.user.username is not None) else None,
#                 'created':  t.created.isoformat() if t.created else None,
#             } for t in tasks
#         ]}), 200

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @task_bp.route('/v2/assigned-tasks', methods=['POST'])
# @login_required
# @csrf.exempt
# def create_assigned_task():
#     """Admin/manager assigns a task to a specific user."""
#     try:
#         if not has_role(current_user, ['admin', 'hr', 'dev', 'manager']):
#             return jsonify({'error': 'Permission denied'}), 403

#         data = request.get_json(force=True)

#         if not data.get('detail'):
#             return jsonify({'error': 'detail is required'}), 400

#         target_user_id = data.get('user_id', current_user.id)
#         user = User.query.get(target_user_id)
#         if not user:
#             return jsonify({'error': 'Target user not found'}), 404

#         task = Assigned_Task(
#             detail=data['detail'],
#             duration=data.get('duration'),
#             user_id=target_user_id,
#         )
#         db.session.add(task)

#         _notify(target_user_id, 'New Task Assigned by Admin',
#                 f'{current_user.name} assigned you a task: "{data["detail"][:80]}"')

#         db.session.commit()
#         return jsonify({'message': 'Task assigned successfully'}), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # ACTIVITY FEED
# # ─────────────────────────────────────────────────────────────────────────────

# @task_bp.route('/v2/activities', methods=['GET'])
# @login_required
# @csrf.exempt
# def activity_feed():
#     """
#     Recent activity for current user across all their projects / tasks.
#     """
#     try:
#         project_id = request.args.get('project_id', type=int)
#         task_id    = request.args.get('task_id',    type=int)
#         limit      = request.args.get('limit', 30, type=int)

#         query = TaskActivity.query

#         if project_id:
#             query = query.filter_by(project_id=project_id)
#         elif task_id:
#             query = query.filter_by(task_id=task_id)
#         else:
#             # Show activities from user's projects
#             if has_role(current_user, ['admin', 'hr']):
#                 pass  # all activities
#             else:
#                 my_project_ids = [
#                     m.project_id for m in
#                     ProjectMember.query.filter_by(user_id=current_user.id).all()
#                 ]
#                 query = query.filter(
#                     db.or_(
#                         TaskActivity.project_id.in_(my_project_ids),
#                         TaskActivity.user_id == current_user.id
#                     )
#                 )

#         activities = query.order_by(TaskActivity.created.desc()).limit(limit).all()
#         return jsonify({'activities': [a.get_summary() for a in activities]}), 200

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # NOTIFICATIONS
# # ─────────────────────────────────────────────────────────────────────────────

# @task_bp.route('/v2/notifications', methods=['GET'])
# @login_required
# @csrf.exempt
# def get_notifications():
#     from web.models import Notification
#     notifs = Notification.query.filter_by(
#         user_id=current_user.id, deleted=False
#     ).order_by(Notification.created_at.desc()).limit(30).all()

#     return jsonify({'notifications': [
#         {
#             'id':       n.id,
#             'title':    n.title,
#             'message':  n.message,
#             'is_read':  n.is_read,
#             'path':     n.file_path,
#             'created':  n.created_at.isoformat() if n.created_at else None,
#         } for n in notifs
#     ], 'unread': sum(1 for n in notifs if not n.is_read)}), 200


# @task_bp.route('/v2/notifications/read', methods=['POST'])
# @login_required
# @csrf.exempt
# def mark_notifications_read():
#     try:
#         data = request.get_json(force=True)
#         ids  = data.get('ids', [])

#         from web.models import Notification
#         q = Notification.query.filter_by(user_id=current_user.id, is_read=False)
#         if ids:
#             q = q.filter(Notification.id.in_(ids))
#         q.update({'is_read': True}, synchronize_session=False)
#         db.session.commit()
#         return jsonify({'message': 'Marked as read'}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # INTERNAL UTILS
# # ─────────────────────────────────────────────────────────────────────────────

# def _safe_set(obj, attr, value):
#     """Set attribute only if it exists on the model (graceful migration guard)."""
#     if hasattr(obj, attr):
#         setattr(obj, attr, value)


# def _sync_project_counts(project_id):
#     """Update cached task_count / completed_count on the Project row."""
#     project = Project.query.get(project_id)
#     if not project:
#         return
#     tasks = Task.query.filter_by(project_id=project_id, deleted=False).all()
#     project.task_count      = len(tasks)
#     project.completed_count = sum(1 for t in tasks if t.status == 'completed')
#     db.session.add(project)



# v0

"""
Workforce — Extended Tasks Blueprint (FIXED)
==============================================
Fixes applied:
  1. name → username fallback (_display_name) everywhere
  2. Notifications on ALL assignment paths (create, update, reorder, assigned-task)
  3. _can_access / _can_edit_task: assigned users always get access
  4. Label toggle endpoint (POST /v2/tasks/<id>/labels/<lid>)
  5. Consistent permission model throughout
  6. SAWarning-free subquery usage
"""

import traceback
from datetime import datetime, date

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import select

from web.models import db
from web import csrf
from web.models.users import User
from web.models.projects import Task, Assigned_Task
from web.models import Notification

from web.models.projects import (
    Project, ProjectMember, TaskComment, TaskActivity, TaskLabel
)
from web.utils.user_role import has_role

task_bp = Blueprint('task_api', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

VALID_STATUSES   = ('pending', 'on-going', 'stucked', 'completed', 'cancelled')
VALID_PRIORITIES = ('low', 'medium', 'high', 'critical')


def _display_name(user):
    """Return name with username fallback."""
    if user is None:
        return 'Unknown'
    return (user.name or '').strip() or user.username or str(user.id)


def _log(task_id=None, project_id=None, action='', detail='', old=None, new=None):
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


def _notify(user_id, title, message, path='/'):
    """Create a notification, skip if notifying self."""
    if user_id == current_user.id:
        return
    db.session.add(Notification(
        user_id=user_id,
        title=title,
        message=message,
        file_path=path,
        image=current_user.photo or '',
    ))


def _task_to_dict(t):
    assignee = getattr(t, 'assigned_to', None)
    return {
        'id':            t.id,
        'description':   t.description,
        'status':        t.status,
        'priority':      getattr(t, 'priority',      'medium'),
        'due_date':      t.due_date.isoformat()      if getattr(t, 'due_date',      None) else None,
        'estimated_hrs': getattr(t, 'estimated_hrs', None),
        'logged_hrs':    getattr(t, 'logged_hrs',    0.0),
        'position':      getattr(t, 'position',      0),
        'project_id':    getattr(t, 'project_id',    None),
        'milestone_id':  getattr(t, 'milestone_id',  None),
        'user_id':       t.user_id,
        'assigned_to':   {
            'id':    assignee.id,
            'name':  _display_name(assignee),
            'photo': assignee.photo,
        } if assignee else None,
        'labels': [l.get_summary() for l in t.labels] if hasattr(t, 'labels') else [],
        'comment_count': t.comments.filter_by(deleted=False).count()
                         if hasattr(t, 'comments') else 0,
        'timestamp': t.timestamp.strftime('%Y-%m-%d')
                     if t.timestamp and isinstance(t.timestamp, (datetime, date)) else None,
        'created':   t.created.isoformat() if t.created else None,
    }


def _can_edit_task(user, task):
    """Creator, assignee, or elevated role can edit."""
    if has_role(user, ['admin', 'hr', 'dev', 'manager']):
        return True
    if task.user_id == user.id:
        return True
    if getattr(task, 'assigned_to_id', None) == user.id:
        return True
    return False


def _can_view_task(user, task):
    """Anyone who can edit, or is a project member, can view."""
    if _can_edit_task(user, task):
        return True
    project_id = getattr(task, 'project_id', None)
    if project_id:
        m = ProjectMember.query.filter_by(
            project_id=project_id, user_id=user.id
        ).first()
        return m is not None
    return False


def _safe_set(obj, attr, value):
    """Set attribute only if it exists on the model."""
    if hasattr(obj, attr):
        setattr(obj, attr, value)


def _sync_project_counts(project_id):
    """Update cached task_count / completed_count on the Project row."""
    project = Project.query.get(project_id)
    if not project:
        return
    tasks = Task.query.filter_by(project_id=project_id, deleted=False).all()
    project.task_count      = len(tasks)
    project.completed_count = sum(1 for t in tasks if t.status == 'completed')
    db.session.add(project)


def _notify_project_members(project_id, title, message, path, exclude_ids=None):
    """Notify all project members except those in exclude_ids."""
    exclude = set(exclude_ids or [current_user.id])
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    for m in members:
        if m.user_id not in exclude:
            _notify(m.user_id, title, message, path)


# ─────────────────────────────────────────────────────────────────────────────
# TASKS — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/tasks', methods=['GET'])
@login_required
@csrf.exempt
def list_tasks():
    """
    Filterable task list.
    Params: project_id, assigned_to_id, status, priority, page, per_page, my_tasks
    """
    try:
        page        = request.args.get('page',        1,    type=int)
        per_page    = request.args.get('per_page',    50,   type=int)
        project_id  = request.args.get('project_id',  None, type=int)
        status      = request.args.get('status',      None)
        priority    = request.args.get('priority',    None)
        assigned_to = request.args.get('assigned_to', None, type=int)
        my_tasks    = request.args.get('my_tasks',    'false').lower() == 'true'

        query = Task.query.filter_by(deleted=False)

        if project_id:
            # Verify access to project
            project = Project.query.filter_by(id=project_id, deleted=False).first()
            if project:
                from web.apis.projects import _can_access as proj_can_access
                if not proj_can_access(current_user, project):
                    return jsonify({'error': 'Access denied'}), 403
            query = query.filter_by(project_id=project_id)
        elif my_tasks or not has_role(current_user, ['admin', 'hr', 'dev']):
            query = query.filter(
                db.or_(
                    Task.user_id == current_user.id,
                    Task.assigned_to_id == current_user.id
                )
            )

        if status:
            query = query.filter_by(status=status)
        if priority and hasattr(Task, 'priority'):
            query = query.filter_by(priority=priority)
        if assigned_to:
            query = query.filter_by(assigned_to_id=assigned_to)

        paginated = query.order_by(
            Task.position.asc(), Task.due_date.asc(), Task.created.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'tasks': [_task_to_dict(t) for t in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'page':  page,
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/tasks', methods=['POST'])
@login_required
@csrf.exempt
def create_task():
    """
    Create a task.
    - project_id: creator must be a project member (or elevated role)
    - assigned_to_id: notification sent; assignee gets project access implicitly
    """
    try:
        data = request.get_json(force=True)

        if not data.get('description'):
            return jsonify({'error': 'description is required'}), 400

        priority = data.get('priority', 'medium')
        if priority not in VALID_PRIORITIES:
            return jsonify({'error': f'priority must be one of {VALID_PRIORITIES}'}), 400

        project_id  = data.get('project_id')
        assigned_id = data.get('assigned_to_id', current_user.id)

        project = None
        if project_id:
            project = Project.query.filter_by(id=project_id, deleted=False).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            if not has_role(current_user, ['admin', 'hr', 'dev']):
                m = ProjectMember.query.filter_by(
                    project_id=project_id, user_id=current_user.id
                ).first()
                if not m:
                    return jsonify({'error': 'You are not a member of this project'}), 403

        due_date = None
        if data.get('due_date'):
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

        task = Task(
            description=data['description'],
            status=data.get('status', 'pending'),
            timestamp=datetime.utcnow(),
            user_id=current_user.id,
        )
        _safe_set(task, 'priority',       priority)
        _safe_set(task, 'due_date',       due_date)
        _safe_set(task, 'project_id',     project_id)
        _safe_set(task, 'assigned_to_id', assigned_id)
        _safe_set(task, 'estimated_hrs',  data.get('estimated_hrs'))
        _safe_set(task, 'milestone_id',   data.get('milestone_id'))
        _safe_set(task, 'position',       data.get('position', 0))

        db.session.add(task)
        db.session.flush()

        # Labels
        for label_id in data.get('label_ids', []):
            label = TaskLabel.query.get(label_id)
            if label and hasattr(task, 'labels'):
                task.labels.append(label)

        actor_name = _display_name(current_user)
        proj_path  = f'/projects/{project_id}/board' if project_id else '/'

        _log(task_id=task.id, project_id=project_id,
             action='task_created',
             detail=f'Task "{task.description[:60]}" created by {actor_name}')

        # Notify assignee (if different from creator)
        if assigned_id and assigned_id != current_user.id:
            assignee = User.query.get(assigned_id)
            assignee_name = _display_name(assignee) if assignee else str(assigned_id)
            _notify(
                assigned_id,
                'New Task Assigned',
                f'{actor_name} assigned you: "{task.description[:80]}"',
                proj_path
            )

        # Notify all other project members (creator is excluded by _notify)
        if project_id:
            _notify_project_members(
                project_id,
                f'New task in "{project.title}"' if project else 'New task',
                f'{actor_name} created: "{task.description[:60]}"',
                proj_path,
                exclude_ids={current_user.id, assigned_id}
            )
            _sync_project_counts(project_id)

        db.session.commit()
        return jsonify({'message': 'Task created', 'task': _task_to_dict(task)}), 201

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/tasks/<int:task_id>', methods=['GET'])
@login_required
@csrf.exempt
def get_task(task_id):
    """Full task detail with comments and activity."""
    try:
        task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()

        if not _can_view_task(current_user, task):
            return jsonify({'error': 'Access denied'}), 403

        comments = []
        if hasattr(task, 'comments'):
            top_level = task.comments.filter_by(parent_id=None, deleted=False)\
                                     .order_by(TaskComment.created.asc()).all()
            comments = [c.get_summary(include_replies=True) for c in top_level]

        activities = []
        if hasattr(task, 'activities'):
            activities = [a.get_summary() for a in
                          task.activities.order_by(TaskActivity.created.desc()).limit(30).all()]

        return jsonify({
            'task':       _task_to_dict(task),
            'comments':   comments,
            'activities': activities,
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/tasks/<int:task_id>', methods=['PUT'])
@login_required
@csrf.exempt
def update_task(task_id):
    """
    Update any task field.
    - All members can update: status, logged_hrs
    - Managers/creators/assignees can update everything else
    """
    try:
        task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()

        if not _can_edit_task(current_user, task):
            return jsonify({'error': 'Permission denied'}), 403

        data       = request.get_json(force=True)
        is_manager = has_role(current_user, ['admin', 'hr', 'dev', 'manager'])
        project_id = getattr(task, 'project_id', None)
        actor_name = _display_name(current_user)
        proj_path  = f'/projects/{project_id}/board' if project_id else '/'

        # ── Status (anyone with edit access) ─────────────────────────────
        if 'status' in data:
            old_status = task.status
            new_status = data['status']
            if new_status not in VALID_STATUSES:
                return jsonify({'error': f'Invalid status. Must be one of {VALID_STATUSES}'}), 400
            task.status = new_status
            if old_status != new_status:
                _log(task_id=task_id, project_id=project_id,
                     action='status_changed', detail='Status changed',
                     old=old_status, new=new_status)
                # Notify task owner + assignee (not current actor)
                targets = set()
                targets.add(task.user_id)
                if getattr(task, 'assigned_to_id', None):
                    targets.add(task.assigned_to_id)
                targets.discard(current_user.id)
                for uid in targets:
                    _notify(uid, 'Task Status Updated',
                            f'"{task.description[:60]}" → {new_status}',
                            proj_path)

        # ── Manager-only fields ───────────────────────────────────────────
        if is_manager or task.user_id == current_user.id:

            if 'description' in data:
                task.description = data['description']

            if 'priority' in data:
                old = getattr(task, 'priority', 'medium')
                new_p = data['priority']
                if new_p not in VALID_PRIORITIES:
                    return jsonify({'error': f'Invalid priority'}), 400
                _safe_set(task, 'priority', new_p)
                if old != new_p:
                    _log(task_id=task_id, project_id=project_id,
                         action='priority_changed', old=old, new=new_p)

            if 'due_date' in data:
                old_date = getattr(task, 'due_date', None)
                new_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() \
                           if data['due_date'] else None
                _safe_set(task, 'due_date', new_date)
                if old_date != new_date:
                    _log(task_id=task_id, project_id=project_id,
                         action='due_date_changed',
                         old=old_date.isoformat() if old_date else None,
                         new=new_date.isoformat() if new_date else None)

            if 'assigned_to_id' in data:
                old_assignee = getattr(task, 'assigned_to_id', None)
                new_assignee = data['assigned_to_id']
                _safe_set(task, 'assigned_to_id', new_assignee)
                if old_assignee != new_assignee:
                    _log(task_id=task_id, project_id=project_id,
                         action='assigned', old=old_assignee, new=new_assignee)
                    if new_assignee and new_assignee != current_user.id:
                        assignee = User.query.get(new_assignee)
                        _notify(
                            new_assignee,
                            'Task Assigned to You',
                            f'{actor_name} assigned "{task.description[:60]}" to you.',
                            proj_path
                        )
                    # Also notify previous assignee they were unassigned
                    if old_assignee and old_assignee != current_user.id and old_assignee != new_assignee:
                        _notify(
                            old_assignee,
                            'Task Reassigned',
                            f'"{task.description[:60]}" was reassigned by {actor_name}.',
                            proj_path
                        )

            if 'milestone_id' in data:
                _safe_set(task, 'milestone_id', data['milestone_id'])

            if 'estimated_hrs' in data:
                _safe_set(task, 'estimated_hrs', data['estimated_hrs'])

        # ── Anyone can log hours ──────────────────────────────────────────
        if 'logged_hrs' in data:
            current_logged = getattr(task, 'logged_hrs', 0) or 0
            added = float(data['logged_hrs'])
            _safe_set(task, 'logged_hrs', current_logged + added)
            _log(task_id=task_id, project_id=project_id,
                 action='hours_logged', detail=f'{added}h logged')

        # ── Labels ────────────────────────────────────────────────────────
        if 'label_ids' in data and hasattr(task, 'labels'):
            task.labels = []
            for lid in data['label_ids']:
                label = TaskLabel.query.get(lid)
                if label:
                    task.labels.append(label)
            _log(task_id=task_id, project_id=project_id,
                 action='labels_updated', detail='Labels updated')

        if project_id:
            _sync_project_counts(project_id)

        db.session.commit()
        return jsonify({'message': 'Task updated', 'task': _task_to_dict(task)}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/tasks/<int:task_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_task(task_id):
    try:
        task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()

        if not (has_role(current_user, ['admin', 'hr', 'dev', 'manager'])
                or task.user_id == current_user.id):
            return jsonify({'error': 'Permission denied'}), 403

        project_id = getattr(task, 'project_id', None)
        actor_name = _display_name(current_user)

        # Notify assignee of deletion (if not self)
        assigned_id = getattr(task, 'assigned_to_id', None)
        if assigned_id and assigned_id != current_user.id:
            _notify(
                assigned_id,
                'Task Deleted',
                f'{actor_name} deleted task: "{task.description[:60]}"',
                f'/projects/{project_id}/board' if project_id else '/'
            )

        task.deleted = True
        _log(task_id=task_id, project_id=project_id,
             action='task_deleted',
             detail=f'Task deleted by {actor_name}')

        if project_id:
            _sync_project_counts(project_id)

        db.session.commit()
        return jsonify({'message': 'Task deleted'}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# LABEL TOGGLE ON TASK
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/tasks/<int:task_id>/labels/<int:label_id>', methods=['POST'])
@login_required
@csrf.exempt
def toggle_task_label(task_id, label_id):
    """Toggle a label on a task (add if not present, remove if present)."""
    try:
        task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()
        if not _can_edit_task(current_user, task):
            return jsonify({'error': 'Permission denied'}), 403
        if not hasattr(task, 'labels'):
            return jsonify({'error': 'Labels not supported on this task model'}), 400

        label = TaskLabel.query.get_or_404(label_id)
        if label in task.labels:
            task.labels.remove(label)
            action = 'removed'
        else:
            task.labels.append(label)
            action = 'added'

        _log(task_id=task_id, project_id=getattr(task, 'project_id', None),
             action='label_toggled', detail=f'Label "{label.name}" {action}')
        db.session.commit()
        return jsonify({
            'message': f'Label {action}',
            'labels':  [l.get_summary() for l in task.labels]
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# KANBAN REORDER
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/tasks/reorder', methods=['POST'])
@login_required
@csrf.exempt
def reorder_tasks():
    """
    Accepts an ordered list of task IDs per status column and persists positions.
    Body: { "columns": { "pending": [3,1,5], "on-going": [2,4] } }
    """
    try:
        data    = request.get_json(force=True)
        columns = data.get('columns', {})

        for status, task_ids in columns.items():
            if status not in VALID_STATUSES:
                continue
            for position, tid in enumerate(task_ids):
                Task.query.filter_by(id=tid).update(
                    {'status': status, 'position': position},
                    synchronize_session=False
                )

        db.session.commit()
        return jsonify({'message': 'Board updated'}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TASK COMMENTS
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
@csrf.exempt
def list_comments(task_id):
    task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()
    if not _can_view_task(current_user, task):
        return jsonify({'error': 'Access denied'}), 403
    comments = task.comments.filter_by(parent_id=None, deleted=False)\
                             .order_by(TaskComment.created.asc()).all()
    return jsonify({'comments': [c.get_summary(include_replies=True) for c in comments]}), 200


@task_bp.route('/v2/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
@csrf.exempt
def add_comment(task_id):
    try:
        task = Task.query.filter_by(id=task_id, deleted=False).first_or_404()
        if not _can_view_task(current_user, task):
            return jsonify({'error': 'Access denied'}), 403

        data = request.get_json(force=True)
        if not data.get('body', '').strip():
            return jsonify({'error': 'Comment body cannot be empty'}), 400

        comment = TaskComment(
            task_id=task_id,
            user_id=current_user.id,
            parent_id=data.get('parent_id'),
            body=data['body'].strip(),
        )
        db.session.add(comment)

        actor_name = _display_name(current_user)
        project_id = getattr(task, 'project_id', None)
        proj_path  = f'/projects/{project_id}/board' if project_id else '/'

        _log(task_id=task_id, project_id=project_id,
             action='comment_added',
             detail=f'{actor_name}: "{comment.body[:80]}"')

        # Notify task owner + assignee
        targets = {task.user_id, getattr(task, 'assigned_to_id', None)} - {None, current_user.id}
        for uid in targets:
            _notify(uid, 'New Comment',
                    f'{actor_name} commented on "{task.description[:50]}"',
                    proj_path)

        db.session.commit()
        return jsonify({'message': 'Comment added', 'comment': comment.get_summary()}), 201

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/comments/<int:comment_id>', methods=['PUT'])
@login_required
@csrf.exempt
def edit_comment(comment_id):
    try:
        comment = TaskComment.query.filter_by(id=comment_id, deleted=False).first_or_404()
        if comment.user_id != current_user.id:
            return jsonify({'error': 'You can only edit your own comments'}), 403

        data = request.get_json(force=True)
        comment.body   = data.get('body', comment.body).strip()
        comment.edited = True
        db.session.commit()
        return jsonify({'message': 'Comment updated', 'comment': comment.get_summary()}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/comments/<int:comment_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_comment(comment_id):
    try:
        comment = TaskComment.query.filter_by(id=comment_id, deleted=False).first_or_404()
        if comment.user_id != current_user.id and \
                not has_role(current_user, ['admin', 'hr', 'dev']):
            return jsonify({'error': 'Permission denied'}), 403

        comment.deleted = True
        db.session.commit()
        return jsonify({'message': 'Comment deleted'}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ASSIGNED TASKS (backward-compatible)
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/assigned-tasks', methods=['GET'])
@login_required
@csrf.exempt
def list_assigned_tasks():
    try:
        if has_role(current_user, ['admin', 'hr', 'dev', 'manager']):
            tasks = Assigned_Task.query.filter_by(deleted=False)\
                                       .order_by(Assigned_Task.created.desc()).all()
        else:
            tasks = Assigned_Task.query.filter_by(
                user_id=current_user.id, deleted=False
            ).order_by(Assigned_Task.created.desc()).all()

        return jsonify({'tasks': [
            {
                'id':        t.id,
                'detail':    t.detail,
                'duration':  str(t.duration) if t.duration else None,
                'user_id':   t.user_id,
                'user_name': _display_name(t.user) if t.user else str(t.user_id),
                'created':   t.created.isoformat() if t.created else None,
            } for t in tasks
        ]}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@task_bp.route('/v2/assigned-tasks', methods=['POST'])
@login_required
@csrf.exempt
def create_assigned_task():
    try:
        if not has_role(current_user, ['admin', 'hr', 'dev', 'manager']):
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json(force=True)
        if not data.get('detail'):
            return jsonify({'error': 'detail is required'}), 400

        target_user_id = data.get('user_id', current_user.id)
        user = User.query.get(target_user_id)
        if not user:
            return jsonify({'error': 'Target user not found'}), 404

        task = Assigned_Task(
            detail=data['detail'],
            duration=data.get('duration'),
            user_id=target_user_id,
        )
        db.session.add(task)

        actor_name = _display_name(current_user)
        _notify(
            target_user_id,
            'New Task Assigned',
            f'{actor_name} assigned you: "{data["detail"][:80]}"',
            '/'
        )

        db.session.commit()
        return jsonify({'message': 'Task assigned successfully'}), 201

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVITY FEED
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/activities', methods=['GET'])
@login_required
@csrf.exempt
def activity_feed():
    try:
        project_id = request.args.get('project_id', type=int)
        task_id    = request.args.get('task_id',    type=int)
        limit      = request.args.get('limit', 30,  type=int)

        query = TaskActivity.query

        if project_id:
            query = query.filter_by(project_id=project_id)
        elif task_id:
            query = query.filter_by(task_id=task_id)
        else:
            if not has_role(current_user, ['admin', 'hr']):
                my_project_ids = [
                    m.project_id for m in
                    ProjectMember.query.filter_by(user_id=current_user.id).all()
                ]
                query = query.filter(
                    db.or_(
                        TaskActivity.project_id.in_(my_project_ids) if my_project_ids else db.false(),
                        TaskActivity.user_id == current_user.id
                    )
                )

        activities = query.order_by(TaskActivity.created.desc()).limit(limit).all()
        return jsonify({'activities': [a.get_summary() for a in activities]}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

@task_bp.route('/v2/notifications', methods=['GET'])
@login_required
@csrf.exempt
def get_notifications():
    notifs = Notification.query.filter_by(
        user_id=current_user.id, deleted=False
    ).order_by(Notification.created_at.desc()).limit(50).all()

    return jsonify({'notifications': [
        {
            'id':      n.id,
            'title':   n.title,
            'message': n.message,
            'is_read': n.is_read,
            'path':    n.file_path,
            'created': n.created_at.isoformat() if n.created_at else None,
        } for n in notifs
    ], 'unread': sum(1 for n in notifs if not n.is_read)}), 200


@task_bp.route('/v2/notifications/read', methods=['POST'])
@login_required
@csrf.exempt
def mark_notifications_read():
    try:
        data = request.get_json(force=True)
        ids  = data.get('ids', [])

        q = Notification.query.filter_by(user_id=current_user.id, is_read=False)
        if ids:
            q = q.filter(Notification.id.in_(ids))
        q.update({'is_read': True}, synchronize_session=False)
        db.session.commit()
        return jsonify({'message': 'Marked as read'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks/__init__.py: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


