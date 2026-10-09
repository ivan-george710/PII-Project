"""Employee conversations, sanitized messages, attachments, and submissions."""

import sqlalchemy as sa
from alembic import op

revision = "0002_conversations_messages_attachments"
down_revision = "0001_company_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("id", "employee_id", "organization_id"),
        sa.ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_conversations_owner_updated",
        "conversations",
        ["organization_id", "employee_id", "updated_at", "id"],
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("sanitized_text", sa.Text(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(100)),
        sa.Column("attachment_ids", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id", "organization_id"],
            ["conversations.id", "conversations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("id", "conversation_id", "organization_id"),
        sa.CheckConstraint("role IN ('user','assistant')"),
        sa.CheckConstraint(
            "state IN ('processing','completed','failed','cancelled')"
        ),
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at", "id"],
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid()),
        sa.Column("original_key", sa.String(512), nullable=False),
        sa.Column("sanitized_key", sa.String(512)),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("sample_id", sa.Uuid()),
        sa.Column("sample_request_id", sa.Uuid()),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id", "employee_id", "organization_id"],
            [
                "conversations.id",
                "conversations.employee_id",
                "conversations.organization_id",
            ],
            name="fk_attachment_conversation_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("size_bytes BETWEEN 1 AND 26214400"),
        sa.UniqueConstraint(
            "employee_id",
            "sample_id",
            "sample_request_id",
            name="uq_attachment_employee_sample_request",
        ),
        sa.CheckConstraint(
            "state IN ('pending_upload','uploaded','processing','sanitized','failed')"
        ),
    )
    op.create_index(
        "ix_attachments_owner",
        "attachments",
        ["organization_id", "employee_id", "id"],
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("assistant_message_id", sa.Uuid()),
        sa.Column("stream_result", sa.Text()),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "employee_id",
            "conversation_id",
            "client_request_id",
            name="uq_submission_employee_conversation_request",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id", "employee_id", "organization_id"],
            [
                "conversations.id",
                "conversations.employee_id",
                "conversations.organization_id",
            ],
            name="fk_submission_conversation_owner",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id", "conversation_id", "organization_id"],
            [
                "messages.id",
                "messages.conversation_id",
                "messages.organization_id",
            ],
            name="fk_submission_assistant_message",
        ),
        sa.CheckConstraint("state IN ('processing','completed','failed','cancelled')"),
    )
    op.create_index(
        "uq_submissions_active_conversation",
        "submissions",
        ["organization_id", "conversation_id"],
        unique=True,
        sqlite_where=sa.text("state = 'processing'"),
        postgresql_where=sa.text("state = 'processing'"),
    )


def downgrade():
    op.drop_index("uq_submissions_active_conversation", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_attachments_owner", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_owner_updated", table_name="conversations")
    op.drop_table("conversations")
