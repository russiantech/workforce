"""
Workforce — Roles & Responsibilities: Flask Routes + Registration
=================================================================
"""

import json
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from web.utils.user_role import has_role

roles_view_bp = Blueprint('roles_views', __name__, url_prefix='/roles')


@roles_view_bp.route('/admin')
@login_required
def roles_admin():
    """
    Admin/HR page: manage role definitions, assign roles, view defaulters.
    Access: admin and hr roles only.
    """
    
    print(current_user.my_roles)

    if not has_role(current_user, ['admin', 'md', 'hr', 'dev']):
        abort(403)
        
    # return render_template('staff_roles/admin.html')
    # return render_template('staff_roles/admin_0.html')
    return render_template('staff_roles/admin_1.html')


@roles_view_bp.route('/my-role')
@login_required
def my_role_page():
    """
    Staff self-service page: view own assigned role, duties, KPIs, requirements.
    All logged-in users can access this.
    """
    # Pass current user data as JSON for the template JS to consume
    current_user_json = {
        'id':       current_user.id,
        'name':     (current_user.name or '').strip() or current_user.username,
        'username': current_user.username,
        'photo':    getattr(current_user, 'photo', None),
        'role':     getattr(current_user, 'role', None),
    }

    return render_template(
        # 'staff_roles/my_role.html',
        'staff_roles/my_role_1.html',
        current_user_json=json.dumps(current_user_json)
    )

