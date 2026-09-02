import traceback
from sqlalchemy.exc import IntegrityError
from functools import wraps
from flask import redirect, request, jsonify, url_for, current_app
from web.models import db

def db_session_management(route_function):
    @wraps(route_function)
    def decorated_function(*args, **kwargs):
        try:
            # Check if a transaction is already active, if not, begin a new one
            # This prevents a "transaction already started" error
            if not db.session.is_active:
                db.session.begin()

            result = route_function(*args, **kwargs)

            # Commit the transaction only if it was started in this decorator
            if not db.session.is_active:
                db.session.commit()

            return result

        except IntegrityError as e:
            # Handle IntegrityError (constraint violation)
            print(e)
            db.session.rollback()
            referrer = request.headers.get('Referer')
            response = {'flash': 'alert-warning', 'link': str(referrer), 'response': f'Sorry this already existed, and should not be duplicated->'}
            return jsonify(response)

        except Exception as e:
            current_app.logger.exception(f"Unhandled error in web/utils/db_session_management.py: {e}")
            # Rollback the transaction in case of any other exception
            db.session.rollback()
            referrer = request.headers.get('Referer')
            response = {'flash': 'alert-warning', 'link': str(referrer), 'response': str(e)}
            
            error_message = str(e)
            traceback_info = traceback.format_exc()  # Get traceback information
            print( f"oops: {error_message}.\n hmm:{traceback_info}")

            #return jsonify(response), 500
            
            return redirect(referrer)

        finally:
            if not db.session.is_active:
                db.session.close()

    return decorated_function
