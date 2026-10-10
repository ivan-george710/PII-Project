"""Durable private original/sanitized upload bytes across serverless instances."""

import sqlalchemy as sa
from alembic import op

revision = "0006_private_file_blobs"
down_revision = "0005_company_policy_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "private_file_blobs",
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column(
            "attachment_id",
            sa.Uuid(),
            sa.ForeignKey("attachments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )


def downgrade():
    op.drop_table("private_file_blobs")
