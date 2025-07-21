"""Add seller_rating and rating_count columns to users table

Revision ID: add_seller_rating_and_count
Revises: 
Create Date: 2025-05-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_seller_rating_and_count'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('seller_rating', sa.Float(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('rating_count', sa.Integer(), nullable=True, server_default='0'))

def downgrade():
    op.drop_column('users', 'seller_rating')
    op.drop_column('users', 'rating_count')
