# """
# Workforce — Dashboard Analytics API
# =====================================
# Register:
#     from web.apis.dashboard import dashboard_bp
#     app.register_blueprint(dashboard_bp, url_prefix='/api')

# Endpoints
# ─────────
# GET /api/dashboard/overview      → headline KPI cards
# GET /api/dashboard/attendance    → attendance trend (chart data)
# GET /api/dashboard/projects      → project health & completion stats
# GET /api/dashboard/tasks         → task status breakdown
# GET /api/dashboard/leaderboard   → staff performance ranking (admin)
# GET /api/dashboard/my-stats      → personal stats for current user
# """

# import traceback
# from datetime import date, timedelta

# from flask import Blueprint, request, jsonify, current_app
# from flask_login import login_required, current_user
# from sqlalchemy import func, select

# from web.models import db
# from web import csrf
# from web.models.projects import Assigned_Task, DailyTaskAssignee
# from web.models.users import User
# from web.utils.user_role import has_role

# dashboard_bp = Blueprint('dashboard_api', __name__)

# # ── Optional model imports (graceful if not present) ─────────────────────────
# try:
#     from web.models.attendance import Attendance
#     HAS_ATTENDANCE = True
# except ImportError:
#     HAS_ATTENDANCE = False

# try:
#     from web.models.projects import (
#         Project, ProjectMember, Task, TaskActivity,
#         Assigned_Task, DailyTaskAssignee
#     )
#     HAS_PROJECTS = True
# except ImportError:
#     HAS_PROJECTS = False
    
# try:
#     from web.models.projects import TemporaryTask
#     HAS_TEMP = True
# except ImportError:
#     HAS_TEMP = False


# # ─────────────────────────────────────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────────────────────────────────────

# def _dn(user):
#     if not user: return 'Unknown'
#     return (user.name or '').strip() or user.username or str(user.id)


# def _is_admin(user):
#     return has_role(user, ['admin', 'md', 'hr', 'manager'])


# def _date_range(days=30):
#     end   = date.today()
#     start = end - timedelta(days=days - 1)
#     return start, end


# def _pct(part, total):
#     return round(part / total * 100, 1) if total else 0


# # ─────────────────────────────────────────────────────────────────────────────
# # OVERVIEW CARDS
# # ─────────────────────────────────────────────────────────────────────────────

# @dashboard_bp.route('/dashboard/overview', methods=['GET'])
# @login_required
# @csrf.exempt
# def overview():
#     """
#     Headline KPI cards.
#     Admin: org-wide.   Staff: personal.
#     """
#     try:
#         today     = date.today()
#         wk_start  = today - timedelta(days=6)
#         is_admin  = _is_admin(current_user)

#         result = {}

#         # ── Attendance ────────────────────────────────────────────────────
#         if HAS_ATTENDANCE:
#             att_q = Attendance.query.join(User)
#             if not is_admin:
#                 att_q = att_q.filter(Attendance.user_id == current_user.id)

#             today_att = att_q.filter(
#                 func.date(Attendance.created) == today
#             ).count()

#             week_att  = att_q.filter(
#                 func.date(Attendance.created) >= wk_start
#             ).count()

#             total_att = att_q.count()

#             result['attendance_today'] = today_att
#             result['attendance_week']  = week_att
#             result['attendance_total'] = total_att
#         else:
#             result.update({'attendance_today': 0, 'attendance_week': 0, 'attendance_total': 0})

#         # ── Projects ──────────────────────────────────────────────────────
#         if HAS_PROJECTS:
#             if is_admin:
#                 proj_q = Project.query.filter_by(deleted=False)
#             else:
#                 member_subq = select(ProjectMember.project_id).where(
#                     ProjectMember.user_id == current_user.id
#                 )
#                 proj_q = Project.query.filter(
#                     Project.deleted == False,
#                     Project.id.in_(member_subq)
#                 )

#             total_proj     = proj_q.count()
#             active_proj    = proj_q.filter_by(status='active').count()
#             completed_proj = proj_q.filter_by(status='completed').count()

#             result['projects_total']     = total_proj
#             result['projects_active']    = active_proj
#             result['projects_completed'] = completed_proj

#             # ── Tasks ─────────────────────────────────────────────────────
#             task_q = Task.query.filter_by(deleted=False)
#             if not is_admin:
#                 task_q = task_q.filter(
#                     db.or_(
#                         Task.user_id == current_user.id,
#                         Task.assigned_to_id == current_user.id,
#                     )
#                 )

#             total_tasks     = task_q.count()
#             pending_tasks   = task_q.filter_by(status='pending').count()
#             ongoing_tasks   = task_q.filter_by(status='on-going').count()
#             completed_tasks = task_q.filter_by(status='completed').count()
#             overdue_tasks   = task_q.filter(
#                 Task.due_date < today,
#                 Task.status.notin_(['completed', 'cancelled']),
#                 Task.due_date.isnot(None)
#             ).count()

#             result.update({
#                 'tasks_total':     total_tasks,
#                 'tasks_pending':   pending_tasks,
#                 'tasks_ongoing':   ongoing_tasks,
#                 'tasks_completed': completed_tasks,
#                 'tasks_overdue':   overdue_tasks,
#             })
#         else:
#             result.update({
#                 'projects_total': 0, 'projects_active': 0, 'projects_completed': 0,
#                 'tasks_total': 0, 'tasks_pending': 0, 'tasks_ongoing': 0,
#                 'tasks_completed': 0, 'tasks_overdue': 0,
#             })

#         # ── Temp tasks ────────────────────────────────────────────────────
#         if HAS_TEMP:
#             tt_q = TemporaryTask.query.filter_by(is_deleted=False)
#             if not is_admin:
#                 tt_q = tt_q.filter_by(assigned_to=current_user.id)
#             result['temp_tasks_active'] = tt_q.filter(
#                 TemporaryTask.status.in_(['pending', 'in-progress'])
#             ).count()
#         else:
#             result['temp_tasks_active'] = 0

#         # ── Staff count (admin only) ───────────────────────────────────────
#         if is_admin:
#             result['total_staff'] = User.query.filter_by(deleted=False).count()

#         result['is_admin'] = is_admin

#         return jsonify(result), 200

#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # ATTENDANCE TREND  (30-day daily bar chart)
# # ─────────────────────────────────────────────────────────────────────────────

# @dashboard_bp.route('/dashboard/attendance', methods=['GET'])
# @login_required
# @csrf.exempt
# def attendance_trend():
#     try:
#         days      = request.args.get('days', 30, type=int)
#         d_from, d_to = _date_range(days)
#         is_admin  = _is_admin(current_user)

#         if not HAS_ATTENDANCE:
#             return jsonify({'series': [], 'total': 0}), 200

#         q = (
#             Attendance.query
#             .join(User)
#             .filter(
#                 User.deleted == False,
#                 func.date(Attendance.created) >= d_from,
#                 func.date(Attendance.created) <= d_to,
#             )
#         )
#         if not is_admin:
#             q = q.filter(Attendance.user_id == current_user.id)

#         records = q.order_by(Attendance.created).all()

#         # Bucket by date
#         day_map = {}
#         for i in range(days):
#             d = (d_from + timedelta(days=i)).strftime('%Y-%m-%d')
#             day_map[d] = 0
#         for a in records:
#             if a.created:
#                 key = a.created.strftime('%Y-%m-%d')
#                 if key in day_map:
#                     day_map[key] += 1

#         series = [{'date': k, 'label': k[5:], 'count': v}
#                   for k, v in sorted(day_map.items())]

#         # Average per-day
#         non_zero = [s['count'] for s in series if s['count'] > 0]
#         avg = round(sum(non_zero) / len(non_zero), 1) if non_zero else 0

#         return jsonify({
#             'series':  series,
#             'total':   len(records),
#             'average': avg,
#             'days':    days,
#         }), 200

#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # PROJECTS HEALTH
# # ─────────────────────────────────────────────────────────────────────────────

# @dashboard_bp.route('/dashboard/projects', methods=['GET'])
# @login_required
# @csrf.exempt
# def projects_health():
#     try:
#         if not HAS_PROJECTS:
#             return jsonify({'by_status': [], 'by_priority': [], 'recent': []}), 200

#         is_admin = _is_admin(current_user)

#         if is_admin:
#             proj_q = Project.query.filter_by(deleted=False)
#         else:
#             member_subq = select(ProjectMember.project_id).where(
#                 ProjectMember.user_id == current_user.id
#             )
#             proj_q = Project.query.filter(
#                 Project.deleted == False,
#                 Project.id.in_(member_subq)
#             )

#         projects = proj_q.all()

#         # Status breakdown
#         status_map = {}
#         for p in projects:
#             status_map[p.status] = status_map.get(p.status, 0) + 1
#         by_status = [{'status': k, 'count': v} for k, v in status_map.items()]

