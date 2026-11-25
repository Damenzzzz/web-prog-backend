"""auth for users: email, password_hash, role

Старые анкеты создавались без email и пароля, войти в них нельзя,
а колонки email и password_hash обязательные (NOT NULL). Поэтому старые
пользователи удаляются. Их примерочная, заказы и примерки удаляются
вместе с ними через ON DELETE CASCADE.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a1c4e7f2b9d0'
down_revision: str | Sequence[str] | None = '997671a34a17'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum('user', 'admin', name='user_role')


def upgrade() -> None:
    op.execute('DELETE FROM users')
    user_role.create(op.get_bind())
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=False))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=False))
    op.add_column('users', sa.Column('role', user_role, nullable=False, server_default='user'))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'role')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')
    user_role.drop(op.get_bind())
