from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.extensions import db
from app.models import User
from app.services.game_service import (
    get_all_games, get_game, create_game, delete_game,
    create_achievement, assign_achievement_to_user, get_user_achievements
)
from app.schemas import GameSchema, AchievementSchema, UserSchema

game_bp = Blueprint('game', __name__, url_prefix='/api/games')


def is_admin_user():
    """Check if the current user is an admin."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.is_admin:
        return jsonify({'msg': 'Требуются права администратора'}), 403
    return None


@game_bp.route('/', methods=['GET', 'OPTIONS'])
def get_games():
    """Retrieve all games."""
    if request.method == 'OPTIONS':
        return '', 204
    games = get_all_games()
    game_schema = GameSchema(many=True, only=(
        'id', 'title', 'image_path', 'logo_path', 'service_name'))
    print(game_schema.dump(games))
    return game_schema.dump(games), 200


@game_bp.route('/', methods=['POST'])
@jwt_required()
def add_game():
    """Create a new game (admin-only)."""
    admin_check = is_admin_user()
    if admin_check:
        return admin_check

    data = request.get_json()
    title = data.get('title')
    image_path = data.get('image_path')
    logo_path = data.get('logo_path')
    service_name = data.get('service_name')

    try:
        game = create_game(
            title=title,
            image_path=image_path,
            logo_path=logo_path,
            service_name=service_name
        )
        game_schema = GameSchema(
            only=('id', 'title', 'image_path', 'logo_path', 'service_name'))
        return {
            'msg': 'Игра успешно создана',
            'game': game_schema.dump(game)
        }, 201
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except IntegrityError:
        return jsonify({'msg': 'Игра с таким названием уже существует'}), 409


@game_bp.route('/<uuid:game_id>', methods=['GET', 'OPTIONS'])
def get_game_route(game_id: UUID):
    """Retrieve a specific game by ID."""
    if request.method == 'OPTIONS':
        return '', 204
    game = get_game(game_id)
    game_schema = GameSchema()
    return game_schema.dump(game), 200


@game_bp.route('/<uuid:game_id>', methods=['DELETE'])
@jwt_required()
def delete_game_route(game_id: UUID):
    """Delete a game by ID (admin-only)."""
    admin_check = is_admin_user()
    if admin_check:
        return admin_check

    try:
        delete_game(game_id)
        return {'msg': 'Игра успешно удалена'}, 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400


@game_bp.route('/<uuid:game_id>/achievements', methods=['POST'])
@jwt_required()
def add_achievement(game_id: UUID):
    """Create a new achievement for a game (admin-only)."""
    admin_check = is_admin_user()
    if admin_check:
        return admin_check

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    image_path = data.get('image_path')

    try:
        achievement = create_achievement(
            game_id=game_id,
            title=title,
            description=description,
            image_path=image_path
        )
        achievement_schema = AchievementSchema(
            only=('id', 'title', 'description', 'image_path', 'game_id'))
        return {
            'msg': 'Достижение успешно создано',
            'achievement': achievement_schema.dump(achievement)
        }, 201
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except IntegrityError:
        return jsonify({'msg': 'Достижение с таким названием уже существует для этой игры'}), 409


@game_bp.route('/achievements/<uuid:achievement_id>/assign', methods=['POST'])
@jwt_required()
def assign_achievement(achievement_id: UUID):
    """Assign an achievement to a user (admin-only)."""
    admin_check = is_admin_user()
    if admin_check:
        return admin_check

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'msg': 'Необходимо указать user_id'}), 400

    try:
        achievement = assign_achievement_to_user(achievement_id, user_id)
        achievement_schema = AchievementSchema(
            only=('id', 'title', 'description', 'image_path', 'game_id'))
        return {
            'msg': 'Достижение успешно назначено',
            'achievement': achievement_schema.dump(achievement)
        }, 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400


@game_bp.route('/users/<uuid:user_id>/achievements', methods=['GET'])
def get_user_achievements_route(user_id: UUID):
    """Retrieve all achievements for a user."""
    try:
        achievements = get_user_achievements(user_id)
        achievement_schema = AchievementSchema(many=True, only=(
            'id', 'title', 'description', 'image_path', 'game.title'))
        return achievement_schema.dump(achievements), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 404
