from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = '9d8d32b3736c'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('looks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('height_cm', sa.Integer(), nullable=False),
    sa.Column('weight_kg', sa.Integer(), nullable=False),
    sa.Column('gender', sa.Enum('female', 'male', name='gender'), nullable=False),
    sa.Column('body_type', sa.Enum('slim', 'average', 'athletic', 'plus', name='body_type'), nullable=False),
    sa.Column('style_preference', sa.String(length=200), nullable=True),
    sa.Column('photo_url', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('height_cm BETWEEN 100 AND 250', name='ck_users_height'),
    sa.CheckConstraint('weight_kg BETWEEN 30 AND 250', name='ck_users_weight'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.Enum('top', 'bottom', 'outerwear', 'shoes', 'bag', 'accessory', name='category'), nullable=False),
    sa.Column('color', sa.String(length=30), nullable=False),
    sa.Column('price', sa.Integer(), nullable=False),
    sa.Column('stock', sa.Integer(), nullable=False),
    sa.Column('look_id', sa.Integer(), nullable=True),
    sa.Column('image_url', sa.String(length=255), nullable=True),
    sa.CheckConstraint('price > 0', name='ck_items_price_positive'),
    sa.CheckConstraint('stock >= 0', name='ck_items_stock_not_negative'),
    sa.ForeignKeyConstraint(['look_id'], ['looks.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_items_look_id'), 'items', ['look_id'], unique=False)
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'paid', 'shipped', 'cancelled', name='order_status'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('total >= 0', name='ck_orders_total'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_user_id'), 'orders', ['user_id'], unique=False)
    op.create_table('try_ons',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('done', 'failed', name='try_on_status'), nullable=False),
    sa.Column('source', sa.String(length=10), nullable=False),
    sa.Column('result_url', sa.String(length=255), nullable=True),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_try_ons_user_id'), 'try_ons', ['user_id'], unique=False)
    op.create_table('fitting_room_rows',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.CheckConstraint('quantity >= 1', name='ck_fitting_room_quantity'),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'item_id', name='uq_fitting_room_user_item')
    )
    op.create_index(op.f('ix_fitting_room_rows_user_id'), 'fitting_room_rows', ['user_id'], unique=False)
    op.create_table('order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('price', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.CheckConstraint('price > 0', name='ck_order_items_price'),
    sa.CheckConstraint('quantity >= 1', name='ck_order_items_quantity'),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_items_order_id'), 'order_items', ['order_id'], unique=False)
    op.create_table('try_on_items',
    sa.Column('try_on_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['try_on_id'], ['try_ons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('try_on_id', 'item_id')
    )


def downgrade() -> None:
    op.drop_table('try_on_items')
    op.drop_index(op.f('ix_order_items_order_id'), table_name='order_items')
    op.drop_table('order_items')
    op.drop_index(op.f('ix_fitting_room_rows_user_id'), table_name='fitting_room_rows')
    op.drop_table('fitting_room_rows')
    op.drop_index(op.f('ix_try_ons_user_id'), table_name='try_ons')
    op.drop_table('try_ons')
    op.drop_index(op.f('ix_orders_user_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_items_look_id'), table_name='items')
    op.drop_table('items')
    op.drop_table('users')
    op.drop_table('looks')
    for name in ("try_on_status", "order_status", "category", "body_type", "gender"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
