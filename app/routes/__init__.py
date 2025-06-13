from .auth_routes import auth_bp
from .user_routes import user_bp
# from .match_routes import match_bp
from .tournament_routes import tournament_bp
from .game_routes import game_bp
# from .admin_routes import admin_bp
# from .common_routes import common_bp
from .team_routes import team_bp


def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(tournament_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(team_bp)
