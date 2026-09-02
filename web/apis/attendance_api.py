"""
Workforce — Attendance API
===========================
Register in your app factory:
    from web.apis.attendance import attendance_bp
    app.register_blueprint(attendance_bp, url_prefix='/api')

Weekly scheduler (add to app factory after creating app):
    from web.apis.attendance import init_scheduler
    init_scheduler(app)

Endpoints
─────────
GET  /api/attendance                    list records (admin: all, staff: own)
GET  /api/attendance/export-csv         download CSV (date range in filename)
GET  /api/attendance/stats              aggregate stats for dashboard widgets
POST /api/attendance/schedule-email     manually trigger weekly email export
GET  /api/attendance/weekly-report      JSON weekly report data

Models expected
───────────────
Attendance:
    id, user_id (FK→user.id), sign_in_time, sign_out_time, created
    Relationship: user (→User)
"""

import csv
import io
from datetime import datetime, date, timedelta

from flask import Blueprint, request, jsonify, Response, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from web import csrf
from web.models.users import User
from web.models.attendance import Attendance   # adjust import path if needed
from web.utils.user_role import has_role

attendance_bp = Blueprint('attendance_api', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _dn(user):
    if not user: return 'Unknown'
    return (user.name or '').strip() or user.username or str(user.id)


def _is_admin(user):
    return has_role(user, ['admin', 'hr', 'dev', 'manager'])


def _parse_date(s, fallback=None):
    """Parse YYYY-MM-DD string → date object, or return fallback."""
    if not s:
        return fallback
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return fallback


def _duration_minutes(sign_in, sign_out):
    """Return session duration in minutes, or None."""
    if sign_in and sign_out:
        try:
            delta = sign_out - sign_in
            return round(delta.total_seconds() / 60, 1)
        except Exception:
            return None
    return None


def _record_to_dict(a):
    user = a.user
    duration = _duration_minutes(a.sign_in_time, a.sign_out_time)
    return {
        'id':           a.id,
        'user_id':      a.user_id,
        'user_name':    _dn(user),
        'user_photo':   user.photo if user else None,
        'user_email':   user.email if user else None,
        'user_roles':   user.my_roles if user else [],
        'user_category':getattr(user, 'category', None),
        'sign_in':      a.sign_in_time.strftime('%H:%M:%S') if a.sign_in_time else None,
        'sign_out':     a.sign_out_time.strftime('%H:%M:%S') if a.sign_out_time else None,
        'duration_min': duration,
        'date':         a.created.strftime('%Y-%m-%d') if a.created else None,
        'date_display': a.created.strftime('%d %b %Y') if a.created else None,
        'created':      a.created.isoformat() if a.created else None,
    }


def _base_query(user, date_from=None, date_to=None, category=None):
    """
    Build a filtered attendance query.
    Admins/HR/managers see all records; staff see only their own.
    """
    q = Attendance.query.join(User, Attendance.user_id == User.id)\
                        .filter(User.deleted == False)

    if not _is_admin(user):
        q = q.filter(Attendance.user_id == user.id)

    if date_from:
        q = q.filter(func.date(Attendance.created) >= date_from)
    if date_to:
        q = q.filter(func.date(Attendance.created) <= date_to)

    if category and _is_admin(user):
        if category != 'general':
            q = q.filter(User.category == category)

    return q.order_by(Attendance.created.desc())


# ─────────────────────────────────────────────────────────────────────────────
# LIST RECORDS
# ─────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/attendance', methods=['GET'])
@login_required
@csrf.exempt
def list_attendance():
    """
    Paginated attendance records.
    Query params: date_from, date_to, category, page, per_page, user_id (admin)
    """
    try:
        page      = request.args.get('page', 1, type=int)
        per_page  = request.args.get('per_page', 50, type=int)
        date_from = _parse_date(request.args.get('date_from'))
        date_to   = _parse_date(request.args.get('date_to'))
        category  = request.args.get('category', '').lower() or None
        uid_filter= request.args.get('user_id', type=int)

        q = _base_query(current_user, date_from, date_to, category)
        if uid_filter and _is_admin(current_user):
            q = q.filter(Attendance.user_id == uid_filter)

        pag = q.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'records':   [_record_to_dict(a) for a in pag.items],
            'total':     pag.total,
            'pages':     pag.pages,
            'page':      page,
            'date_from': str(date_from) if date_from else None,
            'date_to':   str(date_to)   if date_to   else None,
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/attendance_api.py: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# CSV EXPORT  (filename includes date range)
# ─────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/attendance/export-csv', methods=['GET'])
@login_required
def export_csv():
    """
    Download attendance as CSV.
    Filename: attendance_YYYY-MM-DD_to_YYYY-MM-DD.csv

    Query params: date_from, date_to, category
    """
    try:
        date_from = _parse_date(request.args.get('date_from'))
        date_to   = _parse_date(request.args.get('date_to'))
        category  = request.args.get('category', '').lower() or None

        # Default: last 7 days if no range supplied
        if not date_from and not date_to:
            date_to   = date.today()
            date_from = date_to - timedelta(days=6)

        records = _base_query(current_user, date_from, date_to, category).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'S/N', 'User ID', 'Name', 'Email', 'Category',
            'Sign-In Time', 'Sign-Out Time', 'Duration (min)', 'Date'
        ])
        for i, a in enumerate(records, 1):
            user = a.user
            writer.writerow([
                i,
                a.user_id,
                _dn(user),
                user.email if user else '',
                getattr(user, 'category', '') if user else '',
                a.sign_in_time.strftime('%H:%M:%S') if a.sign_in_time else '',
                a.sign_out_time.strftime('%H:%M:%S') if a.sign_out_time else '',
                _duration_minutes(a.sign_in_time, a.sign_out_time) or '',
                a.created.strftime('%Y-%m-%d') if a.created else '',
            ])

        df_str = str(date_from or 'all')
        dt_str = str(date_to   or 'all')
        cat_str = f'_{category}' if category and category != 'general' else ''
        filename = f'attendance{cat_str}_{df_str}_to_{dt_str}.csv'

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/attendance_api.py: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# STATS  (used by dashboard widgets)
# ─────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/attendance/stats', methods=['GET'])
@login_required
@csrf.exempt
def attendance_stats():
    """
    Aggregate attendance stats.
    Admin: org-wide.  Staff: personal.
    Query params: date_from, date_to, days (shortcut: last N days)
    """
    try:
        days      = request.args.get('days', 30, type=int)
        date_from = _parse_date(request.args.get('date_from'),
                                fallback=date.today() - timedelta(days=days - 1))
        date_to   = _parse_date(request.args.get('date_to'),
                                fallback=date.today())

        q = _base_query(current_user, date_from, date_to)

        records = q.all()

        # ── Daily attendance count (for sparkline/heatmap) ─────────────────
        daily = {}
        for a in records:
            d = a.created.strftime('%Y-%m-%d') if a.created else None
            if d:
                daily[d] = daily.get(d, 0) + 1

        daily_series = [{'date': k, 'count': v}
                        for k, v in sorted(daily.items())]

        # ── Per-user totals (admin only) ───────────────────────────────────
        per_user = {}
        for a in records:
            uid  = a.user_id
            name = _dn(a.user)
            photo= a.user.photo if a.user else None
            if uid not in per_user:
                per_user[uid] = {'user_id': uid, 'name': name,
                                 'photo': photo, 'days': 0,
                                 'total_min': 0, 'last_seen': None}
            per_user[uid]['days'] += 1
            dur = _duration_minutes(a.sign_in_time, a.sign_out_time)
            if dur:
                per_user[uid]['total_min'] += dur
            if a.created:
                if not per_user[uid]['last_seen'] or a.created > per_user[uid]['last_seen']:
                    per_user[uid]['last_seen'] = a.created

        for u in per_user.values():
            ls = u['last_seen']
            u['last_seen'] = ls.strftime('%Y-%m-%d') if ls else None
            u['avg_hours'] = round(u['total_min'] / 60 / max(u['days'], 1), 2)

        per_user_list = sorted(per_user.values(), key=lambda x: x['days'], reverse=True)

        # ── Totals ─────────────────────────────────────────────────────────
        unique_users  = len(per_user)
        total_records = len(records)
        durations     = [_duration_minutes(a.sign_in_time, a.sign_out_time)
                         for a in records
                         if _duration_minutes(a.sign_in_time, a.sign_out_time)]
        avg_duration  = round(sum(durations) / len(durations), 1) if durations else 0

        return jsonify({
            'date_from':     str(date_from),
            'date_to':       str(date_to),
            'total_records': total_records,
            'unique_users':  unique_users,
            'avg_duration_min': avg_duration,
            'daily_series':  daily_series,
            'per_user':      per_user_list if _is_admin(current_user) else [],
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/attendance_api.py: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY REPORT DATA
# ─────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/attendance/weekly-report', methods=['GET'])
@login_required
@csrf.exempt
def weekly_report_data():
    """Returns last 7 days attendance breakdown for dashboard."""
    try:
        date_to   = date.today()
        date_from = date_to - timedelta(days=6)

        q       = _base_query(current_user, date_from, date_to)
        records = q.all()

        # Build 7-day array (even for days with zero attendance)
        days_map = {}
        for i in range(7):
            d = (date_from + timedelta(days=i)).strftime('%Y-%m-%d')
            days_map[d] = {'date': d, 'day': (date_from + timedelta(days=i)).strftime('%a'), 'count': 0}

        for a in records:
            d = a.created.strftime('%Y-%m-%d') if a.created else None
            if d and d in days_map:
                days_map[d]['count'] += 1

        return jsonify({
            'series': list(days_map.values()),
            'total':  len(records),
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/attendance_api.py: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# MANUAL EMAIL TRIGGER
# ─────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/attendance/schedule-email', methods=['POST'])
@login_required
@csrf.exempt
def trigger_email():
    """Manually trigger the weekly attendance email (admin only)."""
    if not _is_admin(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    try:
        _send_weekly_attendance_email(current_app._get_current_object())
        return jsonify({'message': 'Weekly attendance email sent successfully'}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/attendance_api.py: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY EMAIL FUNCTION (called by scheduler and manual trigger)
# ─────────────────────────────────────────────────────────────────────────────

def _send_weekly_attendance_email(app):
    """
    Generate and email the weekly attendance CSV to all admin users.
    Calls itself inside an app context so it works from the scheduler.
    """
    with app.app_context():
        from flask_mail import Message
        from web import mail   # adjust import to your Flask-Mail instance

        date_to   = date.today()
        date_from = date_to - timedelta(days=6)

        # All non-deleted users for the query (admin context — no user filter)
        records = (
            Attendance.query
            .join(User, Attendance.user_id == User.id)
            .filter(
                User.deleted == False,
                func.date(Attendance.created) >= date_from,
                func.date(Attendance.created) <= date_to,
            )
            .order_by(Attendance.created.desc())
            .all()
        )

        # Build CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'S/N', 'User ID', 'Name', 'Email', 'Category',
            'Sign-In', 'Sign-Out', 'Duration (min)', 'Date'
        ])
        for i, a in enumerate(records, 1):
            u = a.user
            writer.writerow([
                i, a.user_id, _dn(u),
                u.email if u else '',
                getattr(u, 'category', '') if u else '',
                a.sign_in_time.strftime('%H:%M:%S') if a.sign_in_time else '',
                a.sign_out_time.strftime('%H:%M:%S') if a.sign_out_time else '',
                _duration_minutes(a.sign_in_time, a.sign_out_time) or '',
                a.created.strftime('%Y-%m-%d') if a.created else '',
            ])

        filename = f'attendance_{date_from}_to_{date_to}.csv'
        csv_bytes = output.getvalue().encode('utf-8')

        # Find all admin users as recipients
        admin_role = Role.query.filter_by(type='admin').first()
        hr_role    = Role.query.filter_by(type='hr').first()
        dev_role    = Role.query.filter_by(type='dev').first()
        recipients = set()
        for role in [r for r in [admin_role, hr_role, dev_role] if r]:
            for u in role.user.all():
                if u.email and not u.deleted:
                    recipients.add(u.email)

        # Also use config fallback
        fallback = app.config.get('ADMIN_EMAIL') or app.config.get('MAIL_DEFAULT_SENDER')
        if fallback:
            recipients.add(fallback)
            # pass

        if not recipients:
            app.logger.warning('Weekly attendance email: no recipients found.')
            return

        msg = Message(
            subject=f'Weekly Attendance Report — {date_from} to {date_to}',
            recipients=list(recipients),
            sender=app.config['MAIL_DEFAULT_SENDER'],
            body=(
                f'Please find attached the attendance report for '
                f'{date_from.strftime("%d %b %Y")} to {date_to.strftime("%d %b %Y")}.\n\n'
                f'Total records: {len(records)}\n'
                f'Generated automatically by Workforce.\n'
            ),
        )
        msg.attach(filename, 'text/csv', csv_bytes)

        try:
            mail.send(msg)
            app.logger.info(f'Weekly attendance email sent to: {", ".join(recipients)}')
        except Exception as mail_err:
            app.logger.error(f'Weekly attendance email failed: {mail_err}')
            raise


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER SETUP
# ─────────────────────────────────────────────────────────────────────────────

def init_scheduler(app):
    """
    Call this from your app factory after app creation:

        from web.apis.attendance import init_scheduler
        init_scheduler(app)

    Requires:
        pip install flask-apscheduler

    Config keys (optional, in your Flask config):
        WEEKLY_REPORT_DAY   — weekday to send (0=Mon … 6=Sun, default 6=Sunday)
        WEEKLY_REPORT_HOUR  — hour to send (24h, default 7)
        WEEKLY_REPORT_MIN   — minute (default 0)
        SCHEDULER_TIMEZONE  — timezone string (default 'UTC')
    """
    try:
        from flask_apscheduler import APScheduler
    except ImportError:
        app.logger.warning(
            'flask-apscheduler not installed. '
            'Weekly attendance emails will not be automated. '
            'Run: pip install flask-apscheduler'
        )
        return

    # Avoid double-init in debug reloader
    if app.config.get('_SCHEDULER_INITIALISED'):
        return
    app.config['_SCHEDULER_INITIALISED'] = True

    day    = app.config.get('WEEKLY_REPORT_DAY',  6)   # Sunday
    hour   = app.config.get('WEEKLY_REPORT_HOUR', 7)   # 07:00
    minute = app.config.get('WEEKLY_REPORT_MIN',  0)
    tz     = app.config.get('SCHEDULER_TIMEZONE', 'UTC')

    scheduler = APScheduler()

    # APScheduler config injected into Flask config
    app.config.setdefault('SCHEDULER_API_ENABLED', False)
    app.config.setdefault('JOBS', [
        {
            'id':       'weekly_attendance_email',
            'func':     'web.apis.attendance_api:_send_weekly_attendance_email',
            'args':     [app],
            'trigger':  'cron',
            'day_of_week': day,
            'hour':     hour,
            'minute':   minute,
            'timezone': tz,
        }
    ])

    scheduler.init_app(app)
    scheduler.start()
    app.logger.info(
        f'Attendance scheduler started — weekly email every '
        f'{"Mon Tue Wed Thu Fri Sat Sun".split()[day]} at {hour:02d}:{minute:02d} {tz}'
    )


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT GUARD for Role (needed by email function)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from web.models.users import Role
except ImportError:
    Role = None
