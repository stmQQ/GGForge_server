from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Team, User
from app.models.user_models import UserRequest
from app.services.team_service import (
    create_team, update_team, delete_team, get_team, get_teams, get_team_members,
    invite_user_to_team, accept_team_invite, decline_team_invite, leave_team,
    kick_member, get_user_team_invites
)
from app.schemas import TeamSchema, UserRequestSchema, UserSchema
from app.services.user_service import save_image

team_bp = Blueprint('team_bp', __name__, url_prefix='/api/teams')


def is_team_leader_or_admin(team_id: UUID):
    """Check if the current user is the team leader or an admin."""
    user_id = get_jwt_identity()
    try:
        user_id_uuid = UUID(user_id)
    except ValueError:
        return jsonify({'msg': 'Некорректный формат user_id'}), 400

    user = User.query.get(user_id_uuid)
    team = Team.query.get(team_id)
    if not user or not team:
        return jsonify({'msg': 'Пользователь или команда не найдены'}), 404
    if not user.is_admin and team.leader_id != user_id_uuid:
        return jsonify({'msg': 'Требуются права администратора или лидера команды'}), 403
    return None


@team_bp.route('/', methods=['POST', 'OPTIONS'])
def create_team_route():
    """Create a new team."""
    if request.method == 'OPTIONS':
        return '', 204

    @jwt_required()
    def handle_post():
        user_id = get_jwt_identity()
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            return jsonify({'msg': 'Некорректный формат user_id'}), 400

        user = User.query.get(user_id_uuid)
        if not user:
            return jsonify({'msg': 'Пользователь не найден'}), 404

        # Обработка multipart/form-data
        title = request.form.get('title')
        description = request.form.get('description')
        logo_file = request.files.get('logo_path')

        if not title:
            return jsonify({'msg': 'Необходимо указать title'}), 400

        logo_path = None
        if logo_file:
            try:
                logo_path = save_image(
                    logo_file, 'team_logo', user_id=user_id_uuid)
            except ValueError as e:
                return jsonify({'msg': str(e)}), 400

        try:
            team = create_team(
                title=title,
                description=description,
                logo_path=logo_path
            )
            db.session.commit()
            team_schema = TeamSchema(
                only=('id', 'title', 'description', 'leader_id', 'logo_path'))
            return jsonify({
                'msg': 'Команда успешно создана',
                'team': team_schema.dump(team)
            }), 201
        except ValueError as e:
            return jsonify({'msg': str(e)}), 400
        except IntegrityError:
            db.session.rollback()
            return jsonify({'msg': 'Команда с таким названием уже существует'}), 409

    return handle_post()


