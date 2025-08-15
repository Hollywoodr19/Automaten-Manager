# config/__init__.py
"""
Konfiguration für Automaten Manager v2.0
Unterstützt Development, Testing und Production
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""

    # Application
    APP_NAME = 'Automaten Manager'
    APP_VERSION = '2.0.0'

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_APP = 'app'

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/automaten'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

    # Cache
    CACHE_TYPE = 'RedisCache'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'automaten_'

    # Session
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Security
    BCRYPT_LOG_ROUNDS = 13
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'

    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@automaten-manager.com')

    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_HEADERS_ENABLED = True

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'csv', 'xlsx'}

    # Pagination
    ITEMS_PER_PAGE = 20

    # Monitoring
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', 0.1))
    ELASTIC_APM_ENABLED = os.getenv('ELASTIC_APM_ENABLED', 'False').lower() == 'true'
    ELASTIC_APM_SECRET_TOKEN = os.getenv('ELASTIC_APM_SECRET_TOKEN')
    ELASTIC_APM_SERVER_URL = os.getenv('ELASTIC_APM_SERVER_URL')

    # Admin
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@automaten-manager.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme123!')

    # Features Flags
    FEATURE_ML_PREDICTIONS = os.getenv('FEATURE_ML_PREDICTIONS', 'True').lower() == 'true'
    FEATURE_REALTIME_UPDATES = os.getenv('FEATURE_REALTIME_UPDATES', 'True').lower() == 'true'
    FEATURE_PWA_ENABLED = os.getenv('FEATURE_PWA_ENABLED', 'True').lower() == 'true'
    FEATURE_MULTI_LANGUAGE = os.getenv('FEATURE_MULTI_LANGUAGE', 'True').lower() == 'true'

    # Localization
    BABEL_DEFAULT_LOCALE = 'de'
    BABEL_DEFAULT_TIMEZONE = 'Europe/Berlin'
    LANGUAGES = {
        'de': 'Deutsch',
        'en': 'English',
        'fr': 'Français',
        'es': 'Español'
    }


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = False

    # Less secure settings for development
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False

    # Development database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/automaten_dev'
    )

    # Development email (MailHog)
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False

    # Disable rate limiting in development
    RATELIMIT_ENABLED = False

    # CORS - allow all origins in development
    CORS_ORIGINS = ['*']


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    DEBUG = True

    # Use in-memory SQLite for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Use simple password hashing for faster tests
    BCRYPT_LOG_ROUNDS = 4

    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False

    # Require HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

    # Stronger password hashing
    BCRYPT_LOG_ROUNDS = 15

    # Production database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    # Enable all security features
    WTF_CSRF_ENABLED = True
    RATELIMIT_ENABLED = True

    # Production email settings
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True

    # Stricter rate limits
    RATELIMIT_DEFAULT = "50/hour"

    # Production logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}