"""Replace provider identities with password hashes and revocable local sessions.

Existing company/user UUIDs and manager assignments are preserved. Users start
without passwords and must be provisioned through the trusted operator command.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_local_auth"
down_revision = "0001_company_identity"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # Normalize and reject collisions before creating the login identity constraint.
    duplicate = connection.execute(
        sa.text(
            "SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*) > 1"
        )
    ).first()
    if duplicate:
        raise ValueError("Duplicate login emails must be resolved before migrating")
    connection.execute(sa.text("UPDATE users SET email = lower(email)"))
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s"}

    def unique_name(table, column):
        constraints = sa.inspect(connection).get_unique_constraints(table)
        return next(
            c["name"] or f"uq_{table}_{column}"
            for c in constraints
            if c["column_names"] == [column]
        )

    with op.batch_alter_table(
        "users",
        naming_convention=naming,
        table_args=(
            sa.CheckConstraint(
                "role IN ('employee','manager')", name="users_role_check"
            ),
        ),
    ) as batch:
        batch.drop_constraint(unique_name("users", "workos_user_id"), type_="unique")
        batch.drop_column("workos_user_id")
        batch.add_column(sa.Column("password_hash", sa.String(255), nullable=True))
        batch.add_column(
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_unique_constraint("uq_users_email", ["email"])
    with op.batch_alter_table("users") as batch:
        batch.alter_column("failed_login_attempts", server_default=None)
    with op.batch_alter_table("organizations", naming_convention=naming) as batch:
        batch.drop_constraint(
            unique_name("organizations", "workos_organization_id"), type_="unique"
        )
        batch.drop_column("workos_organization_id")
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])


def downgrade():
    # Provider identities were deliberately removed and cannot be reconstructed.
    raise RuntimeError(
        "Local auth migration requires a database backup to restore provider identities"
    )
