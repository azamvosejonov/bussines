from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_babel import Babel
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
mail = Mail()
babel = Babel()

def get_locale_function():
    """Determine the best locale to use for the current request."""
    from flask import request, session
    
    # Check if user has a preferred language in session
    if 'lang' in session:
        return session['lang']
    
    # Check if user has language preference in their profile
    try:
        from flask import g
        if hasattr(g, 'user') and g.user and hasattr(g.user, 'preferences') and g.user.preferences:
            preferences = g.user.preferences[0] if isinstance(g.user.preferences, list) else g.user.preferences
            if hasattr(preferences, 'language') and preferences.language:
                return preferences.language
    except:
        pass
    
    # Fall back to browser's Accept-Language header
    return request.accept_languages.best_match(['en', 'uz', 'ru'], default='uz')

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    
    # Babel configuration for internationalization
    app.config['BABEL_DEFAULT_LOCALE'] = 'uz'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'uz', 'ru']
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'Asia/Tashkent'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(os.path.dirname(__file__), 'translations')
    
    # Disable CSRF protection for API endpoints
    app.config['WTF_CSRF_ENABLED'] = False

    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    
    # Initialize Babel
    babel.init_app(app, locale_selector=get_locale_function)
    
    # Exempt API routes from CSRF protection
    csrf.exempt('web.calculate_tax')
    csrf.exempt('web.convert_currency')
    mail.init_app(app)

    # Register blueprints here later
    from .routes.auth import auth_bp
    from .routes.business import business_bp
    from .routes.employees import employees_bp
    from .routes.sales import sales_bp
    from .routes.expenses import expenses_bp
    from .routes.payroll import payroll_bp
    from .routes.reports import reports_bp
    from .routes.notifications import notifications_bp
    from .routes.web import web_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(business_bp, url_prefix='/api')
    app.register_blueprint(employees_bp, url_prefix='/api/<int:biz_id>')
    app.register_blueprint(sales_bp, url_prefix='/api/<int:biz_id>')
    app.register_blueprint(expenses_bp, url_prefix='/api/<int:biz_id>')
    app.register_blueprint(payroll_bp, url_prefix='/api/<int:biz_id>')
    app.register_blueprint(reports_bp, url_prefix='/api/<int:biz_id>')
    app.register_blueprint(notifications_bp, url_prefix='/api/<int:biz_id>')
    app.register_blueprint(web_bp)

    with app.app_context():
        db.create_all()

        # Initialize business types
        from .models.business_types import BUSINESS_TYPES, BusinessType
        for bt_data in BUSINESS_TYPES:
            if not BusinessType.query.filter_by(name=bt_data['name']).first():
                bt = BusinessType(**bt_data)
                db.session.add(bt)
        db.session.commit()

        # Initialize notification scheduler
        from .services.notifications import alert_checker
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=lambda: asyncio.run(alert_checker.run_all_checks()),
                         trigger="interval", hours=1)  # Check every hour
        scheduler.start()

    return app