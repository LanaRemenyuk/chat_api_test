"""Added chats-users-intemediate-table

Revision ID: eb8988501778
Revises: 80672ed052d0
Create Date: 2024-11-28 13:05:46.491149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb8988501778'
down_revision: Union[str, None] = '80672ed052d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
