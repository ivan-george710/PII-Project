"""Versioned company policies and PII event tables for Issue 4."""

import sqlalchemy as sa
from alembic import op

revision = "0005_company_policy_events"
down_revision = "0003_signup"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_rule_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("builtins", sa.JSON(), nullable=False),
        sa.Column("custom_rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_company_rule_policies_company_id"),
    )

    op.create_table(
        "pii_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "submission_id",
            "policy_version",
            name="uq_pii_events_company_submission_version",
        ),
    )
    op.create_index("ix_pii_events_company_id", "pii_events", ["company_id"])
    op.create_index("ix_pii_events_submission_id", "pii_events", ["submission_id"])
    op.create_index("ix_pii_events_employee_id", "pii_events", ["employee_id"])
    op.create_index("ix_pii_events_occurred_at", "pii_events", ["occurred_at"])
    op.create_index(
        "ix_pii_events_company_employee_time",
        "pii_events",
        ["company_id", "employee_id", "occurred_at"],
    )


def downgrade():
    op.drop_index("ix_pii_events_company_employee_time", table_name="pii_events")
    op.drop_index("ix_pii_events_occurred_at", table_name="pii_events")
    op.drop_index("ix_pii_events_employee_id", table_name="pii_events")
    op.drop_index("ix_pii_events_submission_id", table_name="pii_events")
    op.drop_index("ix_pii_events_company_id", table_name="pii_events")
    op.drop_table("pii_events")

    op.drop_table("company_rule_policies")
