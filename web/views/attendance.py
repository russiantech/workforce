from flask import Blueprint, render_template
from flask_login import login_required, current_user

attendance_view_bp = Blueprint('attendance_views', __name__, url_prefix='/attendance')


@attendance_view_bp.route('/')
@login_required
def attendance_page():
    """Standalone attendance records page."""
    return render_template('attendance/attendance_page.html')

