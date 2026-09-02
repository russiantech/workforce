# web/views/daily_tasks.py
"""
Workforce — Daily Tasks Page View
==================================
Register in the app factory:
    from web.views.daily_tasks import daily_task_views_bp
    app.register_blueprint(daily_task_views_bp)

    GET /daily-tasks   → daily_tasks/board.html
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from web.models.users import User
from web.utils.user_role import has_role

daily_task_views_bp = Blueprint('daily_task_views', __name__)


@daily_task_views_bp.route('/daily-tasks')
@login_required
def daily_tasks_page():
    """Daily / duty task tracker — admins assign & track, staff manage their own."""
    is_manager = has_role(current_user, ['admin', 'hr', 'dev', 'md'])
    staff = []
    if is_manager:
        staff = User.query.filter_by(deleted=False).order_by(User.name).all()

    return render_template(
        'daily_tasks/board.html',
        is_manager=is_manager,
        staff=staff,
    )
