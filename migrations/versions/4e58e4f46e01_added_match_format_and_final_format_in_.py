"""Added match_format and final_format in tournament

Revision ID: 4e58e4f46e01
Revises: ae6e36f1bd0c
Create Date: 2025-05-11 00:08:04.122704

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4e58e4f46e01'
down_revision = 'ae6e36f1bd0c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('match_format', sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column('final_format', sa.String(length=8), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_column('final_format')
        batch_op.drop_column('match_format')

    # ### end Alembic commands ###
