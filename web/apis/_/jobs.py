from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from web import db, csrf
from web.models import JobDescription, JobResponsibility
from web.models.users import User
from web.utils.user_role import has_role
import traceback

job_api = Blueprint('job_api', __name__)

@job_api.route('/job/create', methods=['POST'])
@login_required
@csrf.exempt
def create_job():
    try:
        if not has_role(current_user, ['admin', 'dev', 'hr']):
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json()
        user = User.query.get_or_404(data['user_id'])

        job = JobDescription(
            user_id=user.id,
            title=data['title'],
            department=data.get('department'),
            employment_type=data.get('employment_type'),
            location=data.get('location'),
            description=data.get('description'),
            requirements=data.get('requirements')
        )

        db.session.add(job)
        db.session.commit()

        return jsonify({"message": "Job created", "job_id": job.id}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/jobs.py: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@job_api.route('/job/update/<int:job_id>', methods=['PUT'])
@login_required
@csrf.exempt
def update_job(job_id):
    try:
        if not has_role(current_user, ['admin', 'dev', 'hr']):
            return jsonify({"error": "Permission denied"}), 403

        job = JobDescription.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        data = request.get_json()

        for field in ['title','department','employment_type','location',
                      'description','responsibilities','requirements']:
            setattr(job, field, data.get(field))

        db.session.commit()
        return jsonify({"message": "Job updated successfully"}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/jobs.py: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@job_api.route('/job/delete/<int:job_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_job(job_id):
    try:
        if not has_role(current_user, ['admin', 'dev', 'hr']):
            return jsonify({"error": "Permission denied"}), 403

        job = JobDescription.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        job.is_active = False
        db.session.commit()

        return jsonify({"message": "Job deleted successfully"}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/jobs.py: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# RESPONSIBILITIES ENDPOINTS
@job_api.route('/job/<int:job_id>/responsibility', methods=['POST'])
@login_required
@csrf.exempt
def add_responsibility(job_id):
    try:
        job = JobDescription.query.get_or_404(job_id)

        if not has_role(current_user, ['admin', 'dev', 'hr']):
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json()

        resp = JobResponsibility(
            job_id=job.id,
            content=data['content'],
            position=len(job.responsibilities) + 1
        )

        db.session.add(resp)
        db.session.commit()

        return jsonify({"message": "Responsibility added"}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/jobs.py: {e}")
        return jsonify({"error": str(e)}), 500


@job_api.route('/responsibility/<int:resp_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_responsibility(resp_id):
    try:
        resp = JobResponsibility.query.get_or_404(resp_id)

        if not has_role(current_user, ['admin', 'dev', 'hr']):
            return jsonify({"error": "Permission denied"}), 403

        db.session.delete(resp)
        db.session.commit()

        return jsonify({"message": "Responsibility removed"}), 200

    except Exception as e:
        current_app.logger.exception(f"Unhandled error in web/apis/jobs.py: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
