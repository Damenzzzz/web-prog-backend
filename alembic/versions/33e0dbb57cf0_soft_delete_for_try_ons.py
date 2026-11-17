from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '33e0dbb57cf0'
down_revision: str | Sequence[str] | None = '9d8d32b3736c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('try_ons', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('try_ons', 'deleted_at')
