from web.models.projects import Assigned_Task, DailyTaskAssignee, Task, TemporaryTask
from web.models import db

def _unified_tasks_for_user(uid, is_admin):
    """
    Flat list of normalized task dicts across Project / Daily / Temp tasks.
    Single source of truth so overview, tasks_breakdown, and my_stats
    never disagree again.
    status normalized to: pending / on-going / completed / cancelled
    """
    today = date.today()
    out = []

    if HAS_PROJECTS:
        q = Task.query.filter_by(deleted=False)
        if not is_admin:
            q = q.filter(db.or_(Task.user_id == uid, Task.assigned_to_id == uid))
        for t in q.all():
            out.append({
                'id': f"task-{t.id}", 'source': 'project',
                'description': t.description, 'status': t.status,
                'priority': getattr(t, 'priority', 'medium'),
                'weight': getattr(t, 'weight', 3),
                'due_date': t.due_date,
                'assigned_to': getattr(t, 'assigned_to', None),
            })

        daily_q = (
            db.session.query(DailyTaskAssignee, Assigned_Task)
            .join(Assigned_Task, DailyTaskAssignee.task_id == Assigned_Task.id)
            .filter(DailyTaskAssignee.deleted == False, Assigned_Task.deleted == False)
        )
        if not is_admin:
            daily_q = daily_q.filter(DailyTaskAssignee.user_id == uid)
        for da, dt in daily_q.all():
            status = 'completed' if da.status == 'completed' else (
                     'on-going' if da.status == 'in_progress' else da.status)
            out.append({
                'id': f"daily-{dt.id}-{da.user_id}", 'source': 'daily',
                'description': getattr(dt, 'title', None) or getattr(dt, 'description', '') or 'Daily task',
                'status': status, 'priority': getattr(dt, 'priority', 'medium'),
                'weight': getattr(dt, 'weight', 3),
                'due_date': dt.due_date, 'assigned_to': None,
            })

    if HAS_TEMP:
        tt_q = TemporaryTask.query.filter_by(is_deleted=False)
        if not is_admin:
            tt_q = tt_q.filter_by(assigned_to=uid)
        for tt in tt_q.all():
            status = 'completed' if tt.status == 'done' else tt.status
            out.append({
                'id': f"temp-{tt.id}", 'source': 'temp',
                'description': tt.description, 'status': status,
                'priority': getattr(tt, 'priority', 'medium'),
                'weight': getattr(tt, 'weight', 3),
                'due_date': tt.due_date, 'assigned_to': None,
            })

    return out

