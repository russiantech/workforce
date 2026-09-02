# web/apis/assigned_task.py

from flask import request, jsonify, current_app
from flask_login import current_user, login_required
from web.models.projects import (  Task, Assigned_Task )
from web.models import db
from web import csrf
from datetime import datetime

def handle_response(message=None, alert=None, data=None):
    """ only success response should have data and be set to True. And  """
    response_data = {
        'message': message,
    }
    if data:
        response_data['alert'] = alert

    if data:
        response_data['data'] = data

    return response_data

from flask import Blueprint
assigned_task_bp = Blueprint('assigned_task_api', __name__)

# create tasks
@assigned_task_bp.route('/assigned-tasks', methods=['POST'])
@login_required
@csrf.exempt
def assign_task():
    
    if not db.session.is_active:
            db.session.begin()
            
    # Check if the request's content type is JSON
    if request.headers['Content-Type'] == 'application/json':

        try:
            # Attempt to parse the JSON data
            data = request.get_json()

            detail = data.get('detail')
            duration = data.get('duration', datetime.timestamp)

            if not detail :
                return jsonify({'error': 'kindly provide a detail for this task'}), 400

            new_task = Assigned_Task(
                detail=detail,
                duration = duration if duration is not None and duration != "" else None, 
                #else set to None for timestamp so it can take default time
                user_id=current_user.id,
                user=current_user
            )

            db.session.add(new_task)
            db.session.commit()
            return jsonify({'success':True, 'message': 'Task Assigned successfully'}), 200
        
        except Exception as e:
            current_app.logger.exception(f"Unhandled error in web/apis/assigned_task.py: {e}")
             # Return an error response if JSON parsing fails
            return jsonify({"error": "Invalid JSON", "message": str(e)}), 400
    else:
        # Return an error response if the content type is not JSON
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
# fetch/get tasks
@assigned_task_bp.route('/assigned-tasks', methods=['GET'])
@login_required
@csrf.exempt
def get_assigned_tasks():
    try:
        user_id = current_user.id
        tasks = Assigned_Task.query.filter_by(user_id=user_id).order_by(Assigned_Task.created.desc()).all()

        tasks_list = []
        for task in tasks:
            tasks_list.append({
                'id': task.id,
                'detail': task.detail,
                'duration': task.duration or None
            })
        print(tasks_list)
        return jsonify({"tasks": tasks_list}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/assigned_task.py: {e}")
        return jsonify({"success": False, "error":f"{e}"}), 200

# updating
@assigned_task_bp.route('/assigned-tasks/<int:task_id>', methods=['PUT'])
@login_required
@csrf.exempt
def update_assigned_task(task_id):
    try:
        data = request.get_json()
        task = Assigned_Task.query.get(task_id)
        
        if not task or task.user_id != current_user.id:
            return jsonify({"error": "Assigned Task not found"}), 404

        task.detail = data['detail']
        task.duration = data['duration']
        
        db.session.commit()
        return jsonify({"success": True, "message":"Assigned Task updated successfully"}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/assigned_task.py: {e}")
        return jsonify({"success": False, "error":f"{e}"}), 200
    
# deletion
@assigned_task_bp.route('/assigned-tasks/<int:task_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_assigned_task(task_id):
    try:
        
        task = Assigned_Task.query.get(task_id)
        
        if not task or task.user_id != current_user.id:
            return jsonify({"error": "Task not found"}), 404

        db.session.delete(task)
        db.session.commit()
        # return jsonify({"success": True}), 200
        return jsonify({"success": True, "message":"Assigned Task deleted successfully"}), 200
    
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/assigned_task.py: {e}")
        return jsonify({"success": False, "error":f"{e}"}), 200