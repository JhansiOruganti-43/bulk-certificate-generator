"""Add enrollment_id to Certificate

Revision ID: 99fe284b3eb5
Revises: 2f802a1c9d26
Create Date: 2026-10-09 12:16:54.809500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
"""Add enrollment_id to Certificate

Revision ID: 99fe284b3eb5
Revises: 2f802a1c9d26
Create Date: 2026-10-09 12:16:54.809500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99fe284b3eb5'
down_revision: Union[str, Sequence[str], None] = '2f802a1c9d26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add enrollment_id column and FK to certificates if not present."""
    # SQLite supports IF NOT EXISTS for ADD COLUMN from version 3.35.0
    # Use raw SQL to be safe across versions.
    op.execute("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS enrollment_id VARCHAR")
    # Create index if not exists
    op.execute("CREATE INDEX IF NOT EXISTS ix_certificates_enrollment_id ON certificates (enrollment_id)")
    # Add foreign key constraint via pragma (SQLite does not enforce FK on ALTER, but we keep for other DBs)
    op.create_foreign_key(
        'fk_certificates_enrollment_id',
        'certificates', 'enrollments',
        ['enrollment_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema: remove enrollment_id column and FK if they exist."""
    op.drop_constraint('fk_certificates_enrollment_id', 'certificates', type_='foreignkey')
    # SQLite does not support DROP COLUMN; we can ignore for downgrade on SQLite.
    # For other DBs, use op.drop_column.
    try:
        op.drop_column('certificates', 'enrollment_id')
    except Exception:
        pass
