from uuid import UUID
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from datetime import timedelta, datetime, UTC

from app.extensions import db, jwt
from app.models import User, TokenBlocklist
from app.services.user_service import create_user, update_user, save_image
from app.schemas import UserSchema  # Import the UserSchema

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    avatar_file = request.files.get('avatar')

    if not name or not email or not password:
        return jsonify({'msg': 'Заполните все поля'}), 400

    avatar_url = save_image(
        avatar_file, 'avatar') if avatar_file else "/static/avatars/default.png"

    try:
        user = create_user(name=name, email=email,
                           password=password, avatar=avatar_url)
        user.is_online = True
        if avatar_file:
            new_avatar_url = save_image(avatar_file, 'avatar', user_id=user.id)
            user.avatar = new_avatar_url
            db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'msg': 'Пользователь с таким именем или email уже существует'}), 409

    access_token = create_access_token(identity=str(
        user.id), expires_delta=timedelta(minutes=30))
    refresh_token = create_refresh_token(identity=str(user.id))

    user_schema = UserSchema(only=('id', 'name', 'email', 'avatar'))
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user_schema.dump(user)
    }, 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'msg': 'Введите email и пароль'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'msg': 'Пользователь не найден'}), 404

    if not check_password_hash(user.password_hash, password):
        return jsonify({'msg': 'Неверный пароль'}), 401

    if user.is_banned and (user.ban_until is None or user.ban_until > datetime.now(UTC)):
        return jsonify({'msg': 'Аккаунт заблокирован'}), 403
    user.is_online = True

    access_token = create_access_token(identity=str(
        user.id), expires_delta=timedelta(minutes=30))
    refresh_token = create_refresh_token(identity=str(user.id))
    db.session.add(user)
    db.session.commit()
    user_schema = UserSchema(only=('id', 'name', 'email', 'avatar', 'is_online', 'registration_date'))
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user_schema.dump(user)
    }, 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = update_user(user_id, last_online=datetime.now(UTC))
    if not user:
        return jsonify({'msg': 'Пользователь не найден'}), 404

    new_access_token = create_access_token(identity=str(
        user_id), expires_delta=timedelta(minutes=30))

    user_schema = UserSchema(only=('id', 'name', 'email', 'avatar'))
    return {
        'access_token': new_access_token,
        'user': user_schema.dump(user)
    }, 200


@jwt.token_in_blocklist_loader
def is_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = db.session.query(TokenBlocklist).filter_by(jti=jti).first()
    return token is not None


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    token_type = get_jwt()["type"]
    user_id = get_jwt_identity()
    user = User.query.get(UUID(user_id))
    user.is_online = False

    expires = datetime.fromtimestamp(get_jwt()["exp"], tz=UTC)
    blocked_token = TokenBlocklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires=expires
    )
    db.session.add(user)
    db.session.add(blocked_token)
    db.session.commit()

    return {"msg": "Токен успешно отозван"}, 200
