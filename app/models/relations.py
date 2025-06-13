from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, UTC

user_achievements = db.Table(
    'user_achievements',
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id')),
    db.Column('achievement_id', UUID(as_uuid=True),
              db.ForeignKey('achievements.id')),
    db.Column('unlocked_at', db.DateTime,
              nullable=False, default=datetime.now(UTC))
)

tournament_participants = db.Table(
    'tournament_participants',
    db.Column('tournament_id', UUID(as_uuid=True),
              db.ForeignKey('tournaments.id')),
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id'))
)

tournament_teams = db.Table(
    'tournament_teams',
    db.Column('tournament_id', UUID(as_uuid=True),
              db.ForeignKey('tournaments.id')),
    db.Column('team_id', UUID(as_uuid=True), db.ForeignKey('teams.id'))
)

# match_participants = db.Table(
#     'match_participants',
#     db.Column('match_id', UUID(as_uuid=True), db.ForeignKey('matches.id')),
#     db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id'))
# )

group_users = db.Table(
    'group_users',
    db.Column('group_id', UUID(as_uuid=True), db.ForeignKey('groups.id')),
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id'))
)

group_teams = db.Table(
    'group_teams',
    db.Column('group_id', UUID(as_uuid=True), db.ForeignKey('groups.id')),
    db.Column('team_id', UUID(as_uuid=True), db.ForeignKey('teams.id'))
)

team_members = db.Table(
    'team_members',
    db.Column('team_id', UUID(as_uuid=True), db.ForeignKey('teams.id')),
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id'))
)
