from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = db.Column(db.String(16), nullable=False)  # solo/team
    format = db.Column(db.String(8), nullable=False)  # bo1/bo3...
    # upcoming/ongoing/completed
    status = db.Column(db.String(16), nullable=False)
    number = db.Column(db.String(4))
    scheduled_time = db.Column(db.DateTime)
    is_playoff = db.Column(db.Boolean, default=False, nullable=False)

    participant1_id = db.Column(UUID(as_uuid=True), nullable=True)
    participant2_id = db.Column(UUID(as_uuid=True), nullable=True)
    participant1_score = db.Column(db.Integer, default=0)
    participant2_score = db.Column(db.Integer, default=0)
    winner_id = db.Column(UUID(as_uuid=True), nullable=True)

    tournament_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'tournaments.id', ondelete='CASCADE'), nullable=False)
    tournament = db.relationship('Tournament', back_populates='matches')

    group_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey('groups.id'), nullable=True)
    group = db.relationship('Group', back_populates='matches')

    playoff_match_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'playoff_stage_matches.id', ondelete='CASCADE'), nullable=True, unique=True)
    playoff_match = db.relationship(
        'PlayoffStageMatch', back_populates='match', uselist=False)

    maps = db.relationship('Map', back_populates='match',
                           lazy='selectin', cascade='all, delete-orphan')


class PlayoffStageMatch(db.Model):
    __tablename__ = 'playoff_stage_matches'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_number = db.Column(db.String(8), nullable=False)  # W1, L2 и т.д.
    bracket = db.Column(db.String(8), nullable=False)

    winner_to_match_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'playoff_stage_matches.id'), nullable=True)
    loser_to_match_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'playoff_stage_matches.id'), nullable=True)
    depends_on_match_1_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'playoff_stage_matches.id'), nullable=True)
    depends_on_match_2_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'playoff_stage_matches.id'), nullable=True)

    winner_to_match = db.relationship('PlayoffStageMatch', foreign_keys=[
                                      winner_to_match_id], remote_side='PlayoffStageMatch.id')
    loser_to_match = db.relationship('PlayoffStageMatch', foreign_keys=[
                                     loser_to_match_id], remote_side='PlayoffStageMatch.id')
    depends_on_match_1 = db.relationship('PlayoffStageMatch', foreign_keys=[
                                         depends_on_match_1_id], remote_side='PlayoffStageMatch.id')
    depends_on_match_2 = db.relationship('PlayoffStageMatch', foreign_keys=[
                                         depends_on_match_2_id], remote_side='PlayoffStageMatch.id')

    playoff_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'playoff_stages.id', ondelete='CASCADE'), nullable=False)
    playoff_stage = db.relationship(
        'PlayoffStage', back_populates='playoff_matches')
    match = db.relationship(
        'Match', back_populates='playoff_match', uselist=False, cascade='all, delete-orphan')


class Map(db.Model):
    __tablename__ = 'maps'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    external_url = db.Column(db.String(128), nullable=True)
    winner_id = db.Column(UUID(as_uuid=True), nullable=True)

    match_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'matches.id', ondelete='CASCADE'), nullable=False)
    match = db.relationship('Match', back_populates='maps')
