import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create DB base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
# Use SQLite as a local database solution
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///wordpress_manager.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy with app
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # type: ignore
login_manager.login_message_category = 'info'

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Import and register blueprints
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models

    # Create all tables
    db.create_all()
    
    # Check if default admin user exists and create if not
    from models import User
    from werkzeug.security import generate_password_hash
    
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User()
        admin_user.username = 'admin'
        admin_user.email = 'admin@localhost'
        admin_user.password_hash = generate_password_hash('admin123')
        admin_user.role = 'admin'
        db.session.add(admin_user)
        db.session.commit()
        logger.info("Default admin user created")

    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.domains import domains_bp
    from routes.wordpress import wordpress_bp
    from routes.backups import backups_bp
    from routes.database import database_bp
    from routes.files import files_bp
    from routes.monitoring import monitoring_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(domains_bp)
    app.register_blueprint(wordpress_bp)
    app.register_blueprint(backups_bp)
    app.register_blueprint(database_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(monitoring_bp)

    # Setup user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

# Import and start scheduled tasks
from utils.backup_simple import setup_backup_jobs
setup_backup_jobs(scheduler)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
