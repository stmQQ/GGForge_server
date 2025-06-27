import os

from flask import Flask, make_response, redirect
from .extensions import db, migrate, cors, jwt, ma
from .config import config_by_name
from .models import *
from .routes import register_routes
# from apscheduler_tasks import register_scheduler

from dotenv import load_dotenv

load_dotenv()


# Проверка переменных окружения
YANDEX_ACCESS_KEY_ID = os.getenv('YANDEX_ACCESS_KEY_ID')
YANDEX_SECRET_KEY = os.getenv('YANDEX_SECRET_KEY')
BUCKET_NAME = os.getenv('YANDEX_BUCKET_NAME')

if not all([YANDEX_ACCESS_KEY_ID, YANDEX_SECRET_KEY, BUCKET_NAME]):
    missing_vars = [var for var in ['YANDEX_ACCESS_KEY_ID',
                                    'YANDEX_SECRET_KEY', 'YANDEX_BUCKET_NAME'] if not os.getenv(var)]
    print(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
    raise ValueError(
        f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")


def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.from_object(config_by_name['dev'])
    register_routes(app)
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={
                  r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    jwt.init_app(app)
    ma.init_app(app)

    return app
