import os
from flask import Flask, jsonify, request
from .extensions import db, migrate, cors, jwt, ma
from .config import config_by_name
from .routes import register_routes
from .apscheduler_tasks import init_scheduler
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
    # Используем prod для Render
    app.config.from_object(config_by_name['prod'])

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "allow_headers": ["Content-Type", "X-Timezone", "Authorization"]
        }
    })
    jwt.init_app(app)
    ma.init_app(app)
    register_routes(app)

    # Инициализация APScheduler
    if not app.config.get('TESTING'):
        init_scheduler(app)

    @app.route('/api/ping', methods=['GET', 'OPTIONS'])
    def ping():
        if request.method == 'OPTIONS':
            return '', 204
        return jsonify({'status': 'ok'}), 200

    return app


app = create_app()
