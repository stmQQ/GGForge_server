from flask import Flask
from .extensions import db, migrate, cors, jwt, ma
from .config import config_by_name
from .models import *
from .routes import register_routes
# from apscheduler_tasks import register_scheduler


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
