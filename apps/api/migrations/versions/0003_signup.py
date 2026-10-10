"""Allow unconstrained email text for the requested simple sign-up flow."""

import sqlalchemy as sa
from alembic import op

revision = "0003_signup"
down_revision = "0002_local_auth"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "email",
            existing_type=sa.String(254),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "email",
            existing_type=sa.Text(),
            type_=sa.String(254),
            existing_nullable=False,
        )
