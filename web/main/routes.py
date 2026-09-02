# web/main/routes.py

import traceback
from flask import g, stream_template, Blueprint, flash, request, jsonify, current_app
from flask_login import current_user, login_required

import os
from flask import send_file
from web.models.attendance import Attendance
from datetime import datetime

from web.models import db
from web.models.projects import Task, Assigned_Task
from web.models.users import User

from web.utils.db_session_management import db_session_management
from web.utils.decorators import role_required

main = Blueprint('main', __name__)

@main.route("/")
@login_required
# @role_required('manager', 'admin', '*')
@role_required('*')
@db_session_management
def index():
    user_id = current_user.id
    # tasks = Task.query.filter_by(user_id=user_id).order_by(Task.timestamp.desc()).all()
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.timestamp.desc()).limit(15).all()
    assigned_tasks = Assigned_Task.query.filter_by(user_id=user_id).order_by(Assigned_Task.created.desc()).all()

    tasks_list = []
    for task in tasks:
        
        tasks_list.append({
            'id': task.id,
            'description': task.description,
            'status': task.status,
            'timestamp': task.timestamp.strftime('%Y-%m-%d') \
                if task.timestamp is not None and task.timestamp != "" else None
        })
    
    assigned_tasks_list = []
    for task in assigned_tasks:
        
        assigned_tasks_list.append({
            'id': task.id,
            'detail': task.detail,
            'duration': task.duration or None
        })
    
    context = {
        "tasks_list": tasks_list,
        "assigned_tasks_list": assigned_tasks_list,
        "status_options" : ["pending", "completed", "on-going", "stucked", "cancelled"]  # Define status options
        }

    return stream_template('dashboard/dashboard_page.html', **context)
    # return stream_template('index.html', **context)

@main.route("/users", methods=['GET', 'POST'])
@role_required('hr', 'dev', 'md', 'admin')
@db_session_management
def users():
    try:
        referrer =  request.headers.get('Referer')        
        username, action = request.args.get('username', None), request.args.get('action', None)
        if username != None and action == 'del':
            user = User.query.filter(User.deleted == 0, User.username==username).first()
            print(f"Action: {action}, Username: {username}, User Found: {user is not None}")

            if user:
                Attendance.query.filter_by(user_id=user.id).delete()
                # user.name = user.name
                # user.deleted = True
                db.session.delete(user)
                db.session.commit()
                
                flash(f'User Has Been Deleted!', 'danger')
                return jsonify({ 
                    'response': f'User deleted successfully',
                    'flash':'alert-danger',
                    'link': f'{referrer}'})
                
            return jsonify({ 
                    'response': f'User Not Available',
                    'flash':'alert-warning',
                    'link': f'{referrer}'} )
        
        page = request.args.get('page', 1, type=int)  # Get the requested page number
        per_page = 200  # Number of items per page
        #users = User.query.order_by(User.id.desc()).paginate(page=page, per_page=per_page)
        users = User.query.filter(User.deleted == 0).order_by( User.created.desc()).paginate(page=page, per_page=per_page)
        g.brand = {"name":"dunistech.ng"}
        g.user = User.query.filter(User.deleted == 0, User.username==username).first()
        context = {
            'pname' : 'Users : (staffs | intern | clients | student)',
            'users': users
            }
        
        return stream_template('users/index.html', **context)
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/main/routes.py: {e}")
        traceback.print_exc()
        return jsonify({'success':True, 'error': f'{e}'})
    
