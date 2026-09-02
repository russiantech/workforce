"""
Workforce — Project Page Views  +  Helper API
===============================================
Register in your app factory:
    from web.views.project_views import project_views_bp
    app.register_blueprint(project_views_bp)

This file handles:
  GET  /projects                → dashboard.html
  GET  /projects/<id>/board     → board.html
  GET  /api/users-list          → JSON list of users (used by member select)
"""

from flask import Blueprint, render_template, jsonify, abort
from flask_login import login_required, current_user

from web.models.users import User
from web.models.projects import Project, ProjectMember
from web.utils.decorators import role_required
from web.utils.user_role import has_role

project_views_bp = Blueprint('project_views', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@project_views_bp.route('/projects')
@login_required
def projects_dashboard():
    """Main projects listing page."""
    return render_template('projects/dashboard.html')


@project_views_bp.route('/projects/<int:project_id>/board')
@login_required
def project_board(project_id):
    """Kanban board for a single project."""
    project = Project.query.filter_by(id=project_id, deleted=False).first_or_404()

    # Access check
    is_admin = has_role(current_user, ['admin', 'hr', 'dev'])
    if not is_admin:
        m = ProjectMember.query.filter_by(
            project_id=project_id, user_id=current_user.id
        ).first()
        if not m:
            abort(403)
            # print(m)

    return render_template(
        'projects/board.html',
        project_id=project_id,
        project_title=project.title,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPER API — users list for member select dropdowns
# ─────────────────────────────────────────────────────────────────────────────

@project_views_bp.route('/api/users-list')
@login_required
def users_list():
    """
    Returns a lightweight list of active users for populating member selects.
    Accessible to any logged-in user (names only, no sensitive data).
    """
    # users = User.query.filter_by(deleted=False, status=True).order_by(User.name).all()
    users = User.query.filter_by(deleted=False).order_by(User.name).all()
    return jsonify({'users': [
        {'id': u.id, 'name': u.name, 'username': u.username, 'photo': u.photo}
        for u in users
    ]})

