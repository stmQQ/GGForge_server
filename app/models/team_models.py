from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text)
    logo_path = db.Column(db.String(256))

    leader_id = db.Column(UUID(as_uuid=True),
                          db.ForeignKey('users.id'), nullable=False)
    leader = db.relationship('User', back_populates='led_teams', foreign_keys=[
                             leader_id], lazy='selectin')

    players = db.relationship(
        'User', secondary='team_members', back_populates='member_teams', lazy='selectin')
    participated_tournaments = db.relationship(
        'Tournament', secondary='tournament_teams', back_populates='teams', lazy='selectin')
    groups = db.relationship(
        'Group', secondary='group_teams', back_populates='teams', lazy='selectin')
    group_rows = db.relationship(
        'GroupRow', back_populates='team', lazy='selectin')
    prizetable_rows = db.relationship(
        'PrizeTableRow', back_populates='team', lazy='selectin')
    requests = db.relationship(
        'UserRequest', back_populates='team', lazy='selectin')
