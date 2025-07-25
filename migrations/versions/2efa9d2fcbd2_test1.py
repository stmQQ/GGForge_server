"""Test1\

Revision ID: 2efa9d2fcbd2
Revises: 
Create Date: 2025-04-30 22:59:19.348062

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2efa9d2fcbd2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('games',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=64), nullable=False),
    sa.Column('image_path', sa.String(length=256), nullable=False),
    sa.Column('logo_path', sa.String(length=256), nullable=False),
    sa.Column('service_name', sa.String(length=32), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('image_path'),
    sa.UniqueConstraint('logo_path'),
    sa.UniqueConstraint('title')
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('email', sa.String(length=256), nullable=False),
    sa.Column('password_hash', sa.String(length=256), nullable=False),
    sa.Column('avatar', sa.String(length=128), nullable=True),
    sa.Column('registration_date', sa.Date(), nullable=False),
    sa.Column('last_online', sa.DateTime(), nullable=False),
    sa.Column('is_online', sa.Boolean(), nullable=True),
    sa.Column('admin_role', sa.Boolean(), nullable=False),
    sa.Column('is_banned', sa.Boolean(), nullable=True),
    sa.Column('ban_until', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('name')
    )
    op.create_table('achievements',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=64), nullable=False),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.Column('game_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('connections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('service_name', sa.String(length=64), nullable=False),
    sa.Column('external_user_url', sa.String(length=256), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_user_url')
    )
    op.create_table('mutual_friend_association',
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('friend_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['friend_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_table('support_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('theme', sa.String(length=64), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('response', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('teams',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('logo_path', sa.String(length=256), nullable=True),
    sa.Column('leader_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['leader_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('token_blocklist',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('jti', sa.String(length=36), nullable=False),
    sa.Column('token_type', sa.String(length=10), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('jti')
    )
    op.create_table('tournaments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=64), nullable=False),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('prize_pool', sa.String(length=8), nullable=True),
    sa.Column('max_players', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('banner_url', sa.String(length=128), nullable=True),
    sa.Column('game_id', sa.UUID(), nullable=False),
    sa.Column('creator_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('game_accounts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('game_id', sa.UUID(), nullable=False),
    sa.Column('connection_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('group_stages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tournament_id', sa.UUID(), nullable=False),
    sa.Column('winners_bracket_qualified', sa.Integer(), nullable=False),
    sa.Column('losers_bracket_qualified', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('playoff_stages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tournament_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('prize_tables',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tournament_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('team_members',
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_table('tournament_participants',
    sa.Column('tournament_id', sa.UUID(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_table('tournament_teams',
    sa.Column('tournament_id', sa.UUID(), nullable=True),
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], )
    )
    op.create_table('user_achievements',
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('achievement_id', sa.UUID(), nullable=True),
    sa.Column('unlocked_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['achievement_id'], ['achievements.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_table('user_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('from_user_id', sa.UUID(), nullable=False),
    sa.Column('to_user_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('groups',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('letter', sa.String(length=4), nullable=False),
    sa.Column('max_participants', sa.Integer(), nullable=False),
    sa.Column('groupstage_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['groupstage_id'], ['group_stages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('prize_table_rows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('place', sa.Integer(), nullable=True),
    sa.Column('prize', sa.String(length=16), nullable=True),
    sa.Column('prize_table_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['prize_table_id'], ['prize_tables.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('group_rows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('place', sa.Integer(), nullable=False),
    sa.Column('wins', sa.Integer(), nullable=True),
    sa.Column('draws', sa.Integer(), nullable=True),
    sa.Column('loses', sa.Integer(), nullable=True),
    sa.Column('group_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('group_teams',
    sa.Column('group_id', sa.UUID(), nullable=True),
    sa.Column('team_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], )
    )
    op.create_table('group_users',
    sa.Column('group_id', sa.UUID(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_table('matches',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('format', sa.String(length=8), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('is_playoff', sa.Boolean(), nullable=False),
    sa.Column('participant1_id', sa.UUID(), nullable=True),
    sa.Column('participant2_id', sa.UUID(), nullable=True),
    sa.Column('participant1_score', sa.Integer(), nullable=True),
    sa.Column('participant2_score', sa.Integer(), nullable=True),
    sa.Column('winner_id', sa.UUID(), nullable=True),
    sa.Column('tournament_id', sa.UUID(), nullable=False),
    sa.Column('group_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('maps',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('external_id', sa.String(length=128), nullable=True),
    sa.Column('winner_id', sa.UUID(), nullable=True),
    sa.Column('match_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('playoff_stage_matches',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('round_number', sa.String(length=8), nullable=False),
    sa.Column('winner_to_match_id', sa.UUID(), nullable=True),
    sa.Column('loser_to_match_id', sa.UUID(), nullable=True),
    sa.Column('depends_on_match_1_id', sa.UUID(), nullable=True),
    sa.Column('depends_on_match_2_id', sa.UUID(), nullable=True),
    sa.Column('playoff_id', sa.UUID(), nullable=True),
    sa.Column('match_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['depends_on_match_1_id'], ['playoff_stage_matches.id'], ),
    sa.ForeignKeyConstraint(['depends_on_match_2_id'], ['playoff_stage_matches.id'], ),
    sa.ForeignKeyConstraint(['loser_to_match_id'], ['playoff_stage_matches.id'], ),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
    sa.ForeignKeyConstraint(['playoff_id'], ['playoff_stages.id'], ),
    sa.ForeignKeyConstraint(['winner_to_match_id'], ['playoff_stage_matches.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('match_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('playoff_stage_matches')
    op.drop_table('maps')
    op.drop_table('matches')
    op.drop_table('group_users')
    op.drop_table('group_teams')
    op.drop_table('group_rows')
    op.drop_table('prize_table_rows')
    op.drop_table('groups')
    op.drop_table('user_requests')
    op.drop_table('user_achievements')
    op.drop_table('tournament_teams')
    op.drop_table('tournament_participants')
    op.drop_table('team_members')
    op.drop_table('prize_tables')
    op.drop_table('playoff_stages')
    op.drop_table('group_stages')
    op.drop_table('game_accounts')
    op.drop_table('tournaments')
    op.drop_table('token_blocklist')
    op.drop_table('teams')
    op.drop_table('support_tokens')
    op.drop_table('mutual_friend_association')
    op.drop_table('connections')
    op.drop_table('achievements')
    op.drop_table('users')
    op.drop_table('games')
    # ### end Alembic commands ###
