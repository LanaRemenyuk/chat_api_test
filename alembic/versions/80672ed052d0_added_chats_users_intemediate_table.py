"""Added chats-users-intemediate-table

Revision ID: 80672ed052d0
Revises: b30c81f597ac
Create Date: 2024-11-28 13:04:29.499985

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '80672ed052d0'
down_revision: Union[str, None] = 'b30c81f597ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
