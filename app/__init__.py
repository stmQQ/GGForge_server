import os
import boto3

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

# Настройка Yandex Cloud Object Storage
session = boto3.session.Session()
s3_client = session.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=YANDEX_ACCESS_KEY_ID,
    aws_secret_access_key=YANDEX_SECRET_KEY
)


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

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Возвращает редирект на публичный URL файла в Yandex Object Storage."""
        try:
            # Проверяем существование файла в бакете
            s3_client.head_object(Bucket=BUCKET_NAME, Key=filename)
            # Формируем публичный URL
            file_url = f"https://{BUCKET_NAME}.storage.yandexcloud.net/{filename}"
            print(f"Редирект на файл: {file_url}")
            response = make_response(redirect(file_url))
            # Кэширование на 1 год
            response.headers['Cache-Control'] = 'public, max-age=31536000'
            return response
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"Файл не найден: {filename}")
                return {'error': f'Файл не найден: {filename}'}, 404
            print(f"Ошибка Yandex Cloud: {str(e)}")
            return {'error': f'Ошибка хранилища: {str(e)}'}, 500
        except Exception as e:
            print(f"Общая ошибка: {str(e)}")
            return {'error': f'Неожиданная ошибка: {str(e)}'}, 500

    return app