#         # Priority breakdown
#         pri_map = {}
#         for p in projects:
#             pri = getattr(p, 'priority', 'medium')
#             pri_map[pri] = pri_map.get(pri, 0) + 1
#         by_priority = [{'priority': k, 'count': v} for k, v in pri_map.items()]

#         # Completion rates
#         completion_data = []
#         for p in projects:
#             tc = getattr(p, 'task_count', 0) or 0
#             cc = getattr(p, 'completed_count', 0) or 0
#             completion_data.append({
#                 'id':       p.id,
#                 'title':    p.title,
#                 'color':    getattr(p, 'color', '#2563eb'),
#                 'status':   p.status,
#                 'priority': getattr(p, 'priority', 'medium'),
#                 'progress': _pct(cc, tc),
#                 'task_count':      tc,
#                 'completed_count': cc,
#                 'due_date':        p.due_date.isoformat() if p.due_date else None,
#             })
#         completion_data.sort(key=lambda x: x['progress'])

#         return jsonify({
#             'by_status':   by_status,
#             'by_priority': by_priority,
#             'projects':    completion_data,
#             'total':       len(projects),
#         }), 200

#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # TASK BREAKDOWN
# # ─────────────────────────────────────────────────────────────────────────────

# @dashboard_bp.route('/dashboard/tasks', methods=['GET'])
# @login_required
# @csrf.exempt
# def tasks_breakdown():
#     try:
#         if not HAS_PROJECTS:
#             return jsonify({'by_status': [], 'by_priority': []}), 200

#         today    = date.today()
#         is_admin = _is_admin(current_user)

#         q = Task.query.filter_by(deleted=False)
#         if not is_admin:
#             q = q.filter(db.or_(
#                 Task.user_id == current_user.id,
#                 Task.assigned_to_id == current_user.id,
#             ))

#         tasks = q.all()

#         status_map = {}
#         pri_map    = {}
#         for t in tasks:
#             status_map[t.status] = status_map.get(t.status, 0) + 1
#             pri = getattr(t, 'priority', 'medium')
#             pri_map[pri] = pri_map.get(pri, 0) + 1

#         by_status   = [{'status': k, 'count': v} for k, v in status_map.items()]
#         by_priority = [{'priority': k, 'count': v} for k, v in pri_map.items()]

#         overdue = [
#             t for t in tasks
#             if getattr(t, 'due_date', None)
#             and t.due_date < today
#             and t.status not in ('completed', 'cancelled')
#         ]
#         overdue_list = [{
#             'id':          t.id,
#             'description': t.description,
#             'due_date':    t.due_date.isoformat() if t.due_date else None,
#             'priority':    getattr(t, 'priority', 'medium'),
#             'project_id':  getattr(t, 'project_id', None),
#             'assigned_to': {
#                 'id':   t.assigned_to.id,
#                 'name': _dn(t.assigned_to),
#             } if getattr(t, 'assigned_to', None) else None,
#         } for t in sorted(overdue, key=lambda x: x.due_date)]

        
#         return jsonify({
#             'by_status':   by_status,
#             'by_priority': by_priority,
#             'overdue':     overdue_list[:10],
#             'overdue_count': len(overdue),
#             'total':       len(tasks),
#         }), 200

#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # LEADERBOARD  (admin only — who's doing the most)
# # ─────────────────────────────────────────────────────────────────────────────

# @dashboard_bp.route('/dashboard/leaderboard', methods=['GET'])
# @login_required
# @csrf.exempt
# def leaderboard():
#     """
#     Staff performance leaderboard for admin/manager.
#     Scores are composite of: attendance days + completed tasks + project contributions.
#     """
#     if not _is_admin(current_user):
#         return jsonify({'error': 'Permission denied'}), 403

#     try:
#         days        = request.args.get('days', 30, type=int)
#         d_from, d_to = _date_range(days)
#         users       = User.query.filter_by(deleted=False).all()
#         board       = []

#         for u in users:
#             score = 0
#             att_days = 0
#             tasks_done = 0
#             tasks_total = 0
#             projects_count = 0

#             # Attendance
#             if HAS_ATTENDANCE:
#                 att_days = (
#                     Attendance.query
#                     .filter_by(user_id=u.id)
#                     .filter(func.date(Attendance.created) >= d_from)
#                     .count()
#                 )
#                 score += att_days * 2  # 2pts per attendance day

#             # Tasks
#             if HAS_PROJECTS:
#                 user_tasks = Task.query.filter(
#                     Task.deleted == False,
#                     db.or_(
#                         Task.user_id == u.id,
#                         Task.assigned_to_id == u.id,
#                     )
#                 )
#                 tasks_total = user_tasks.count()
#                 tasks_done  = user_tasks.filter_by(status='completed').count()
                
#                 # score += tasks_done * 5   # 5pts per completed task
                
#                 # v2 of scoring with weighted
#                 # OLD: score += tasks_done * 5
#                 # NEW: weighted score
#                 user_tasks = Task.query.filter(
#                     Task.deleted == False,
#                     db.or_(Task.user_id == u.id, Task.assigned_to_id == u.id)
#                 )
#                 tasks_total = user_tasks.count()
#                 tasks_done  = 0
#                 weighted_done = 0
#                 weighted_overdue = 0
#                 today       = date.today()

#                 for t in user_tasks.all():
#                     w = getattr(t, 'weight', 3)
#                     if t.status == 'completed':
#                         tasks_done += 1
#                         weighted_done += w
#                     elif getattr(t, 'due_date', None) and t.due_date < d_to and t.status not in ('completed', 'cancelled'):
#                         weighted_overdue += w

#                 # Also include daily tasks and temp tasks in the same loop if desired,
#                 # or keep separate. Below shows the unified approach:

#                 # Daily tasks
#                 daily_q = Assigned_Task.query.filter_by(deleted=False).join(DailyTaskAssignee).filter(
#                     DailyTaskAssignee.user_id == u.id,
#                     DailyTaskAssignee.deleted == False
#                 )
#                 for dt in daily_q.all():
#                     w = getattr(dt, 'weight', 3)
#                     if dt.status == 'completed':
#                         weighted_done += w
#                     elif dt.due_date and dt.due_date < today and dt.status not in ('completed', 'cancelled'):
#                         weighted_overdue += w

#                 # Temp tasks
#                 temp_q = TemporaryTask.query.filter_by(assigned_to=u.id, is_deleted=False)
#                 for tt in temp_q.all():
#                     w = getattr(tt, 'weight', 3)
#                     if tt.status == 'done':
#                         weighted_done += w

#                 score += weighted_done * 5      # 5 pts per weight unit completed
#                 score -= weighted_overdue * 3   # -3 pts per weight unit overdue
                
#                 # Overdue penalty
#                 overdue_cnt = user_tasks.filter(
#                     Task.due_date < d_to,
#                     Task.status.notin_(['completed', 'cancelled']),
#                     Task.due_date.isnot(None)
#                 ).count()
#                 score -= overdue_cnt * 3  # -3pts per overdue

#                 # Project memberships
#                 projects_count = ProjectMember.query.filter_by(user_id=u.id).count()
#                 score += projects_count  # 1pt per project

#             board.append({
#                 'user_id':       u.id,
#                 'name':          _dn(u),
#                 'photo':         u.photo,
#                 'username':      u.username,
#                 'system_roles':  u.my_roles,
#                 'att_days':      att_days,
#                 'tasks_done':    tasks_done,
#                 'tasks_total':   tasks_total,
#                 'projects':      projects_count,
#                 'completion_rate': _pct(tasks_done, tasks_total),
#                 'score':         max(score, 0),
#             })

#         board.sort(key=lambda x: x['score'], reverse=True)

#         # Add rank and performance label
#         labels = ['Top Performer', 'High Performer', 'On Track',
#                   'Needs Attention', 'At Risk']
#         n = len(board)
#         for i, b in enumerate(board):
#             b['rank'] = i + 1
#             if n <= 1:
#                 b['label'] = 'Top Performer'
#             else:
#                 idx = min(int(i / n * len(labels)), len(labels) - 1)
#                 b['label'] = labels[idx]

#         return jsonify({
#             'leaderboard': board,
#             'days':        days,
#             'date_from':   str(d_from),
#             'date_to':     str(d_to),
#         }), 200

#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500


# # ─────────────────────────────────────────────────────────────────────────────
# # MY STATS  (personal dashboard for non-admin users)
# # ─────────────────────────────────────────────────────────────────────────────

# """ 
#         my_tasks = Task.query.filter(
#             Task.deleted == False,
#             db.or_(Task.user_id == uid, Task.assigned_to_id == uid)
#         ).all()

#         total_weight = 0
#         completed_weight = 0
#         for t in my_tasks:
#             w = getattr(t, 'weight', 3)
#             total_weight += w
#             if t.status == 'completed':
#                 completed_weight += w

#         result['task_completion_rate'] = _pct(completed_weight, total_weight)
#         result['weighted_tasks_completed'] = completed_weight
#         result['weighted_tasks_total'] = total_weight
# """
# # @dashboard_bp.route('/dashboard/my-stats', methods=['GET'])
# # @login_required
# # @csrf.exempt
# # def my_stats():
# #     try:
# #         days        = request.args.get('days', 30, type=int)
# #         d_from, d_to = _date_range(days)
# #         today       = date.today()
# #         uid         = current_user.id

