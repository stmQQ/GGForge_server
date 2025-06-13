import os


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-key')
    CORS_ORIGINS = ['http://localhost:5173',
                    'http://localhost:3000', 'https://stmQQ.github.io']