@team_bp.route('/', methods=['GET', 'OPTIONS'])
def get_teams_route():
    """Get a paginated list of all teams."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        if page < 1 or per_page < 1:
            raise ValueError("Параметры пагинации должны быть положительными")
        teams = get_teams(page=page, per_page=per_page)
        teams_schema = TeamSchema(many=True,
                                  only=('id', 'title', 'description', 'leader_id', 'logo_path'))
        return jsonify(teams_schema.dump(teams)), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except Exception as e:
        return jsonify({'msg': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@team_bp.route('/<uuid:team_id>', methods=['GET'])
def get_team_route(team_id: UUID):
    """Get details of a specific team."""
    try:
        team = get_team(team_id)
        team_schema = TeamSchema(
            only=('id', 'title', 'description', 'leader_id', 'logo_path', 'players'))
        return jsonify(team_schema.dump(team)), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 404


@team_bp.route('/<uuid:team_id>', methods=['PATCH'])
@jwt_required()
def update_team_route(team_id: UUID):
    """Update team information."""
    auth_check = is_team_leader_or_admin(team_id)
    if auth_check:
        return auth_check

    data = request.get_json()
    if not data:
        return jsonify({'msg': 'Отсутствуют данные'}), 400

    try:
        team = update_team(
            team_id=team_id,
            title=data.get('title'),
            description=data.get('description'),
            logo_path=data.get('logo_path')
        )
        db.session.commit()
        team_schema = TeamSchema(
            only=('id', 'title', 'description', 'leader_id', 'logo_path'))
        return jsonify({
            'msg': 'Команда успешно обновлена',
            'team': team_schema.dump(team)
        }), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except PermissionError as e:
        return jsonify({'msg': str(e)}), 403
    except IntegrityError:
        db.session.rollback()
        return jsonify({'msg': 'Команда с таким названием уже существует'}), 409


@team_bp.route('/<uuid:team_id>', methods=['DELETE'])
@jwt_required()
def delete_team_route(team_id: UUID):
    """Delete a team."""
    auth_check = is_team_leader_or_admin(team_id)
    if auth_check:
        return auth_check

    try:
        delete_team(team_id)
        db.session.commit()
        return jsonify({'msg': 'Команда успешно удалена'}), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 404
    except PermissionError as e:
        return jsonify({'msg': str(e)}), 403


@team_bp.route('/<uuid:team_id>/invite', methods=['POST'])
@jwt_required()
def invite_user_route(team_id: UUID):
    """Invite a user to a team."""
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'msg': 'Необходимо указать user_id'}), 400

    try:
        to_user_id = UUID(data['user_id'])
        request_obj = invite_user_to_team(
            to_user_id=to_user_id, team_id=team_id)
        db.session.commit()
        request_schema = UserRequestSchema(
            only=('id', 'from_user_id', 'to_user_id', 'team_id', 'status'))
        return jsonify({
            'msg': 'Приглашение успешно отправлено',
            'request': request_schema.dump(request_obj)
        }), 201
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except PermissionError as e:
        return jsonify({'msg': str(e)}), 403


@team_bp.route('/invites/<uuid:request_id>/accept', methods=['POST'])
@jwt_required()
def accept_invite_route(request_id: UUID):
    """Accept a team invitation."""
    try:
        team = accept_team_invite(request_id)
        db.session.commit()
        team_schema = TeamSchema(only=('id', 'title', 'leader_id', 'players'))
        return jsonify({
            'msg': 'Приглашение успешно принято',
            'team': team_schema.dump(team)
        }), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400


@team_bp.route('/invites/<uuid:request_id>/decline', methods=['POST'])
@jwt_required()
def decline_invite_route(request_id: UUID):
    """Decline a team invitation."""
    try:
        decline_team_invite(request_id)
        db.session.commit()
        return jsonify({'msg': 'Приглашение успешно отклонено'}), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400


@team_bp.route('/<uuid:team_id>/leave', methods=['POST'])
@jwt_required()
def leave_team_route(team_id: UUID):
    """Leave a team."""
    try:
        leave_team(team_id)
        db.session.commit()
        return jsonify({'msg': 'Вы успешно покинули команду'}), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except PermissionError as e:
        return jsonify({'msg': str(e)}), 403


@team_bp.route('/<uuid:team_id>/kick', methods=['POST'])
@jwt_required()
def kick_member_route(team_id: UUID):
    """Kick a member from a team."""
    auth_check = is_team_leader_or_admin(team_id)
    if auth_check:
        return auth_check

    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'msg': 'Необходимо указать user_id'}), 400

    try:
        user_to_kick_id = UUID(data['user_id'])
        kick_member(team_id, user_to_kick_id)
        db.session.commit()
        return jsonify({'msg': 'Участник успешно исключён'}), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except PermissionError as e:
        return jsonify({'msg': str(e)}), 403


@team_bp.route('/<uuid:team_id>/members', methods=['GET'])
def get_team_members_route(team_id: UUID):
    """Get the list of team members."""
    try:
        members = get_team_members(team_id)
        user_schema = UserSchema(many=True, only=('id', 'name'))
        return jsonify(user_schema.dump(members)), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 404


@team_bp.route('/invites', methods=['GET'])
@jwt_required()
def get_user_invites_route():
    """Get all pending team invitations for the current user."""
    try:
        invites = get_user_team_invites()
        requests_schema = UserRequestSchema(many=True,
                                            only=('id', 'from_user_id', 'to_user_id', 'team_id', 'status'))
        return jsonify(requests_schema.dump(invites)), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400


@team_bp.route('/me', methods=['GET'])
@jwt_required()
def list_user_teams():
    """Get all teams where the current user is a member or leader."""
    user_id = get_jwt_identity()
    try:
        user_id_uuid = UUID(user_id)
    except ValueError:
        return jsonify({'msg': 'Некорректный формат user_id'}), 400

    user = User.query.get(user_id_uuid)
    if not user:
        return jsonify({'msg': 'Пользователь не найден'}), 404

    teams_schema = TeamSchema(many=True, only=(
        'id', 'title', 'description', 'logo_path', 'leader_id'))
    return jsonify({"member_teams": teams_schema.dump(user.member_teams)}, {"led_teams": teams_schema.dump(user.led_teams)}), 200


@team_bp.route('/invites/incoming', methods=['GET'])
@jwt_required()
def list_incoming_team_invites():
    """Get all pending team invitations where the current user is the recipient."""
    user_id = get_jwt_identity()
    try:
        user_id_uuid = UUID(user_id)
    except ValueError:
        return jsonify({'msg': 'Некорректный формат user_id'}), 400

    user = User.query.get(user_id_uuid)
    if not user:
        return jsonify({'msg': 'Пользователь не найден'}), 404

    invites = UserRequest.query.filter(
        UserRequest.to_user_id == user_id_uuid,
        UserRequest.type == 'team',
        UserRequest.status == 'pending'
    ).all()

    invites_schema = UserRequestSchema(many=True, only=(
        'id', 'from_user_id', 'to_user_id', 'team_id', 'status'))
    return jsonify(invites_schema.dump(invites)), 200
