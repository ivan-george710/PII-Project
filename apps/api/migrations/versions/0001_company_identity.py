"""Company identity and trusted manager assignments."""

import sqlalchemy as sa
from alembic import op

revision = "0001_company_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    timestamps = [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("workos_organization_id", sa.String(100), unique=True),
        *timestamps,
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("workos_user_id", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "organization_id"),
        sa.CheckConstraint("role IN ('employee','manager')"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_table(
        "manager_assignments",
        sa.Column("employee_id", sa.Uuid(), primary_key=True),
        sa.Column("manager_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["manager_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("employee_id <> manager_id"),
    )
    op.create_index(
        "ix_manager_assignments_manager_id", "manager_assignments", ["manager_id"]
    )
    op.create_index(
        "ix_manager_assignments_organization_id",
        "manager_assignments",
        ["organization_id"],
    )


def downgrade():
    op.drop_table("manager_assignments")
    op.drop_table("users")
    op.drop_table("organizations")
