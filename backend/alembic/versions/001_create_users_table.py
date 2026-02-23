"""create users table

Revision ID: 001
Revises:
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        # Fernet-encrypted fields stored as text
        sa.Column("passport_number_enc", sa.String, nullable=True),
        sa.Column("tsa_known_traveler_enc", sa.String, nullable=True),
        # Plain-text preferences
        sa.Column("seat_preference", sa.String(50), nullable=True),
        sa.Column("meal_preference", sa.String(50), nullable=True),
        # JSON array of {program, number}
        sa.Column("loyalty_numbers", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
