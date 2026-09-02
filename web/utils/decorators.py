# application/decorators.py
from functools import wraps
from flask import jsonify, redirect, url_for, flash
from flask_login import current_user
from functools import wraps
from flask import abort

def confirm_email(func):
    '''Check if email has been confirmed'''
    @wraps(func)
    def wrapper_function(*args, **kwargs):
        if current_user.is_authenticated and not current_user.verified :
            flash(f' You\'re Yet To Verify Your Account!', 'danger')
            return redirect(url_for('auth.unverified'))
        return func(*args, **kwargs)
    return wrapper_function

def disable_csrf(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        csrf.protect = False
        try:
            response = f(*args, **kwargs)
        finally:
            csrf.protect = True
        return response
    return decorated_function

def role_required(*required_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                # Return a JSON response if the user is not logged in
                return jsonify({'success': False, 'error': "login required"})

            user_has_role = any(r_roles in [role.type for role in current_user.roles] for r_roles in required_roles)
            allow_all = any('*' in r_roles for r_roles in required_roles)
            
            if user_has_role or allow_all:
                return view_func(*args, **kwargs)  # Proceed if the user has the required role(s)
            else:
                flash(f'{[x.type for x in current_user.roles]} do not have permission to access this page', 'danger')
                return redirect(url_for('main.index'))  # Ensure this redirect is returned

        return wrapper
    return decorator


def role_required_0(*required_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                # return redirect(url_for('auth.signin'))
                # Remove the "abort(401)" part, so it won't tamper/affect other operations
                return jsonify({'success': False, 'error': "login required"})

            user_has_role = any(r_roles in [role.type for role in current_user.roles] for r_roles in required_roles)
            allow_all = any( '*' in r_roles for r_roles in required_roles)
            
            # return view_func(*args, **kwargs) if user_has_role or allow_all else redirect(url_for('main.index', usrname=current_user.username)) #abort(403) #forbidden
            # return view_func(*args, **kwargs) if user_has_role or allow_all else redirect(url_for('main.index')) #abort(403) #forbidden
            
            if user_has_role or allow_all:
                return view_func(*args, **kwargs)
            
            else:
                flash(f'{[x.type for x in current_user.roles]} do not have permission to here', 'danger')
                # return jsonify({[x.type for x in current_user.roles]})
                # return jsonify([x.type for x in current_user.roles])
                redirect(url_for('main.index')) #abort(403) #forbidden

        return wrapper
    return decorator

def admin_or_current_user():
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                # return redirect(url_for('auth.signin'))  # or abort(401) #//Unauthorized/unauthenticated
                return jsonify({'success': False, 'error': "You've not been authenticated"})
            
            requested_username = kwargs.get('username')
            #if ( (current_user.is_admin()) | (current_user.username == usr.username) ):
            if ( (current_user.is_admin()) | (current_user.username == requested_username)  ):
                return view_func(*args, **kwargs) 
            else:
                #abort(403) #forbidden
                # return redirect(url_for('auth.update', username=current_user.username))
                # return redirect(url_for('main.index'))
                return jsonify({'success': False, 'error': "Only admin/account owners are allowed"})

        return wrapper
    return decorator
