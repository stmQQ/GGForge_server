import os


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-key')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
