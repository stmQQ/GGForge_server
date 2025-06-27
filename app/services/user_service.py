from io import BytesIO
import os
import tempfile
import traceback
import uuid
import boto3

from flask import current_app
from app.models.game_models import Game
from app.models.user_models import User, Connection, GameAccount, UserRequest, TokenBlocklist, SupportToken
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from datetime import datetime, timedelta, UTC
from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID

from dotenv import load_dotenv


load_dotenv()

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


# print(BUCKET_NAME)


def allowed_file(filename):
    """Проверяет, допустимое ли расширение файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_storage: FileStorage, image_type: str, entity_id=None):
    """Сохраняет изображение в Yandex Object Storage и возвращает полный URL."""
    # Проверка типа file_storage
    if not isinstance(file_storage, FileStorage):
        print(
            f"Неверный тип file_storage: ожидается FileStorage, получен {type(file_storage)}")
        raise ValueError(
            f"Неверный тип file_storage: ожидается FileStorage, получен {type(file_storage)}")

    if not file_storage:
        print("Файл не предоставлен")
        raise ValueError('Файл не предоставлен')

    # Проверка расширения
    if not allowed_file(file_storage.filename):
        print(f"Недопустимый формат файла: {file_storage.filename}")
        raise ValueError('Недопустимый формат файла')

    # Проверка размера
    file_storage.seek(0, os.SEEK_END)
    file_size_mb = file_storage.tell() / (1024 * 1024)
    file_storage.seek(0)
    if file_size_mb > MAX_FILE_SIZE_MB:
        print(
            f"Файл слишком большой: {file_size_mb} MB, максимум {MAX_FILE_SIZE_MB} MB")
        raise ValueError(
            f"Файл слишком большой. Максимальный размер — {MAX_FILE_SIZE_MB}MB")

    # Определение поддиректории
    sub_path = {
        'avatar': f'avatars/{entity_id}' if entity_id else 'avatars',
        'team_logo': f'team_logos/{entity_id}' if entity_id else 'team_logos',
        'tournament': f'tournaments/{entity_id}' if entity_id else 'tournaments',
        'general': 'general',
        'game_image': 'games/images',
        'game_logo': 'games/logos',
    }.get(image_type)
    if not sub_path:
        print(f"Недопустимый тип изображения: {image_type}")
        raise ValueError('Недопустимый тип изображения')

    # Формирование имени файла
    ext = os.path.splitext(secure_filename(file_storage.filename))[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    storage_path = f"{sub_path}/{filename}"

    # Загрузка файла
    try:
        print(
            f"Загрузка файла: type={type(file_storage)}, filename={file_storage.filename}, storage_path={storage_path}")
        s3_client.upload_fileobj(
            file_storage,
            BUCKET_NAME,
            storage_path,
            ExtraArgs={'ACL': 'public-read'}  # Делаем файл публичным
        )
        file_url = f"https://{BUCKET_NAME}.storage.yandexcloud.net/{storage_path}"
        print(f"Файл успешно загружен: {file_url}")
        return file_url  # Возвращаем полный URL
    except Exception as e:
        error_trace = ''.join(traceback.format_exc())
        print(f"Yandex Cloud error: {str(e)}\nStack trace:\n{error_trace}")
        raise ValueError(
            f"Ошибка загрузки в Yandex Cloud: {str(e)}\n{error_trace}")


def delete_image(image_url):
    """Удаляет изображение из Yandex Object Storage, если оно не дефолтное.

    Args:
        image_url: Полный URL файла (например, 'https://<bucket>.storage.yandexcloud.net/avatars/<user_id>/<uuid>.jpg').
    """
    if not image_url or any(default in image_url for default in ['default.png', 'games/images', 'games/logos']):
        print(f"Пропуск удаления: {image_url} является дефолтным или пустым")
        return  # Нельзя удалять дефолтные изображения

    # Извлекаем ключ объекта из URL
    try:
        object_key = image_url.split(
            f"https://{BUCKET_NAME}.storage.yandexcloud.net/")[-1]
    except IndexError:
        print(f"Некорректный URL: {image_url}")
        return

    try:
        # Проверяем существование файла
        s3_client.head_object(Bucket=BUCKET_NAME, Key=object_key)
        # Удаляем файл
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_key)
        print(f"Файл успешно удален: {object_key}")
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"Файл не найден в бакете: {object_key}")
        else:
            print(f"Ошибка удаления в Yandex Cloud: {str(e)}")
    except Exception as e:
        print(f"Общая ошибка при удалении: {str(e)}")

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
