# web/apis/tasks.py
from flask import request, jsonify, current_app
from flask_login import current_user, login_required
from sqlalchemy.sql.expression import func
from web.models import (
    Task
)
from web.models import db
from web import csrf

from flask import Blueprint
task_bp = Blueprint('task_api', __name__)

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

from datetime import datetime, date

# create tasks
@task_bp.route('/tasks', methods=['POST'])
@login_required
@csrf.exempt
def add_task():
    
    if not db.session.is_active:
            db.session.begin()
            
    # Check if the request's content type is JSON
    if request.headers['Content-Type'] == 'application/json':

        try:
            # Attempt to parse the JSON data
            data = request.get_json()

            description = data.get('description')
            status = data.get('status', 'pending')
            timestamp = data.get('timestamp', datetime.timestamp)

            if not description :
                return jsonify({'error': 'kindly provide a description for this task'}), 400

            # 
            weight = data.get('weight', 3)
            try:
                weight = max(1, min(int(weight), 10))
            except (ValueError, TypeError):
                weight = 3
                
            new_task = Task(
                description=description,
                status=status,
                timestamp=timestamp if timestamp is not None and timestamp != "" else None, 
                #else set to None for timestamp so it can take default time
                
                weight=weight,
                weight_locked=False,  # or read from data if admin
        
                user_id=current_user.id,
                user=current_user
            )

            db.session.add(new_task)
            db.session.commit()
            return jsonify({'success':True, 'message': 'Task added successfully'}), 200
        
        except Exception as e:
            current_app.logger.exception(f"Unhandled error in web/apis/tasks.py: {e}")
             # Return an error response if JSON parsing fails
            return jsonify({"error": "Invalid JSON", "message": str(e)}), 400
    else:
        # Return an error response if the content type is not JSON
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
# fetch/get tasks
@task_bp.route('/tasks', methods=['GET'])
@login_required
@csrf.exempt
def get_tasks():
    try:
        user_id = current_user.id
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.timestamp.desc()).all()

        tasks_list = []
        for task in tasks:
            tasks_list.append({
                'id': task.id,
                'description': task.description,
                'status': task.status,
                'timestamp': task.timestamp.strftime('%Y-%m-%d')\
                    if task.timestamp and task.timestamp != "" else None
            })
        print(tasks_list)
        return jsonify({"tasks": tasks_list}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks.py: {e}")
        return jsonify({"success": False, "error":f"{e}"}), 200

# updating
@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
@csrf.exempt
def update_task(task_id):
    try:
        data = request.get_json()
        task = Task.query.get(task_id)
        
        if not task or task.user_id != current_user.id:
            return jsonify({"error": "Task not found"}), 404

        task.description = data['description']
        task.status = data['status']
        # print(type(data['timestamp']))
        task.timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%d') \
            if isinstance(data['timestamp'], date) else func.now()

        db.session.commit()
        return jsonify({"success": True, "message":"Task updated successfully"}), 200
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks.py: {e}")
        return jsonify({"success": False, "error":f"{e}"}), 200
    
# deletion
@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_task(task_id):
    try:
        
        task = Task.query.get(task_id)
        
        if not task or task.user_id != current_user.id:
            return jsonify({"error": "Task not found"}), 404

        db.session.delete(task)
        db.session.commit()
        # return jsonify({"success": True}), 200
        return jsonify({"success": True, "message":"Task deleted successfully"}), 200
    
    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/tasks.py: {e}")
        return jsonify({"success": False, "error":f"{e}"}), 200