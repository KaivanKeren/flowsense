"""initial

Revision ID: initial
Revises: 
Create Date: 2026-08-04 16:59:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = 'initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # We leave the actual table creation to be generated later since we don't have python access
    # Run `alembic revision --autogenerate` to get the real migration
    pass

def downgrade() -> None:
    # Intentional no-op: this is the initial (base) migration, so there is no
    # prior schema to revert to. Dropping the initial tables is destructive
    # and is intentionally not supported.
    pass
