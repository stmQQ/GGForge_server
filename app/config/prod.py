import os
from .base import BaseConfig
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class ProdConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 'postgresql://dev_db_gwaq_user:qTds3t9bIxiP6ldhBK2CugN1Dv1dAEtU@dpg-d1655rbipnbc73fir470-a.frankfurt-postgres.render.com/dev_db_gwaq')
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    JWT_TOKEN_LOCATION = ['headers']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=180)
    API_URL = os.getenv('API_URL', 'https://ggforge-server.onrender.com')
