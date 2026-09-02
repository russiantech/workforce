from flask import Blueprint, render_template, request
from flask_limiter.util import get_remote_address

from sqlalchemy.exc import InterfaceError, ProgrammingError
from werkzeug.exceptions import MethodNotAllowed

from web.models import db
from web.errors.response import error_response as api_error_response

errors_bp = Blueprint('errors_bp', __name__)

def wants_json_response():
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']

@errors_bp.app_errorhandler(400)
def error_400(error):
    """ 400 (BAD REQUEST """
    if wants_json_response():
        return api_error_response(400)
    return render_template('errors/400.html', e=error), 400

@errors_bp.app_errorhandler(403)
def error_403(error):
    db.session.rollback()
    if wants_json_response():
        return api_error_response(403)
    return render_template('errors/403.html', e=error), 403

@errors_bp.app_errorhandler(404)
def error_404(error):
    """ Not found error """
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html', e=error), 404

@errors_bp.app_errorhandler(MethodNotAllowed or 405)
def error_405(error):
    """Handle Method Not Allowed error."""
    if wants_json_response():
        return api_error_response(405)
    return render_template('errors/405.html'), 405

@errors_bp.app_errorhandler(413)
def error_413(error):
    """ HTTP status code 413 (Payload Too Large) """
    if wants_json_response():
        return api_error_response(413)
    return render_template('errors/413.html', e=error), 413

@errors_bp.app_errorhandler(415)
def error_415(error):
    """ Internal server error """
    db.session.rollback()
    if wants_json_response():
        return api_error_response(415, message="Unsupported Media Type")
    return render_template('errors/415.html', e=error), 415

@errors_bp.app_errorhandler(429)
# @limiter.request_filter
def error_429(error):
    """ Too many request error """
    db.session.rollback()
    if wants_json_response():
        return api_error_response(429)
    return render_template('errors/429.html', e=error, client = get_remote_address()), 429 


@errors_bp.app_errorhandler(500)
def error_500(error):
    """ Internal server error """
    db.session.rollback()
    if wants_json_response():
        return api_error_response(500)
    return render_template('errors/500.html', e=error), 500

@errors_bp.app_errorhandler(InterfaceError or ProgrammingError)
def error_db(error):
    """ Handle InterfaceError, typically related to database connectivity issues. """
    print("Caught an InterfaceError:", error)
    db.session.rollback()
    if wants_json_response():
        return api_error_response(500, message="db-related issues")  # Internal Server Error
    return render_template('errors/500.html', e=error), 500


# Rest of my error handling logic


