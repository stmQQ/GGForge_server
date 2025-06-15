import os
from pyuploadcare import Uploadcare

from flask import Flask, make_response, redirect
from .extensions import db, migrate, cors, jwt, ma
from .config import config_by_name
from .models import *
from .routes import register_routes
# from apscheduler_tasks import register_scheduler

from dotenv import load_dotenv

load_dotenv()


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

    # Инициализация Uploadcare
    uploadcare = Uploadcare(
        public_key=os.getenv('UPLOADCARE_PUBLIC_KEY'),
        secret_key=os.getenv('UPLOADCARE_SECRET_KEY')
    )

    # Проксирование файлов
    @app.route('static/<path:filename>')
    def serve_static(filename):
        try:
            file_obj = uploadcare.file(filename)
            # Пример трансформации: сжатие и ресайз
            url = file_obj.cdn_url + '-/resize/300x300/-/quality/lightest/'
            response = make_response(redirect(url))
            response.headers['Cache-Control'] = 'public, max-age=31536000'
            return response
        except Exception as e:
            return {'error': f'Файл не найден: {str(e)}'}, 404
    return app