# #         result = {'user_id': uid, 'days': days}

# #         # Attendance
# #         if HAS_ATTENDANCE:
# #             my_att = (
# #                 Attendance.query
# #                 .filter_by(user_id=uid)
# #                 .filter(func.date(Attendance.created) >= d_from)
# #                 .all()
# #             )
# #             result['att_days']  = len(my_att)
# #             result['att_rate']  = _pct(len(my_att), days)
# #             # 7-day sparkline
# #             wk_map = {}
# #             for i in range(7):
# #                 d = (today - timedelta(days=6 - i)).strftime('%Y-%m-%d')
# #                 wk_map[d] = 0
# #             for a in Attendance.query.filter_by(user_id=uid)\
# #                     .filter(func.date(Attendance.created) >= today - timedelta(days=6)).all():
# #                 if a.created:
# #                     key = a.created.strftime('%Y-%m-%d')
# #                     if key in wk_map:
# #                         wk_map[key] += 1
# #             result['att_week'] = [{'date': k, 'day': k[5:], 'present': v > 0}
# #                                    for k, v in sorted(wk_map.items())]
# #         else:
# #             result.update({'att_days': 0, 'att_rate': 0, 'att_week': []})

# #         # Tasks
# #         if HAS_PROJECTS:
# #             my_tasks = Task.query.filter(
# #                 Task.deleted == False,
# #                 db.or_(Task.user_id == uid, Task.assigned_to_id == uid)
# #             ).all()
            
# #             total     = len(my_tasks)
# #             completed = sum(1 for t in my_tasks if t.status == 'completed')
# #             pending   = sum(1 for t in my_tasks if t.status == 'pending')
# #             ongoing   = sum(1 for t in my_tasks if t.status == 'on-going')
# #             overdue   = sum(
# #                 1 for t in my_tasks
# #                 if getattr(t, 'due_date', None)
# #                 and t.due_date < today
# #                 and t.status not in ('completed', 'cancelled')
# #             )
# #             result.update({
# #                 'tasks_total':     total,
# #                 'tasks_completed': completed,
# #                 'tasks_pending':   pending,
# #                 'tasks_ongoing':   ongoing,
# #                 'tasks_overdue':   overdue,
# #                 'task_completion_rate': _pct(completed, total),
# #             })

# #             # Project memberships
# #             result['project_count'] = ProjectMember.query.filter_by(user_id=uid).count()
# #         else:
# #             result.update({
# #                 'tasks_total': 0, 'tasks_completed': 0, 'tasks_pending': 0,
# #                 'tasks_ongoing': 0, 'tasks_overdue': 0,
# #                 'task_completion_rate': 0, 'project_count': 0,
# #             })

# #         # Temp tasks
# #         if HAS_TEMP:
# #             my_tt = TemporaryTask.query.filter_by(assigned_to=uid, is_deleted=False).all()
# #             result['temp_tasks_active'] = sum(
# #                 1 for t in my_tt if t.status in ('pending', 'in-progress')
# #             )
# #         else:
# #             result['temp_tasks_active'] = 0

# #         return jsonify(result), 200

# #     except Exception as e:
# #         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
# #         traceback.print_exc()
# #         return jsonify({'error': str(e)}), 500


# # v2
# @dashboard_bp.route('/dashboard/my-stats', methods=['GET'])
# @login_required
# @csrf.exempt
# def my_stats():
#     try:
#         days        = request.args.get('days', 30, type=int)
#         d_from, d_to = _date_range(days)
#         today       = date.today()
#         uid         = current_user.id

#         result = {'user_id': uid, 'days': days}

#         # ── Attendance (unchanged) ──────────────────────────────────────
#         if HAS_ATTENDANCE:
#             my_att = (
#                 Attendance.query
#                 .filter_by(user_id=uid)
#                 .filter(func.date(Attendance.created) >= d_from)
#                 .all()
#             )
#             result['att_days']  = len(my_att)
#             result['att_rate']  = _pct(len(my_att), days)
#             wk_map = {}
#             for i in range(7):
#                 d = (today - timedelta(days=6 - i)).strftime('%Y-%m-%d')
#                 wk_map[d] = 0
#             for a in Attendance.query.filter_by(user_id=uid)\
#                     .filter(func.date(Attendance.created) >= today - timedelta(days=6)).all():
#                 if a.created:
#                     key = a.created.strftime('%Y-%m-%d')
#                     if key in wk_map:
#                         wk_map[key] += 1
#             result['att_week'] = [{'date': k, 'day': k[5:], 'present': v > 0}
#                                    for k, v in sorted(wk_map.items())]
#         else:
#             result.update({'att_days': 0, 'att_rate': 0, 'att_week': []})

#         # ── Unified counters (Project + Daily + Temp) ───────────────────
#         total_count     = 0
#         completed_count = 0
#         pending_count   = 0
#         ongoing_count   = 0
#         overdue_count   = 0

#         total_weight     = 0
#         completed_weight = 0
#         pending_weight   = 0
#         ongoing_weight   = 0
#         overdue_weight   = 0

#         # 1. Project Tasks
#         if HAS_PROJECTS:
#             my_tasks = Task.query.filter(
#                 Task.deleted == False,
#                 db.or_(Task.user_id == uid, Task.assigned_to_id == uid)
#             ).all()

#             for t in my_tasks:
#                 w = getattr(t, 'weight', 3)
#                 total_count  += 1
#                 total_weight += w

#                 if t.status == 'completed':
#                     completed_count  += 1
#                     completed_weight += w
#                 elif t.status == 'pending':
#                     pending_count    += 1
#                     pending_weight   += w
#                 elif t.status == 'on-going':
#                     ongoing_count    += 1
#                     ongoing_weight   += w

#                 if getattr(t, 'due_date', None) and t.due_date < today \
#                         and t.status not in ('completed', 'cancelled'):
#                     overdue_count  += 1
#                     overdue_weight += w

#             result['project_count'] = ProjectMember.query.filter_by(user_id=uid).count()
#         else:
#             result['project_count'] = 0

#         # 2. Daily Tasks (Assigned_Task via DailyTaskAssignee)
#         #    We use the INDIVIDUAL assignee status so a user gets credit
#         #    even when other assignees on the same task are still pending.
#         if HAS_PROJECTS:
#             daily_rows = (
#                 db.session.query(DailyTaskAssignee, Assigned_Task)
#                 .join(Assigned_Task, DailyTaskAssignee.task_id == Assigned_Task.id)
#                 .filter(DailyTaskAssignee.user_id == uid)
#                 .filter(DailyTaskAssignee.deleted == False)
#                 .filter(Assigned_Task.deleted == False)
#                 .all()
#             )
#             for da, dt in daily_rows:
#                 w = getattr(dt, 'weight', 3)
#                 total_count  += 1
#                 total_weight += w

#                 if da.status == 'completed':
#                     completed_count  += 1
#                     completed_weight += w
#                 elif da.status == 'pending':
#                     pending_count    += 1
#                     pending_weight   += w
#                 elif da.status == 'in_progress':
#                     ongoing_count    += 1
#                     ongoing_weight   += w

#                 if dt.due_date and dt.due_date < today \
#                         and da.status not in ('completed', 'cancelled'):
#                     overdue_count  += 1
#                     overdue_weight += w

#         # 3. Temp Tasks
#         if HAS_TEMP:
#             my_tt = TemporaryTask.query.filter_by(assigned_to=uid, is_deleted=False).all()
#             for tt in my_tt:
#                 w = getattr(tt, 'weight', 3)
#                 total_count  += 1
#                 total_weight += w

#                 if tt.status == 'done':
#                     completed_count  += 1
#                     completed_weight += w
#                 elif tt.status == 'pending':
#                     pending_count    += 1
#                     pending_weight   += w
#                 elif tt.status == 'in-progress':
#                     ongoing_count    += 1
#                     ongoing_weight   += w

#                 if tt.due_date and tt.due_date < today \
#                         and tt.status not in ('done', 'cancelled'):
#                     overdue_count  += 1
#                     overdue_weight += w

#             result['temp_tasks_active'] = sum(
#                 1 for t in my_tt if t.status in ('pending', 'in-progress')
#             )
#         else:
#             result['temp_tasks_active'] = 0

#         # ── Populate result ─────────────────────────────────────────────
#         result.update({
#             # Legacy raw-count keys (backward compatible)
#             'tasks_total':          total_count,
#             'tasks_completed':      completed_count,
#             'tasks_pending':        pending_count,
#             'tasks_ongoing':        ongoing_count,
#             'tasks_overdue':        overdue_count,
#             'task_completion_rate': _pct(completed_count, total_count),

