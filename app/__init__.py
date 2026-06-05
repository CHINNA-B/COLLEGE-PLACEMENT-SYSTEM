import os
from flask import Flask
from app.config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.student import student_bp
    app.register_blueprint(student_bp, url_prefix='/student')

    from app.company import company_bp
    app.register_blueprint(company_bp, url_prefix='/company')

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/notifications')

    # Register root route
    from flask import redirect, url_for, render_template
    from flask_login import current_user

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'company':
                return redirect(url_for('company.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        return render_template('landing.html')

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    # Context processor for notifications count
    @app.context_processor
    def inject_notification_count():
        if current_user.is_authenticated:
            from app.models import Notification
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
            return {'unread_notifications': unread}
        return {'unread_notifications': 0}

    # Create database tables and seed admin
    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    """Create default admin account if none exists."""
    from app.models import User
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@college.edu',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(' * Default admin created: admin@college.edu / admin123')
