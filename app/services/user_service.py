import os
import tempfile
import traceback
import uuid

from flask import current_app
from app.models.game_models import Game
from app.models.user_models import User, Connection, GameAccount, UserRequest, TokenBlocklist, SupportToken
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from datetime import datetime, timedelta, UTC
from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID

from pyuploadcare import Uploadcare
from dotenv import load_dotenv

load_dotenv()


# region User operations

def create_user(name, email, password, avatar="default", is_admin=False):
    """Создает нового пользователя"""
    user: User = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        avatar=avatar,
        is_admin=is_admin,
        last_online=datetime.now(UTC),
        is_banned=False,
        ban_until=None
    )
    db.session.add(user)
    db.session.commit()
    return user


def update_user(user_id, name=None, email=None, password=None, avatar=None, last_online=None):
    """Обновляет данные пользователя"""
    user = User.query.get(user_id)
    if not user:
        return None

    if name:
        user.name = name.strip()
    if email:
        user.email = email.strip().lower()
    if password:
        user.password_hash = generate_password_hash(password)
    if avatar:
        user.avatar = avatar
    if last_online:
        user.last_online = last_online

    db.session.commit()
    return user


def delete_user(user_id):
    """Удаляет пользователя"""
    user = User.query.get(user_id)
    if not user:
        return None
    db.session.delete(user)
    db.session.commit()
    return True


def get_user_profile(user_id):
    """Возвращает информацию о пользователе (без пароля)"""
    user = User.query.get(user_id)

    if not user:
        return None  # Пользователь не найден

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": user.avatar,
        "is_admin": user.is_admin,
        "is_banned": user.is_banned,
        "ban_until": user.ban_until,
    }


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE_MB = 2


