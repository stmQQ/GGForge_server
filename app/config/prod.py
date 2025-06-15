import os
from .base import BaseConfig
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class ProdConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 'postgresql://postgres:postgres@localhost/dev_db').replace("postgres://", "postgresql://")
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    JWT_TOKEN_LOCATION = ['headers']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=180)
    API_URL = os.getenv('API_URL', 'https://ggforge-server.onrender.com')