#             # New weighted keys
#             'weighted_total':       total_weight,
#             'weighted_completed':   completed_weight,
#             'weighted_pending':     pending_weight,
#             'weighted_ongoing':     ongoing_weight,
#             'weighted_overdue':     overdue_weight,
#             'weighted_completion_rate': _pct(completed_weight, total_weight),
#         })

#         return jsonify(result), 200

#     except Exception as e:
#         current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500






# v2
"""
Workforce — Dashboard Analytics API
=====================================
Register:
    from web.apis.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api')

Endpoints
─────────
GET /api/dashboard/overview      → headline KPI cards
GET /api/dashboard/attendance    → attendance trend (chart data)
GET /api/dashboard/projects      → project health & completion stats
GET /api/dashboard/tasks         → task status breakdown
GET /api/dashboard/leaderboard   → staff performance ranking (admin)
GET /api/dashboard/my-stats      → personal stats for current user

Task sources
────────────
Every "tasks" number in this file (overview, tasks_breakdown, leaderboard,
my_stats) is built from ONE helper — _unified_tasks_for_user() — which pulls
from all three task tables:
    1. Task              (project tasks)
    2. Assigned_Task + DailyTaskAssignee   (daily tasks, per-assignee status)
    3. TemporaryTask      (temp tasks)
This guarantees the KPI strip, the donut, the overdue list, the leaderboard
score, and "My Performance" can never disagree with each other again.
"""

import traceback
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, select

from web.models import db
from web import csrf
from web.models.projects import Assigned_Task, DailyTaskAssignee
from web.models.users import User
from web.utils.user_role import has_role

dashboard_bp = Blueprint('dashboard_api', __name__)

# ── Optional model imports (graceful if not present) ─────────────────────────
try:
    from web.models.attendance import Attendance
    HAS_ATTENDANCE = True
except ImportError:
    HAS_ATTENDANCE = False

try:
    from web.models.projects import (
        Project, ProjectMember, Task, TaskActivity,
        Assigned_Task, DailyTaskAssignee
    )
    HAS_PROJECTS = True
except ImportError:
    HAS_PROJECTS = False

try:
    from web.models.projects import TemporaryTask
    HAS_TEMP = True
except ImportError:
    HAS_TEMP = False


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _dn(user):
    if not user:
        return 'Unknown'
    return (user.name or '').strip() or user.username or str(user.id)


def _is_admin(user):
    return has_role(user, ['admin', 'md', 'hr', 'manager'])


def _date_range(days=30):
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start, end


def _pct(part, total):
    return round(part / total * 100, 1) if total else 0


def _unified_tasks_for_user(uid=None, admin_wide=False, _user_cache=None):
    """
    Single source of truth for "all tasks belonging to a person/org", merged
    across Project tasks, Daily tasks (per-assignee), and Temp tasks.

    Args:
        uid:         user id to filter to. Required unless admin_wide=True.
        admin_wide:  if True, returns tasks across ALL users (no uid filter).
                     Used by admin-scoped views (overview/tasks_breakdown
                     when the caller is an admin).
        _user_cache: optional dict {user_id: User} to avoid repeat lookups
                     when resolving assignees across many rows (used by
                     leaderboard/admin-wide calls). Pass {} to enable caching
                     across a loop; omit for one-off calls.

    Returns a flat list of normalized dicts:
        {
            id, source ('project'|'daily'|'temp'), description,
            status (normalized: pending / on-going / completed / cancelled),
            priority, weight, due_date (date or None), assigned_to (User or None)
        }
    """
    if not admin_wide and uid is None:
        return []

    out = []
    cache = _user_cache if _user_cache is not None else {}

    def _resolve_user(user_id):
        if user_id is None:
            return None
        if user_id in cache:
            return cache[user_id]
        u = User.query.get(user_id)
        cache[user_id] = u
        return u

    if not HAS_PROJECTS:
        # Project + Daily tasks both live under HAS_PROJECTS; if that's
        # unavailable there's nothing to pull from either source.
        pass
    else:
        # 1. Project tasks ----------------------------------------------------
        proj_q = Task.query.filter_by(deleted=False)
        if not admin_wide:
            proj_q = proj_q.filter(
                db.or_(Task.user_id == uid, Task.assigned_to_id == uid)
            )
        for t in proj_q.all():
            out.append({
                'id':          f"task-{t.id}",
                'source':      'project',
                'description': t.description,
                'status':      t.status,
                'priority':    getattr(t, 'priority', 'medium'),
                'weight':      getattr(t, 'weight', 3) or 3,
                'due_date':    t.due_date,
                'assigned_to': getattr(t, 'assigned_to', None),
            })

        # 2. Daily tasks (per-assignee status) --------------------------------
        daily_q = (
            db.session.query(DailyTaskAssignee, Assigned_Task)
            .join(Assigned_Task, DailyTaskAssignee.task_id == Assigned_Task.id)
            .filter(DailyTaskAssignee.deleted == False, Assigned_Task.deleted == False)
        )
        if not admin_wide:
            daily_q = daily_q.filter(DailyTaskAssignee.user_id == uid)

        for da, dt in daily_q.all():
            if da.status == 'completed':
                norm_status = 'completed'
            elif da.status == 'in_progress':
                norm_status = 'on-going'
            elif da.status in ('cancelled',):
                norm_status = 'cancelled'
            else:
                norm_status = 'pending'

            assignee = _resolve_user(da.user_id) if admin_wide else None

            out.append({
                'id':          f"daily-{dt.id}-{da.user_id}",
                'source':      'daily',
                'description': getattr(dt, 'title', None) or getattr(dt, 'description', '') or 'Daily task',
                'status':      norm_status,
                'priority':    getattr(dt, 'priority', 'medium'),
                'weight':      getattr(dt, 'weight', 3) or 3,
                'due_date':    getattr(dt, 'due_date', None),
                'assigned_to': assignee,
            })

    # 3. Temp tasks -------------------------------------------------------
    if HAS_TEMP:
        tt_q = TemporaryTask.query.filter_by(is_deleted=False)
        if not admin_wide:
            tt_q = tt_q.filter_by(assigned_to=uid)
        for tt in tt_q.all():
            if tt.status == 'done':
                norm_status = 'completed'
            elif tt.status == 'cancelled':
                norm_status = 'cancelled'
            elif tt.status == 'in-progress':
                norm_status = 'on-going'
            else:
                norm_status = 'pending'

            assignee = _resolve_user(getattr(tt, 'assigned_to', None)) if admin_wide else None

            out.append({
                'id':          f"temp-{tt.id}",
                'source':      'temp',
                'description': tt.description,
                'status':      norm_status,
                'priority':    getattr(tt, 'priority', 'medium'),
                'weight':      getattr(tt, 'weight', 3) or 3,
                'due_date':    getattr(tt, 'due_date', None),
                'assigned_to': assignee,
            })

    return out


def _task_counts(all_tasks, today=None):
    """Roll a unified task list up into raw + weighted counters."""
    today = today or date.today()

    total_count = completed_count = pending_count = ongoing_count = overdue_count = 0
    total_weight = completed_weight = pending_weight = ongoing_weight = overdue_weight = 0

    for t in all_tasks:
        w = t['weight'] or 3
        total_count += 1
        total_weight += w

        if t['status'] == 'completed':
            completed_count += 1
            completed_weight += w
        elif t['status'] == 'pending':
            pending_count += 1
            pending_weight += w
        elif t['status'] == 'on-going':
            ongoing_count += 1
            ongoing_weight += w
        # 'cancelled' intentionally excluded from pending/ongoing/completed buckets

        if t['due_date'] and t['due_date'] < today and t['status'] not in ('completed', 'cancelled'):
            overdue_count += 1
            overdue_weight += w

    return {
        'tasks_total':     total_count,
        'tasks_completed': completed_count,
        'tasks_pending':   pending_count,
        'tasks_ongoing':   ongoing_count,
        'tasks_overdue':   overdue_count,
        'task_completion_rate': _pct(completed_count, total_count),

        'weighted_total':       total_weight,
        'weighted_completed':   completed_weight,
        'weighted_pending':     pending_weight,
        'weighted_ongoing':     ongoing_weight,
        'weighted_overdue':     overdue_weight,
        'weighted_completion_rate': _pct(completed_weight, total_weight),
    }


# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW CARDS
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/overview', methods=['GET'])
@login_required
@csrf.exempt
def overview():
    """
    Headline KPI cards.
    Admin: org-wide.   Staff: personal.
    """
    try:
        today    = date.today()
        wk_start = today - timedelta(days=6)
        is_admin = _is_admin(current_user)

        result = {}

        # ── Attendance ────────────────────────────────────────────────────
        if HAS_ATTENDANCE:
            att_q = Attendance.query.join(User)
            if not is_admin:
                att_q = att_q.filter(Attendance.user_id == current_user.id)

            today_att = att_q.filter(func.date(Attendance.created) == today).count()
            week_att  = att_q.filter(func.date(Attendance.created) >= wk_start).count()
            total_att = att_q.count()

            result['attendance_today'] = today_att
            result['attendance_week']  = week_att
            result['attendance_total'] = total_att
        else:
            result.update({'attendance_today': 0, 'attendance_week': 0, 'attendance_total': 0})

        # ── Projects ──────────────────────────────────────────────────────
        if HAS_PROJECTS:
            if is_admin:
                proj_q = Project.query.filter_by(deleted=False)
            else:
                member_subq = select(ProjectMember.project_id).where(
                    ProjectMember.user_id == current_user.id
                )
                proj_q = Project.query.filter(
                    Project.deleted == False,
                    Project.id.in_(member_subq)
                )

            total_proj     = proj_q.count()
            active_proj    = proj_q.filter_by(status='active').count()
            completed_proj = proj_q.filter_by(status='completed').count()

            result['projects_total']     = total_proj
            result['projects_active']    = active_proj
            result['projects_completed'] = completed_proj
        else:
            result.update({'projects_total': 0, 'projects_active': 0, 'projects_completed': 0})

        # ── Tasks (unified across project / daily / temp) ───────────────────
        all_tasks = _unified_tasks_for_user(uid=current_user.id, admin_wide=is_admin)
        result.update(_task_counts(all_tasks, today=today))
        # overview() historically only exposed raw counts (not weighted_*).
        # Weighted keys are included above too now — harmless additions,
        # existing template code that only reads tasks_* still works as-is.

        # ── Temp tasks (separate "currently active" KPI — independent metric) ──
        if HAS_TEMP:
            tt_q = TemporaryTask.query.filter_by(is_deleted=False)
            if not is_admin:
                tt_q = tt_q.filter_by(assigned_to=current_user.id)
            result['temp_tasks_active'] = tt_q.filter(
                TemporaryTask.status.in_(['pending', 'in-progress'])
            ).count()
        else:
            result['temp_tasks_active'] = 0

        # ── Staff count (admin only) ───────────────────────────────────────
        if is_admin:
            result['total_staff'] = User.query.filter_by(deleted=False).count()

        result['is_admin'] = is_admin

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE TREND  (daily bar chart)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/attendance', methods=['GET'])
@login_required
@csrf.exempt
def attendance_trend():
    try:
        days = request.args.get('days', 30, type=int)
        d_from, d_to = _date_range(days)
        is_admin = _is_admin(current_user)

        if not HAS_ATTENDANCE:
            return jsonify({'series': [], 'total': 0}), 200

        q = (
            Attendance.query
            .join(User)
            .filter(
                User.deleted == False,
                func.date(Attendance.created) >= d_from,
                func.date(Attendance.created) <= d_to,
            )
        )
        if not is_admin:
            q = q.filter(Attendance.user_id == current_user.id)

        records = q.order_by(Attendance.created).all()

        day_map = {}
        for i in range(days):
            d = (d_from + timedelta(days=i)).strftime('%Y-%m-%d')
            day_map[d] = 0
        for a in records:
            if a.created:
                key = a.created.strftime('%Y-%m-%d')
                if key in day_map:
                    day_map[key] += 1

        series = [{'date': k, 'label': k[5:], 'count': v} for k, v in sorted(day_map.items())]

        non_zero = [s['count'] for s in series if s['count'] > 0]
        avg = round(sum(non_zero) / len(non_zero), 1) if non_zero else 0

        return jsonify({'series': series, 'total': len(records), 'average': avg, 'days': days}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/projects', methods=['GET'])
@login_required
@csrf.exempt
def projects_health():
    try:
        if not HAS_PROJECTS:
            return jsonify({'by_status': [], 'by_priority': [], 'projects': [], 'total': 0}), 200

        is_admin = _is_admin(current_user)

        if is_admin:
            proj_q = Project.query.filter_by(deleted=False)
        else:
            member_subq = select(ProjectMember.project_id).where(
                ProjectMember.user_id == current_user.id
            )
            proj_q = Project.query.filter(
                Project.deleted == False,
                Project.id.in_(member_subq)
            )

        projects = proj_q.all()

        status_map = {}
        for p in projects:
            status_map[p.status] = status_map.get(p.status, 0) + 1
        by_status = [{'status': k, 'count': v} for k, v in status_map.items()]

        pri_map = {}
        for p in projects:
            pri = getattr(p, 'priority', 'medium')
            pri_map[pri] = pri_map.get(pri, 0) + 1
        by_priority = [{'priority': k, 'count': v} for k, v in pri_map.items()]

        completion_data = []
        for p in projects:
            tc = getattr(p, 'task_count', 0) or 0
            cc = getattr(p, 'completed_count', 0) or 0
            completion_data.append({
                'id':       p.id,
                'title':    p.title,
                'color':    getattr(p, 'color', '#2563eb'),
                'status':   p.status,
                'priority': getattr(p, 'priority', 'medium'),
                'progress': _pct(cc, tc),
                'task_count':      tc,
                'completed_count': cc,
                'due_date':        p.due_date.isoformat() if p.due_date else None,
            })
        completion_data.sort(key=lambda x: x['progress'])

        return jsonify({
            'by_status':   by_status,
            'by_priority': by_priority,
            'projects':    completion_data,
            'total':       len(projects),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TASK BREAKDOWN  (unified across project / daily / temp)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/tasks', methods=['GET'])
@login_required
@csrf.exempt
def tasks_breakdown():
    try:
        today    = date.today()
        is_admin = _is_admin(current_user)

        all_tasks = _unified_tasks_for_user(uid=current_user.id, admin_wide=is_admin)

        if not all_tasks:
            return jsonify({
                'by_status': [], 'by_priority': [],
                'overdue': [], 'overdue_count': 0, 'total': 0,
            }), 200

        status_map, pri_map = {}, {}
        for t in all_tasks:
            status_map[t['status']] = status_map.get(t['status'], 0) + 1
            pri_map[t['priority']] = pri_map.get(t['priority'], 0) + 1

        by_status   = [{'status': k, 'count': v} for k, v in status_map.items()]
        by_priority = [{'priority': k, 'count': v} for k, v in pri_map.items()]

        overdue = [
            t for t in all_tasks
            if t['due_date'] and t['due_date'] < today and t['status'] not in ('completed', 'cancelled')
        ]
        overdue.sort(key=lambda x: x['due_date'])

        overdue_list = [{
            'id':          t['id'],
            'description': t['description'],
            'due_date':    t['due_date'].isoformat() if t['due_date'] else None,
            'priority':    t['priority'],
            'weight':      t['weight'],
            'source':      t['source'],   # 'project' | 'daily' | 'temp'
            'assigned_to': {'id': t['assigned_to'].id, 'name': _dn(t['assigned_to'])} if t['assigned_to'] else None,
        } for t in overdue]

        return jsonify({
            'by_status':     by_status,
            'by_priority':   by_priority,
            'overdue':       overdue_list[:10],
            'overdue_count': len(overdue),
            'total':         len(all_tasks),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# LEADERBOARD  (admin only — who's doing the most)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/leaderboard', methods=['GET'])
@login_required
@csrf.exempt
def leaderboard():
    """
    Staff performance leaderboard for admin/manager.
    Score = 2pts/attendance day + 5pts per weight-unit completed
            - 3pts per weight-unit overdue + 1pt per project membership.
    Uses the same unified task list as overview/tasks_breakdown/my_stats,
    so a user's leaderboard "tasks done" always matches their own
    My Performance panel.
    """
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        d_from, d_to = _date_range(days)
        today = date.today()

        users = User.query.filter_by(deleted=False).all()

        # Pull ALL tasks once (admin_wide=True), then bucket per-user in
        # Python — avoids N+1 queries across the whole staff list.
        user_cache = {u.id: u for u in users}
        all_tasks_admin_wide = _unified_tasks_for_user(admin_wide=True, _user_cache=user_cache)

        tasks_by_user = {}
        for t in all_tasks_admin_wide:
            uid = t['assigned_to'].id if t['assigned_to'] else None
            if uid is None:
                continue
            tasks_by_user.setdefault(uid, []).append(t)

        # Project-source tasks use Task.user_id / Task.assigned_to_id, and
        # _unified_tasks_for_user only attaches `assigned_to` from the Task
        # relationship (assigned_to_id). Tasks created-by-but-not-assigned-to
        # a user (Task.user_id) also need to count for that user's score —
        # match the original scoring behaviour by re-querying those directly.
        project_task_ids_by_user = {}
        if HAS_PROJECTS:
            for t in Task.query.filter(Task.deleted == False).all():
                for uid in {t.user_id, t.assigned_to_id}:
                    if uid:
                        project_task_ids_by_user.setdefault(uid, set()).add(t.id)

        board = []
        for u in users:
            score = 0
            att_days = 0

            # Attendance
            if HAS_ATTENDANCE:
                att_days = (
                    Attendance.query
                    .filter_by(user_id=u.id)
                    .filter(func.date(Attendance.created) >= d_from)
                    .count()
                )
                score += att_days * 2  # 2pts per attendance day

            # Unified tasks for this user (daily + temp always keyed by
            # assignee; project tasks need the extra owner-or-assignee merge
            # done above since Task.user_id ≠ Task.assigned_to_id can differ)
            user_tasks = list(tasks_by_user.get(u.id, []))

            if HAS_PROJECTS and u.id in project_task_ids_by_user:
                already_have = {t['id'] for t in user_tasks if t['source'] == 'project'}
                extra_ids = project_task_ids_by_user[u.id] - {
                    int(tid.split('-')[1]) for tid in already_have
                }
                if extra_ids:
                    for t in Task.query.filter(Task.id.in_(extra_ids)).all():
                        user_tasks.append({
                            'id': f"task-{t.id}", 'source': 'project',
                            'description': t.description, 'status': t.status,
                            'priority': getattr(t, 'priority', 'medium'),
                            'weight': getattr(t, 'weight', 3) or 3,
                            'due_date': t.due_date, 'assigned_to': None,
                        })

            counts = _task_counts(user_tasks, today=today)

            score += counts['weighted_completed'] * 5   # 5 pts per weight unit completed
            score -= counts['weighted_overdue'] * 3      # -3 pts per weight unit overdue

            # Project memberships
            projects_count = ProjectMember.query.filter_by(user_id=u.id).count() if HAS_PROJECTS else 0
            score += projects_count  # 1pt per project

            board.append({
                'user_id':          u.id,
                'name':             _dn(u),
                'photo':            u.photo,
                'username':         u.username,
                'system_roles':     u.my_roles,
                'att_days':         att_days,
                'tasks_done':       counts['tasks_completed'],
                'tasks_total':      counts['tasks_total'],
                'tasks_overdue':    counts['tasks_overdue'],
                'weighted_done':    counts['weighted_completed'],
                'weighted_total':   counts['weighted_total'],
                'weighted_overdue': counts['weighted_overdue'],
                'projects':         projects_count,
                'completion_rate':  counts['task_completion_rate'],
                'score':            max(score, 0),
            })

        board.sort(key=lambda x: x['score'], reverse=True)

        labels = ['Top Performer', 'High Performer', 'On Track', 'Needs Attention', 'At Risk']
        n = len(board)
        for i, b in enumerate(board):
            b['rank'] = i + 1
            if n <= 1:
                b['label'] = 'Top Performer'
            else:
                idx = min(int(i / n * len(labels)), len(labels) - 1)
                b['label'] = labels[idx]

        return jsonify({
            'leaderboard': board,
            'days':        days,
            'date_from':   str(d_from),
            'date_to':     str(d_to),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# MY STATS  (personal dashboard for non-admin users)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/my-stats', methods=['GET'])
@login_required
@csrf.exempt
def my_stats():
    try:
        days = request.args.get('days', 30, type=int)
        d_from, d_to = _date_range(days)
        today = date.today()
        uid = current_user.id

        result = {'user_id': uid, 'days': days}

        # ── Attendance ────────────────────────────────────────────────────
        if HAS_ATTENDANCE:
            my_att = (
                Attendance.query
                .filter_by(user_id=uid)
                .filter(func.date(Attendance.created) >= d_from)
                .all()
            )
            result['att_days'] = len(my_att)
            result['att_rate'] = _pct(len(my_att), days)

            wk_map = {}
            for i in range(7):
                d = (today - timedelta(days=6 - i)).strftime('%Y-%m-%d')
                wk_map[d] = 0
            for a in Attendance.query.filter_by(user_id=uid) \
                    .filter(func.date(Attendance.created) >= today - timedelta(days=6)).all():
                if a.created:
                    key = a.created.strftime('%Y-%m-%d')
                    if key in wk_map:
                        wk_map[key] += 1
            result['att_week'] = [{'date': k, 'day': k[5:], 'present': v > 0}
                                   for k, v in sorted(wk_map.items())]
        else:
            result.update({'att_days': 0, 'att_rate': 0, 'att_week': []})

        # ── Unified tasks (project + daily + temp) ──────────────────────────
        all_tasks = _unified_tasks_for_user(uid=uid, admin_wide=False)
        result.update(_task_counts(all_tasks, today=today))

        result['project_count'] = ProjectMember.query.filter_by(user_id=uid).count() if HAS_PROJECTS else 0

        # ── Temp tasks (separate "currently active" KPI — independent metric) ──
        if HAS_TEMP:
            my_tt = TemporaryTask.query.filter_by(assigned_to=uid, is_deleted=False).all()
            result['temp_tasks_active'] = sum(1 for t in my_tt if t.status in ('pending', 'in-progress'))
        else:
            result['temp_tasks_active'] = 0

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
"""
Workforce — Dashboard Analytics API
=====================================
Register:
    from web.apis.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api')

Endpoints
─────────
GET /api/dashboard/overview      → headline KPI cards
GET /api/dashboard/attendance    → attendance trend (chart data)
GET /api/dashboard/projects      → project health & completion stats
GET /api/dashboard/tasks         → task status breakdown
GET /api/dashboard/leaderboard   → staff performance ranking (admin)
GET /api/dashboard/my-stats      → personal stats for current user

Task sources
────────────
Every "tasks" number in this file (overview, tasks_breakdown, leaderboard,
my_stats) is built from ONE helper — _unified_tasks_for_user() — which pulls
from all three task tables:
    1. Task              (project tasks)
    2. Assigned_Task + DailyTaskAssignee   (daily tasks, per-assignee status)
    3. TemporaryTask      (temp tasks)
This guarantees the KPI strip, the donut, the overdue list, the leaderboard
score, and "My Performance" can never disagree with each other again.

"""

import traceback
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, select

from web.models import db
from web import csrf
from web.models.projects import Assigned_Task, DailyTaskAssignee
from web.models.users import User
from web.utils.user_role import has_role

dashboard_bp = Blueprint('dashboard_api', __name__)

# ── Optional model imports (graceful if not present) ─────────────────────────
try:
    from web.models.attendance import Attendance
    HAS_ATTENDANCE = True
except ImportError:
    HAS_ATTENDANCE = False

try:
    from web.models.projects import (
        Project, ProjectMember, Task, TaskActivity,
        Assigned_Task, DailyTaskAssignee
    )
    HAS_PROJECTS = True
except ImportError:
    HAS_PROJECTS = False

try:
    from web.models.projects import TemporaryTask
    HAS_TEMP = True
except ImportError:
    HAS_TEMP = False


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _dn(user):
    if not user:
        return 'Unknown'
    return (user.name or '').strip() or user.username or str(user.id)


def _is_admin(user):
    return has_role(user, ['admin', 'md', 'hr', 'manager'])


def _date_range(days=30):
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start, end


def _pct(part, total):
    return round(part / total * 100, 1) if total else 0


def _unified_tasks_for_user(uid=None, admin_wide=False, _user_cache=None):
    """
    Single source of truth for "all tasks belonging to a person/org", merged
    across Project tasks, Daily tasks (per-assignee), and Temp tasks.

    Args:
        uid:         user id to filter to. Required unless admin_wide=True.
        admin_wide:  if True, returns tasks across ALL users (no uid filter).
                     Used by admin-scoped views (overview/tasks_breakdown
                     when the caller is an admin).
        _user_cache: optional dict {user_id: User} to avoid repeat lookups
                     when resolving assignees across many rows (used by
                     leaderboard/admin-wide calls). Pass {} to enable caching
                     across a loop; omit for one-off calls.

    Returns a flat list of normalized dicts:
        {
            id, source ('project'|'daily'|'temp'), description,
            status (normalized: pending / on-going / completed / cancelled),
            priority, weight, due_date (date or None), assigned_to (User or None)
        }
    """
    if not admin_wide and uid is None:
        return []

    out = []
    cache = _user_cache if _user_cache is not None else {}

    def _resolve_user(user_id):
        if user_id is None:
            return None
        if user_id in cache:
            return cache[user_id]
        u = User.query.get(user_id)
        cache[user_id] = u
        return u

    if not HAS_PROJECTS:
        # Project + Daily tasks both live under HAS_PROJECTS; if that's
        # unavailable there's nothing to pull from either source.
        pass
    else:
        # 1. Project tasks ----------------------------------------------------
        proj_q = Task.query.filter_by(deleted=False)
        if not admin_wide:
            proj_q = proj_q.filter(
                db.or_(Task.user_id == uid, Task.assigned_to_id == uid)
            )
        for t in proj_q.all():
            out.append({
                'id':          f"task-{t.id}",
                'source':      'project',
                'description': t.description,
                'status':      t.status,
                'priority':    getattr(t, 'priority', 'medium'),
                'weight':      getattr(t, 'weight', 3) or 3,
                'due_date':    t.due_date,
                'assigned_to': getattr(t, 'assigned_to', None),
            })

        # 2. Daily tasks (per-assignee status) --------------------------------
        daily_q = (
            db.session.query(DailyTaskAssignee, Assigned_Task)
            .join(Assigned_Task, DailyTaskAssignee.task_id == Assigned_Task.id)
            .filter(DailyTaskAssignee.deleted == False, Assigned_Task.deleted == False)
        )
        if not admin_wide:
            daily_q = daily_q.filter(DailyTaskAssignee.user_id == uid)

        for da, dt in daily_q.all():
            if da.status == 'completed':
                norm_status = 'completed'
            elif da.status == 'in_progress':
                norm_status = 'on-going'
            elif da.status in ('cancelled',):
                norm_status = 'cancelled'
            else:
                norm_status = 'pending'

            assignee = _resolve_user(da.user_id) if admin_wide else None

            out.append({
                'id':          f"daily-{dt.id}-{da.user_id}",
                'source':      'daily',
                'description': getattr(dt, 'title', None) or getattr(dt, 'description', '') or 'Daily task',
                'status':      norm_status,
                'priority':    getattr(dt, 'priority', 'medium'),
                'weight':      getattr(dt, 'weight', 3) or 3,
                'due_date':    getattr(dt, 'due_date', None),
                'assigned_to': assignee,
            })

    # 3. Temp tasks -------------------------------------------------------
    if HAS_TEMP:
        tt_q = TemporaryTask.query.filter_by(is_deleted=False)
        if not admin_wide:
            tt_q = tt_q.filter_by(assigned_to=uid)
        for tt in tt_q.all():
            if tt.status == 'done':
                norm_status = 'completed'
            elif tt.status == 'cancelled':
                norm_status = 'cancelled'
            elif tt.status == 'in-progress':
                norm_status = 'on-going'
            else:
                norm_status = 'pending'

            assignee = _resolve_user(getattr(tt, 'assigned_to', None)) if admin_wide else None

            out.append({
                'id':          f"temp-{tt.id}",
                'source':      'temp',
                'description': tt.detail,
                'status':      norm_status,
                'priority':    getattr(tt, 'priority', 'medium'),
                'weight':      getattr(tt, 'weight', 3) or 3,
                'due_date':    getattr(tt, 'due_date', None),
                'assigned_to': assignee,
            })

    return out


def _task_counts(all_tasks, today=None):
    """Roll a unified task list up into raw + weighted counters."""
    today = today or date.today()

    total_count = completed_count = pending_count = ongoing_count = overdue_count = 0
    total_weight = completed_weight = pending_weight = ongoing_weight = overdue_weight = 0

    for t in all_tasks:
        w = t['weight'] or 3
        total_count += 1
        total_weight += w

        if t['status'] == 'completed':
            completed_count += 1
            completed_weight += w
        elif t['status'] == 'pending':
            pending_count += 1
            pending_weight += w
        elif t['status'] == 'on-going':
            ongoing_count += 1
            ongoing_weight += w
        # 'cancelled' intentionally excluded from pending/ongoing/completed buckets

        if t['due_date'] and t['due_date'] < today and t['status'] not in ('completed', 'cancelled'):
            overdue_count += 1
            overdue_weight += w

    return {
        'tasks_total':     total_count,
        'tasks_completed': completed_count,
        'tasks_pending':   pending_count,
        'tasks_ongoing':   ongoing_count,
        'tasks_overdue':   overdue_count,
        'task_completion_rate': _pct(completed_count, total_count),

        'weighted_total':       total_weight,
        'weighted_completed':   completed_weight,
        'weighted_pending':     pending_weight,
        'weighted_ongoing':     ongoing_weight,
        'weighted_overdue':     overdue_weight,
        'weighted_completion_rate': _pct(completed_weight, total_weight),
    }


# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW CARDS
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/overview', methods=['GET'])
@login_required
@csrf.exempt
def overview():
    """
    Headline KPI cards.
    Admin: org-wide.   Staff: personal.
    """
    try:
        today    = date.today()
        wk_start = today - timedelta(days=6)
        is_admin = _is_admin(current_user)

        result = {}

        # ── Attendance ────────────────────────────────────────────────────
        if HAS_ATTENDANCE:
            att_q = Attendance.query.join(User)
            if not is_admin:
                att_q = att_q.filter(Attendance.user_id == current_user.id)

            today_att = att_q.filter(func.date(Attendance.created) == today).count()
            week_att  = att_q.filter(func.date(Attendance.created) >= wk_start).count()
            total_att = att_q.count()

            result['attendance_today'] = today_att
            result['attendance_week']  = week_att
            result['attendance_total'] = total_att
        else:
            result.update({'attendance_today': 0, 'attendance_week': 0, 'attendance_total': 0})

        # ── Projects ──────────────────────────────────────────────────────
        if HAS_PROJECTS:
            if is_admin:
                proj_q = Project.query.filter_by(deleted=False)
            else:
                member_subq = select(ProjectMember.project_id).where(
                    ProjectMember.user_id == current_user.id
                )
                proj_q = Project.query.filter(
                    Project.deleted == False,
                    Project.id.in_(member_subq)
                )

            total_proj     = proj_q.count()
            active_proj    = proj_q.filter_by(status='active').count()
            completed_proj = proj_q.filter_by(status='completed').count()

            result['projects_total']     = total_proj
            result['projects_active']    = active_proj
            result['projects_completed'] = completed_proj
        else:
            result.update({'projects_total': 0, 'projects_active': 0, 'projects_completed': 0})

        # ── Tasks (unified across project / daily / temp) ───────────────────
        all_tasks = _unified_tasks_for_user(uid=current_user.id, admin_wide=is_admin)
        result.update(_task_counts(all_tasks, today=today))
        # overview() historically only exposed raw counts (not weighted_*).
        # Weighted keys are included above too now — harmless additions,
        # existing template code that only reads tasks_* still works as-is.

        # ── Temp tasks (separate "currently active" KPI — independent metric) ──
        if HAS_TEMP:
            tt_q = TemporaryTask.query.filter_by(is_deleted=False)
            if not is_admin:
                tt_q = tt_q.filter_by(assigned_to=current_user.id)
            result['temp_tasks_active'] = tt_q.filter(
                TemporaryTask.status.in_(['pending', 'in-progress'])
            ).count()
        else:
            result['temp_tasks_active'] = 0

        # ── Staff count (admin only) ───────────────────────────────────────
        if is_admin:
            result['total_staff'] = User.query.filter_by(deleted=False).count()

        result['is_admin'] = is_admin

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE TREND  (daily bar chart)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/attendance', methods=['GET'])
@login_required
@csrf.exempt
def attendance_trend():
    try:
        days = request.args.get('days', 30, type=int)
        d_from, d_to = _date_range(days)
        is_admin = _is_admin(current_user)

        if not HAS_ATTENDANCE:
            return jsonify({'series': [], 'total': 0}), 200

        q = (
            Attendance.query
            .join(User)
            .filter(
                User.deleted == False,
                func.date(Attendance.created) >= d_from,
                func.date(Attendance.created) <= d_to,
            )
        )
        if not is_admin:
            q = q.filter(Attendance.user_id == current_user.id)

        records = q.order_by(Attendance.created).all()

        day_map = {}
        for i in range(days):
            d = (d_from + timedelta(days=i)).strftime('%Y-%m-%d')
            day_map[d] = 0
        for a in records:
            if a.created:
                key = a.created.strftime('%Y-%m-%d')
                if key in day_map:
                    day_map[key] += 1

        series = [{'date': k, 'label': k[5:], 'count': v} for k, v in sorted(day_map.items())]

        non_zero = [s['count'] for s in series if s['count'] > 0]
        avg = round(sum(non_zero) / len(non_zero), 1) if non_zero else 0

        return jsonify({'series': series, 'total': len(records), 'average': avg, 'days': days}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/projects', methods=['GET'])
@login_required
@csrf.exempt
def projects_health():
    try:
        if not HAS_PROJECTS:
            return jsonify({'by_status': [], 'by_priority': [], 'projects': [], 'total': 0}), 200

        is_admin = _is_admin(current_user)

        if is_admin:
            proj_q = Project.query.filter_by(deleted=False)
        else:
            member_subq = select(ProjectMember.project_id).where(
                ProjectMember.user_id == current_user.id
            )
            proj_q = Project.query.filter(
                Project.deleted == False,
                Project.id.in_(member_subq)
            )

        projects = proj_q.all()

        status_map = {}
        for p in projects:
            status_map[p.status] = status_map.get(p.status, 0) + 1
        by_status = [{'status': k, 'count': v} for k, v in status_map.items()]

        pri_map = {}
        for p in projects:
            pri = getattr(p, 'priority', 'medium')
            pri_map[pri] = pri_map.get(pri, 0) + 1
        by_priority = [{'priority': k, 'count': v} for k, v in pri_map.items()]

        completion_data = []
        for p in projects:
            tc = getattr(p, 'task_count', 0) or 0
            cc = getattr(p, 'completed_count', 0) or 0
            completion_data.append({
                'id':       p.id,
                'title':    p.title,
                'color':    getattr(p, 'color', '#2563eb'),
                'status':   p.status,
                'priority': getattr(p, 'priority', 'medium'),
                'progress': _pct(cc, tc),
                'task_count':      tc,
                'completed_count': cc,
                'due_date':        p.due_date.isoformat() if p.due_date else None,
            })
        completion_data.sort(key=lambda x: x['progress'])

        return jsonify({
            'by_status':   by_status,
            'by_priority': by_priority,
            'projects':    completion_data,
            'total':       len(projects),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# TASK BREAKDOWN  (unified across project / daily / temp)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/tasks', methods=['GET'])
@login_required
@csrf.exempt
def tasks_breakdown():
    try:
        today    = date.today()
        is_admin = _is_admin(current_user)

        all_tasks = _unified_tasks_for_user(uid=current_user.id, admin_wide=is_admin)

        if not all_tasks:
            return jsonify({
                'by_status': [], 'by_priority': [],
                'overdue': [], 'overdue_count': 0, 'total': 0,
            }), 200

        status_map, pri_map = {}, {}
        for t in all_tasks:
            status_map[t['status']] = status_map.get(t['status'], 0) + 1
            pri_map[t['priority']] = pri_map.get(t['priority'], 0) + 1

        by_status   = [{'status': k, 'count': v} for k, v in status_map.items()]
        by_priority = [{'priority': k, 'count': v} for k, v in pri_map.items()]

        overdue = [
            t for t in all_tasks
            if t['due_date'] and t['due_date'] < today and t['status'] not in ('completed', 'cancelled')
        ]
        overdue.sort(key=lambda x: x['due_date'])

        overdue_list = [{
            'id':          t['id'],
            'description': t['description'],
            'due_date':    t['due_date'].isoformat() if t['due_date'] else None,
            'priority':    t['priority'],
            'weight':      t['weight'],
            'source':      t['source'],   # 'project' | 'daily' | 'temp'
            'assigned_to': {'id': t['assigned_to'].id, 'name': _dn(t['assigned_to'])} if t['assigned_to'] else None,
        } for t in overdue]

        return jsonify({
            'by_status':     by_status,
            'by_priority':   by_priority,
            'overdue':       overdue_list[:10],
            'overdue_count': len(overdue),
            'total':         len(all_tasks),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# LEADERBOARD  (admin only — who's doing the most)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/leaderboard', methods=['GET'])
@login_required
@csrf.exempt
def leaderboard():
    """
    Staff performance leaderboard for admin/manager.
    Score = 2pts/attendance day + 5pts per weight-unit completed
            - 3pts per weight-unit overdue + 1pt per project membership.
    Uses the same unified task list as overview/tasks_breakdown/my_stats,
    so a user's leaderboard "tasks done" always matches their own
    My Performance panel.
    """
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        d_from, d_to = _date_range(days)
        today = date.today()

        users = User.query.filter_by(deleted=False).all()

        # Pull ALL tasks once (admin_wide=True), then bucket per-user in
        # Python — avoids N+1 queries across the whole staff list.
        user_cache = {u.id: u for u in users}
        all_tasks_admin_wide = _unified_tasks_for_user(admin_wide=True, _user_cache=user_cache)

        tasks_by_user = {}
        for t in all_tasks_admin_wide:
            uid = t['assigned_to'].id if t['assigned_to'] else None
            if uid is None:
                continue
            tasks_by_user.setdefault(uid, []).append(t)

        # Project-source tasks use Task.user_id / Task.assigned_to_id, and
        # _unified_tasks_for_user only attaches `assigned_to` from the Task
        # relationship (assigned_to_id). Tasks created-by-but-not-assigned-to
        # a user (Task.user_id) also need to count for that user's score —
        # match the original scoring behaviour by re-querying those directly.
        project_task_ids_by_user = {}
        if HAS_PROJECTS:
            for t in Task.query.filter(Task.deleted == False).all():
                for uid in {t.user_id, t.assigned_to_id}:
                    if uid:
                        project_task_ids_by_user.setdefault(uid, set()).add(t.id)

        board = []
        for u in users:
            score = 0
            att_days = 0

            # Attendance
            if HAS_ATTENDANCE:
                att_days = (
                    Attendance.query
                    .filter_by(user_id=u.id)
                    .filter(func.date(Attendance.created) >= d_from)
                    .count()
                )
                score += att_days * 2  # 2pts per attendance day

            # Unified tasks for this user (daily + temp always keyed by
            # assignee; project tasks need the extra owner-or-assignee merge
            # done above since Task.user_id ≠ Task.assigned_to_id can differ)
            user_tasks = list(tasks_by_user.get(u.id, []))

            if HAS_PROJECTS and u.id in project_task_ids_by_user:
                already_have = {t['id'] for t in user_tasks if t['source'] == 'project'}
                extra_ids = project_task_ids_by_user[u.id] - {
                    int(tid.split('-')[1]) for tid in already_have
                }
                if extra_ids:
                    for t in Task.query.filter(Task.id.in_(extra_ids)).all():
                        user_tasks.append({
                            'id': f"task-{t.id}", 'source': 'project',
                            'description': t.description, 'status': t.status,
                            'priority': getattr(t, 'priority', 'medium'),
                            'weight': getattr(t, 'weight', 3) or 3,
                            'due_date': t.due_date, 'assigned_to': None,
                        })

            counts = _task_counts(user_tasks, today=today)

            score += counts['weighted_completed'] * 5   # 5 pts per weight unit completed
            score -= counts['weighted_overdue'] * 3      # -3 pts per weight unit overdue

            # Project memberships
            projects_count = ProjectMember.query.filter_by(user_id=u.id).count() if HAS_PROJECTS else 0
            score += projects_count  # 1pt per project

            board.append({
                'user_id':          u.id,
                'name':             _dn(u),
                'photo':            u.photo,
                'username':         u.username,
                'system_roles':     u.my_roles,
                'att_days':         att_days,
                'tasks_done':       counts['tasks_completed'],
                'tasks_total':      counts['tasks_total'],
                'tasks_overdue':    counts['tasks_overdue'],
                'weighted_done':    counts['weighted_completed'],
                'weighted_total':   counts['weighted_total'],
                'weighted_overdue': counts['weighted_overdue'],
                'projects':         projects_count,
                'completion_rate':  counts['task_completion_rate'],
                'score':            max(score, 0),
            })

        board.sort(key=lambda x: x['score'], reverse=True)

        labels = ['Top Performer', 'High Performer', 'On Track', 'Needs Attention', 'At Risk']
        n = len(board)
        for i, b in enumerate(board):
            b['rank'] = i + 1
            if n <= 1:
                b['label'] = 'Top Performer'
            else:
                idx = min(int(i / n * len(labels)), len(labels) - 1)
                b['label'] = labels[idx]

        return jsonify({
            'leaderboard': board,
            'days':        days,
            'date_from':   str(d_from),
            'date_to':     str(d_to),
        }), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# MY STATS  (personal dashboard for non-admin users)
# ─────────────────────────────────────────────────────────────────────────────

@dashboard_bp.route('/dashboard/my-stats', methods=['GET'])
@login_required
@csrf.exempt
def my_stats():
    try:
        days = request.args.get('days', 30, type=int)
        d_from, d_to = _date_range(days)
        today = date.today()
        uid = current_user.id

        result = {'user_id': uid, 'days': days}

        # ── Attendance ────────────────────────────────────────────────────
        if HAS_ATTENDANCE:
            my_att = (
                Attendance.query
                .filter_by(user_id=uid)
                .filter(func.date(Attendance.created) >= d_from)
                .all()
            )
            result['att_days'] = len(my_att)
            result['att_rate'] = _pct(len(my_att), days)

            wk_map = {}
            for i in range(7):
                d = (today - timedelta(days=6 - i)).strftime('%Y-%m-%d')
                wk_map[d] = 0
            for a in Attendance.query.filter_by(user_id=uid) \
                    .filter(func.date(Attendance.created) >= today - timedelta(days=6)).all():
                if a.created:
                    key = a.created.strftime('%Y-%m-%d')
                    if key in wk_map:
                        wk_map[key] += 1
            result['att_week'] = [{'date': k, 'day': k[5:], 'present': v > 0}
                                   for k, v in sorted(wk_map.items())]
        else:
            result.update({'att_days': 0, 'att_rate': 0, 'att_week': []})

        # ── Unified tasks (project + daily + temp) ──────────────────────────
        all_tasks = _unified_tasks_for_user(uid=uid, admin_wide=False)
        result.update(_task_counts(all_tasks, today=today))

        result['project_count'] = ProjectMember.query.filter_by(user_id=uid).count() if HAS_PROJECTS else 0

        # ── Temp tasks (separate "currently active" KPI — independent metric) ──
        if HAS_TEMP:
            my_tt = TemporaryTask.query.filter_by(assigned_to=uid, is_deleted=False).all()
            result['temp_tasks_active'] = sum(1 for t in my_tt if t.status in ('pending', 'in-progress'))
        else:
            result['temp_tasks_active'] = 0

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/dashboard_api.py: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
