import uuid
from app.models import Match, PlayoffStageMatch, Map
from app.extensions import db
from marshmallow import fields, post_dump, validate
from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields
from .models import *


class AchievementSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Achievement
        load_instance = True
        include_fk = True
        include_relationships = True


class GameSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Game
        load_instance = True
        include_relationships = True

        achievements = fields.List(fields.Nested(
            AchievementSchema(only=('id', 'title'))))


class ConnectionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Connection
        include_fk = True
        load_instance = True
        include_relationships = True

    game_account = fields.Nested('GameAccountSchema', only=('id', 'game_id'))


class GameAccountSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = GameAccount
        include_fk = True
        load_instance = True

    user = fields.Nested('UserSchema', only=('id', 'name'))
    game = fields.Nested('GameSchema', only=('id', 'title', 'logo_path'))
    connection = fields.Nested(ConnectionSchema, only=(
        'id', 'service_name', 'external_user_url'))


class SupportTokenSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = SupportToken
        include_fk = True
        load_instance = True

    user = fields.Nested('UserSchema', only=('id', 'name'))


class UserRequestSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = UserRequest
        include_fk = True
        load_instance = True
        sqla_session = db.session

    id = fields.UUID()
    from_user_id = fields.UUID()
    to_user_id = fields.UUID()
    from_user = fields.Nested('UserSchema', only=('id', 'name'))
    to_user = fields.Nested('UserSchema', only=('id', 'name'))


class TokenBlocklistSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TokenBlocklist
        include_fk = True
        load_instance = True

    user = fields.Nested('UserSchema', only=('id', 'name'))


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True
        include_relationships = True
        load_instance = True

    friends = fields.List(fields.Nested(
        lambda: UserSchema(only=('id', 'name', 'avatar'))))
    game_accounts = fields.Nested(
        GameAccountSchema, many=True, only=('id', 'game_id', 'game.logo_path'))
    connections = fields.Nested(
        ConnectionSchema, many=True, only=('id', 'service_name', 'external_user_url'))
    member_teams = fields.List(fields.Nested(
        'TeamSchema', only=('id', 'title', 'logo_path')))
    led_teams = fields.List(fields.Nested(
        'TeamSchema', only=('id', 'title', 'logo_path')))
    created_tournaments = fields.List(fields.Nested(
        'TournamentSchema', only=('id', 'title', 'banner_url', 'status', 'start_time', 'prize_fund')))
    achievements = fields.List(fields.Nested(
        'AchievementSchema', only=('id', 'title')))
    participated_tournaments = fields.List(
        fields.Nested('TournamentSchema', only=('id', 'title', 'banner_url', 'status', 'start_time', 'prize_fund')))
    groups = fields.List(fields.Nested('GroupSchema', only=('id', 'letter')))
    group_rows = fields.List(fields.Nested('GroupRowSchema', only=('id',)))
    prizetable_rows = fields.List(fields.Nested(
        'PrizeTableRowSchema', only=('id',)))
    support_tokens = fields.Nested(SupportTokenSchema, many=True)
    sent_requests = fields.Nested(
        UserRequestSchema, many=True, only=('id', 'to_user', 'status'))
    received_requests = fields.Nested(
        UserRequestSchema, many=True, only=('id', 'from_user', 'status'))


class GroupRowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = GroupRow
        include_fk = True
        load_instance = True

    user = fields.Nested('UserSchema', only=(
        'id', 'name', 'avatar'), allow_none=True)
    team = fields.Nested('TeamSchema', only=(
        'id', 'title', 'logo_path'), allow_none=True)
    place = fields.Integer()  # Атрибут для сортировки


class GroupSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Group
        include_fk = True
        load_instance = True

    participants = fields.List(fields.Nested(
        'UserSchema', only=('id', 'name')))
    teams = fields.List(fields.Nested('TeamSchema', only=('id', 'title')))
    rows = fields.List(fields.Nested('GroupRowSchema'))
    matches = fields.List(fields.Nested('MatchSchema', exclude=('group',)))

    @post_dump
    def sort_rows_by_place(self, data, **kwargs):
        # Сортируем rows по атрибуту place
        if 'rows' in data:
            data['rows'] = sorted(
                data['rows'], key=lambda row: row.get('place', float('inf')))
        return data


class GroupStageSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = GroupStage
        include_fk = True
        load_instance = True

    groups = fields.List(fields.Nested(GroupSchema, only=(
        'id', 'letter', 'participants', 'teams', 'rows', 'matches')))


class PrizeTableRowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PrizeTableRow
        include_fk = True
        load_instance = True

    user = fields.Nested('UserSchema', only=(
        'id', 'name', 'avatar'), allow_none=True)
    team = fields.Nested('TeamSchema', only=(
        'id', 'title', 'logo_path'), allow_none=True)


class PrizeTableSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PrizeTable
        include_fk = True
        load_instance = True

    rows = fields.List(fields.Nested(PrizeTableRowSchema))


class PlayoffStageSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PlayoffStage
        include_fk = True
        load_instance = True

    playoff_matches = fields.List(fields.Nested(
        'PlayoffStageMatchSchema', only=('id', 'round_number', 'depends_on_match_1_id', 'depends_on_match_2_id', 'match')))


class TournamentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Tournament
        include_fk = True
        load_instance = True

    game = fields.Nested('GameSchema', only=('id', 'title'))
    creator = fields.Nested('UserSchema', only=('id', 'name', 'avatar'))
    participants = fields.List(fields.Nested(
        'UserSchema', only=('id', 'name', 'avatar')))
    teams = fields.List(fields.Nested('TeamSchema', only=('id', 'title')))
    matches = fields.List(fields.Nested('MatchSchema', only=('id', 'status')))
    group_stage = fields.Nested(GroupStageSchema, allow_none=True)
    playoff_stage = fields.Nested(PlayoffStageSchema, allow_none=True)
    prize_table = fields.Nested(PrizeTableSchema, allow_none=True)

    start_time = fields.DateTime(format='iso')


class TeamSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Team
        include_fk = True
        load_instance = True

    leader = fields.Nested('UserSchema', only=('id', 'name'))

    players = fields.List(fields.Nested('UserSchema', only=('id', 'name')))
    participated_tournaments = fields.List(
        fields.Nested('TournamentSchema', only=('id', 'title')))
    groups = fields.List(fields.Nested('GroupSchema', only=('id', 'letter')))
    group_rows = fields.List(fields.Nested(
        'GroupRowSchema', only=('id', 'place', 'wins', 'draws', 'loses')))
    prizetable_rows = fields.List(fields.Nested(
        'PrizeTableRowSchema', only=('id', 'place', 'prize')))
    requests = fields.List(fields.Nested(
        'UserRequestSchema', only=('id', 'status')))


ma = Marshmallow()


class MapSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Map
        load_instance = True
        sqla_session = db.session
        include_fk = True  # Включаем внешние ключи (match_id)

    id = fields.UUID(dump_default=uuid.uuid4)
    external_id = fields.Str(allow_none=True)
    winner_id = fields.UUID(allow_none=True)
    # match_id = fields.UUID(required=True)

    # Связь match сериализуем только как match_id, чтобы избежать рекурсии
    match = fields.Nested('MatchSchema', only=('id',), dump_only=True)


class PlayoffStageMatchSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PlayoffStageMatch
        load_instance = True
        sqla_session = db.session
        include_fk = True

    id = fields.UUID(dump_default=uuid.uuid4)
    round_number = fields.Str(required=True, validate=validate.Length(max=8))
    winner_to_match_id = fields.UUID(allow_none=True)
    loser_to_match_id = fields.UUID(allow_none=True)
    depends_on_match_1_id = fields.UUID(allow_none=True)
    depends_on_match_2_id = fields.UUID(allow_none=True)
    playoff_id = fields.UUID(allow_none=True)
    match_id = fields.UUID(required=True)

    # Сериализация связей
    match = fields.Nested('MatchSchema', exclude=(
        'playoff_match',), dump_only=True)
    playoff_stage = fields.Nested(
        'PlayoffStageSchema', only=('id',), dump_only=True)

    # Рекурсивные связи сериализуем только как ID, чтобы избежать бесконечной рекурсии
    winner_to_match = fields.Nested(
        'PlayoffStageMatchSchema', only=('id',), dump_only=True)
    loser_to_match = fields.Nested(
        'PlayoffStageMatchSchema', only=('id',), dump_only=True)
    depends_on_match_1 = fields.Nested(
        'PlayoffStageMatchSchema', only=('id',), dump_only=True)
    depends_on_match_2 = fields.Nested(
        'PlayoffStageMatchSchema', only=('id',), dump_only=True)


class MatchSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Match
        load_instance = True
        sqla_session = db.session
        include_fk = True

    id = fields.UUID(dump_default=uuid.uuid4)
    type = fields.Str(required=True, validate=validate.Length(max=16))
    format = fields.Str(required=True, validate=validate.Length(max=8))
    status = fields.Str(required=True, validate=validate.Length(max=16))
    scheduled_time = fields.DateTime(allow_none=True)
    is_playoff = fields.Boolean(required=True)
    participant1_score = fields.Integer(dump_default=0)
    participant2_score = fields.Integer(dump_default=0)
    winner_id = fields.UUID(allow_none=True)
    tournament_id = fields.UUID(required=True)
    group_id = fields.UUID(allow_none=True)

    # Сериализация связей
    tournament = fields.Nested(
        'TournamentSchema', only=('id',), dump_only=True)
    group = fields.Nested('GroupSchema', only=('id',), dump_only=True)
    playoff_match = fields.Nested(
        'PlayoffStageMatchSchema', exclude=('match',), dump_only=True)
    maps = fields.Nested('MapSchema', many=True, dump_only=True)
    participant1 = fields.Nested('UserSchema', only=(
        'id', 'name', 'avatar'), dump_only=True)
    participant2 = fields.Nested('UserSchema', only=(
        'id', 'name', 'avatar'), dump_only=True)
