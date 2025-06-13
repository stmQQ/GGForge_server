from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID
from flask_login import UserMixin
import uuid
from sqlalchemy.sql import func


mutual_friend_association = db.Table(
    'mutual_friend_association',
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id')),
    db.Column('friend_id', UUID(as_uuid=True), db.ForeignKey('users.id'))
)


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(256), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(128))
    registration_date = db.Column(
        db.Date, nullable=False, default=func.current_date())
    last_online = db.Column(db.DateTime, nullable=False, onupdate=func.now())
    is_online = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    ban_until = db.Column(db.DateTime)

    friends = db.relationship(
        'User', secondary=mutual_friend_association,
        primaryjoin=id == mutual_friend_association.c.user_id,
        secondaryjoin=id == mutual_friend_association.c.friend_id,
        backref='friends_back'
    )

    game_accounts = db.relationship(
        'GameAccount', back_populates='user', lazy='selectin')
    connections = db.relationship(
        'Connection', back_populates='user', lazy='selectin')
    member_teams = db.relationship(
        'Team', secondary='team_members', back_populates='players')
    led_teams = db.relationship(
        'Team', back_populates='leader', foreign_keys='Team.leader_id')
    created_tournaments = db.relationship(
        'Tournament', back_populates='creator', lazy='selectin')
    achievements = db.relationship(
        'Achievement', secondary='user_achievements', back_populates='users', lazy='selectin')
    participated_tournaments = db.relationship(
        'Tournament', secondary='tournament_participants', back_populates='participants', lazy='selectin')
    groups = db.relationship('Group', secondary='group_users',
                             back_populates='participants', lazy='selectin')
    group_rows = db.relationship(
        'GroupRow', back_populates='user', lazy='selectin')
    prizetable_rows = db.relationship(
        'PrizeTableRow', back_populates='user', lazy='selectin')
    support_tokens = db.relationship(
        'SupportToken', back_populates='user', lazy='selectin')
    sent_requests = db.relationship('UserRequest',
                                    back_populates='from_user',
                                    foreign_keys='UserRequest.from_user_id',
                                    lazy='selectin')
    received_requests = db.relationship('UserRequest',
                                        back_populates='to_user',
                                        foreign_keys='UserRequest.to_user_id',
                                        lazy='selectin')


class GameAccount(db.Model):
    __tablename__ = 'game_accounts'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), nullable=False)
    user = db.relationship(
        'User', back_populates='game_accounts', lazy='selectin')

    game_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'games.id'), nullable=False)
    game = db.relationship(
        'Game', back_populates='game_accounts', lazy='selectin')

    connection_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'connections.id'), nullable=False)
    connection = db.relationship(
        'Connection', back_populates='game_account', uselist=False, lazy='joined')


class Connection(db.Model):
    __tablename__ = 'connections'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    service_name = db.Column(db.String(64), nullable=False)
    external_user_url = db.Column(db.String(256), nullable=True)

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), nullable=False)
    user = db.relationship('User', back_populates='connections')

    game_account = db.relationship(
        'GameAccount', back_populates='connection', uselist=False)


class SupportToken(db.Model):
    __tablename__ = 'support_tokens'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # theme = db.Column(db.String(64), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False, default='open')
    response = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=func.now())

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), nullable=False)
    user = db.relationship('User', back_populates='support_tokens')


class UserRequest(db.Model):
    __tablename__ = 'user_requests'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    type = db.Column(db.String(32), nullable=False)  # 'friend', 'team'
    # pending, accepted, declined
    status = db.Column(db.String(32), nullable=False, default='pending')

    # Только для приглашения в команду
    team_id = db.Column(UUID(as_uuid=True),
                        db.ForeignKey('teams.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(
        db.DateTime, default=func.now(), onupdate=func.now())

    from_user = db.relationship(
        'User', back_populates='sent_requests', foreign_keys=[from_user_id])
    to_user = db.relationship(
        'User', back_populates='received_requests', foreign_keys=[to_user_id])
    team = db.relationship(
        'Team', back_populates='requests', foreign_keys=[team_id])


class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    # "access" or "refresh"
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    expires = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", lazy="joined")