def allowed_file(filename):
    """Проверяет, допустимое ли расширение файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_storage: FileStorage, image_type: str, entity_id=None):
    """Сохраняет изображение в Uploadcare с проверками."""
    # Проверка типа file_storage
    if not isinstance(file_storage, FileStorage):
        error_msg = f'Неверный тип file_storage: ожидается FileStorage, получен {type(file_storage)}'
        print(error_msg)
        raise ValueError(error_msg)

    if not file_storage or not file_storage.filename:
        raise ValueError('Файл не предоставлен')

    # Проверка расширения
    if not allowed_file(file_storage.filename):
        raise ValueError('Недопустимый формат файла')

    # Проверка размера
    file_storage.seek(0, os.SEEK_END)
    file_size_mb = file_storage.tell() / (1024 * 1024)
    file_storage.seek(0)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError('Файл слишком большой. Максимальный размер — 2MB')

    # Определение поддиректории
    base_path = 'static'
    sub_path = {
        'avatar': f'avatars/{entity_id}' if entity_id else 'avatars',
        'team_logo': f'team_logos/{entity_id}' if entity_id else 'team_logos',
        'tournament': f'tournaments/{entity_id}' if entity_id else 'tournaments',
        'general': 'general',
        'game_image': 'games/images',
        'game_logo': 'games/logos',
    }.get(image_type)
    if not sub_path:
        raise ValueError('Недопустимый тип изображения')

    # Формирование имени файла
    ext = os.path.splitext(secure_filename(file_storage.filename))[1]
    filename = f"{uuid.uuid4().hex}{ext}"

    # Формирование пути для Uploadcare
    storage_path = f"{sub_path}/{filename}"

    # Инициализация Uploadcare
    uploadcare = Uploadcare(
        public_key=os.getenv('UPLOADCARE_PUBLIC_KEY'),
        secret_key=os.getenv('UPLOADCARE_SECRET_KEY')
    )

    # Сохранение во временный файл и загрузка
    try:
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            file_storage.save(temp_file.name)
            temp_file_path = temp_file.name
            print(f"Saved temp file at: {temp_file_path}")

        # Открываем временный файл для чтения
        with open(temp_file_path, 'rb') as f:
            print(f"File stream type: {type(f)}")
            uploaded_file = uploadcare.upload(
                f, store=True)

        # Удаляем временный файл
        os.unlink(temp_file_path)
        print(f"Deleted temp file: {temp_file_path}")

    except Exception as e:
        # Удаляем временный файл, если он существует
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
                print(f"Deleted temp file on error: {temp_file_path}")
            except:
                pass
        # Выводим стек ошибки
        error_trace = ''.join(traceback.format_exc())
        print(f"Uploadcare error: {str(e)}\nStack trace:\n{error_trace}")
        raise ValueError(
            f'Ошибка загрузки в Uploadcare: {str(e)}\nStack trace:\n{error_trace}')

    return f"{base_path}/{storage_path}"


def delete_image(image_path):
    """Удаляет изображение, если оно не дефолтное.

    Args:
        image_path: Путь к файлу (например, '/static/avatars/<user_id>/<uuid>.jpg').
    """
    if not image_path or any(default in image_path for default in ['default.png', 'games/images', 'games/logos']):
        return  # Нельзя удалять дефолтные изображения

    full_path = os.path.join(current_app.root_path, image_path.lstrip("/"))
    if os.path.exists(full_path):
        os.remove(full_path)


# endregion


# region Administrating and support

def get_all_users():
    """Возвращает список всех пользователей"""
    return User.query.all()


def ban_user(user_id, ban_hours=None):
    """Банит пользователя на определенное количество дней (если не указано, бан перманентный)"""
    user = User.query.get(user_id)
    if not user:
        return None  # Пользователь не найден

    user.is_banned = True
    user.ban_until = ban_hours if ban_hours else None

    db.session.commit()
    return user  # Возвращаем обновленного пользователя


def unban_user(user_id):
    """Разбанивает пользователя"""
    user = User.query.get(user_id)
    if not user:
        return None  # Пользователь не найден

    user.is_banned = False
    user.ban_until = None  # Обнуляем время бана

    db.session.commit()
    return user  # Возвращаем обновленного пользователя


def create_support_ticket(user_id, theme, text):
    """Создает запрос в поддержку"""
    if not text.strip():
        return None  # Сообщение не может быть пустым

    ticket = SupportToken(user_id=user_id,
                          text=text, status="open")
    db.session.add(ticket)
    db.session.commit()

    return ticket


def get_all_tickets():
    """Возвращает список всех тикетов"""
    return SupportToken.query.all()


def get_user_tickets(user_id):
    """Возвращает список тикетов пользователя"""
    return SupportToken.query.filter_by(user_id=user_id).all()


def update_ticket_status(ticket_id, status):
    """Обновляет статус тикета в поддержку (open, in_progress, closed)"""
    ticket = SupportToken.query.get(ticket_id)

    if not ticket:
        return None  # Тикет не найден

    if status not in ["open", "in_progress", "closed"]:
        return None  # Некорректный статус

    ticket.status = status
    db.session.commit()

    return ticket


def respond_to_ticket(ticket_id, response):
    """Добавляет ответ администратора в тикет"""
    ticket = SupportToken.query.get(ticket_id)

    if not ticket or ticket.status == "closed":
        return None  # Тикет не найден или уже закрыт

    ticket.response = response
    ticket.status = "closed"  # Меняем статус, если он еще открыт
    db.session.commit()

    return ticket

# endregion

# region Friendship system

# def send_friend_request(sender_id, receiver_id):
#     """Отправка запроса в друзья"""
#     sender = User.query.get(sender_id)
#     receiver = User.query.get(receiver_id)
#     request = UserRequest(from_user=sender, to_user=receiver, type='friend', status="pending")
#     db.session.add(request)
#     db.session.commit()
#     return request


# def accept_friend_request(request_id):
#     """Принятие заявки в друзья"""
#     friend_request = UserRequest.query.get(request_id)

#     if not friend_request or friend_request.status != "pending":
#         return None  # Запрос не найден или уже обработан

#     # Обновляем статус запроса
#     friend_request.status = "accepted"
#     #TODO FIX METHOD
#     # Добавляем запись в список друзей (если нужно)
#     friendship1 = Friendship(user_id=friend_request.sender_id, friend_id=friend_request.receiver_id)
#     friendship2 = Friendship(user_id=friend_request.receiver_id, friend_id=friend_request.sender_id)

#     db.session.add(friendship1)
#     db.session.add(friendship2)
#     db.session.commit()

#     return friend_request


# def reject_friend_request(request_id):
#     """Отклонение заявки в друзья"""
#     friend_request = UserRequest.query.get(request_id)

#     if not friend_request or friend_request.status != "pending":
#         return None  # Запрос не найден или уже обработан

#     friend_request.status = "rejected"
#     db.session.commit()

#     return friend_request


# def get_pending_friend_requests(user_id):
#     """Получение списка входящих заявок"""
#     return UserRequest.query.filter_by(to_user_id=user_id, status="pending").all()


# def remove_friend(user_id, friend_id):
#     """Удаляет пользователя из списка друзей"""
#     friendship1 = Friendship.query.filter_by(user_id=user_id, friend_id=friend_id).first()
#     friendship2 = Friendship.query.filter_by(user_id=friend_id, friend_id=user_id).first()

#     if not friendship1 or not friendship2:
#         return None  # Дружбы нет

#     db.session.delete(friendship1)
#     db.session.delete(friendship2)
#     db.session.commit()

#     return True


# def get_friends(user_id):
#     """Возвращает список друзей пользователя"""
#     friendships = Friendship.query.filter_by(user_id=user_id).all()
#     friend_ids = [friendship.friend_id for friendship in friendships]

#     friends = User.query.filter(User.id.in_(friend_ids)).all()
#     return friends

# endregion

# region Connections to external API

def get_or_create_connection(service_name: str, profile_url: str, user: User):
    connection = Connection.query.filter_by(
        service_name=service_name,
        external_user_url=profile_url
    ).first()

    if connection is None:
        connection = Connection(
            service_name=service_name,
            external_user_url=profile_url,
            user=user
        )
        db.session.add(connection)
        db.session.flush()  # Чтобы получить connection.id

    return connection


def create_game_account_if_absent(user_id: UUID, connection_id: UUID, game_id: UUID, service_name: str, external_url):
    account = GameAccount.query.filter_by(
        user_id=user_id,
        connection_id=connection_id
    ).first()

    if account is None:
        user = User.query.get(user_id)
        game = Game.query.get(game_id)
        connection = get_or_create_connection(
            service_name=service_name, profile_url=external_url, user=user)
        account = GameAccount(
            user=user,
            game=game,
            connection=connection
        )
        db.session.add(account)
        db.session.commit()

    return account


def unlink_game_account(game_account_id, user_id):
    """
    Unlink a game account and its connection if unused.
    Raises:
        ValueError: If the game account or connection is not found.
        PermissionError: If the user does not own the account.
    """
    # Проверяем существование аккаунта
    account = GameAccount.query.get(game_account_id)
    if not account:
        raise ValueError('Игровой аккаунт не найден')

    # Проверяем, принадлежит ли аккаунт текущему пользователю
    if account.user_id != user_id:
        raise PermissionError('Нет прав для удаления этого аккаунта')

    # Удаляем аккаунт
    db.session.delete(account)

    # Проверяем, остались ли другие аккаунты с этим connection_id
    count = GameAccount.query.filter_by(
        connection_id=account.connection_id).count()
    if count == 0:
        conn = Connection.query.get(account.connection_id)
        if conn:
            db.session.delete(conn)
        else:
            raise ValueError('Соединение не найдено')

    db.session.commit()
    return 'Игровой аккаунт успешно удалён'


def remove_expired_tokens():
    now = datetime.now(UTC)
    deleted = TokenBlocklist.query.filter(
        TokenBlocklist.expires < now).delete()
    db.session.commit()
    print(f"[Auto-clean] Удалено {deleted} просроченных токенов")
