from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_session import Session
# from flask_oauthlib.client import OAuth
from web.models import db
from web.models.users import User

from dotenv import load_dotenv
from web.utils import slug
from web.utils import activelink
load_dotenv()

csrf = CSRFProtect()
f_session = Session()
bcrypt = Bcrypt()
s_manager = LoginManager()
mail = Mail()
migrate = Migrate()
moment = Moment()
# oauth = OAuth()

from authlib.integrations.flask_client import OAuth  # New
oauth = OAuth()

import logging
from logging.handlers import RotatingFileHandler

# ── Logging ──────────────────────────────────────────────────────────────
# NOTE: `logging.basicConfig()` is a no-op if the root logger already has a
# handler attached (very easy to happen once other libraries — Werkzeug,
# APScheduler, etc. — are imported first), which is why error tracebacks
# were silently going nowhere while Werkzeug's own access-log lines still
# showed up in errors.log. Attaching an explicit handler with force=True
# guarantees it takes effect regardless of import order.
_log_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s'
)
_file_handler = RotatingFileHandler('errors.log', maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_log_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[_file_handler], force=True)
loggings = logging.getLogger()  # kept for backward compatibility (web/auth/routes.py does `from web import loggings`)


@s_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

s_manager.login_view = 'auth.signin'

def configure_extensions(app):
    db.init_app(app)
    csrf.init_app(app)
    f_session.init_app(app)
    bcrypt.init_app(app)
    s_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    moment.init_app(app)
    oauth.init_app(app)

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_pyfile('confiq.py') # Load configuration from a separate file
    app.logger.setLevel(logging.DEBUG)
    configure_extensions(app)
    
    # Register blueprints
    
    # APIS
    from web.apis.attendance import attendance_bp_old
    app.register_blueprint(attendance_bp_old)
    
    # #
    from web.apis.attendance_api import attendance_bp
    app.register_blueprint(attendance_bp, url_prefix='/api')

    # Start weekly attendance email scheduler
    from web.apis.attendance_api import init_scheduler
    init_scheduler(app)

    from web.apis.dashboard_api  import dashboard_bp
    app.register_blueprint(dashboard_bp,  url_prefix='/api')
    # 

    from web.apis.projects import project_bp
    app.register_blueprint(project_bp, url_prefix='/api')
    
    from web.apis.tasks import task_bp
    app.register_blueprint(task_bp, url_prefix='/api')

    from web.apis.tasks.daily_tasks import daily_task_bp
    app.register_blueprint(daily_task_bp, url_prefix='/api')
    
    from web.apis.tasks.task_weights import weight_bp
    app.register_blueprint(weight_bp, url_prefix='/api')

    from web.views.projects import project_views_bp
    app.register_blueprint(project_views_bp)

    from web.views.daily_tasks import daily_task_views_bp
    app.register_blueprint(daily_task_views_bp)
    
    from web.views.staff_roles import roles_view_bp
    app.register_blueprint(roles_view_bp)

    from web.apis.staff_roles import roles_bp
    app.register_blueprint(roles_bp, url_prefix='/api')
    
    # VIEWS
    from web.views.attendance import attendance_view_bp
    app.register_blueprint(attendance_view_bp)

    from web.auth.routes import auth
    app.register_blueprint(auth)

    from web.main.routes import main
    app.register_blueprint(main)
    
    from web.errors.handlers import errors_bp
    app.register_blueprint(errors_bp)
    
    from web.utils.user_role import has_role
    # Register the filter with Flask/Jinja
    app.jinja_env.filters['has_role'] = has_role

    app.jinja_env.filters['slugify'] = slug.slugify
    app.jinja_env.globals.update(is_active=activelink.is_active)
    
    # 
    # app = create_app()

    return app
