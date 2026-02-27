"""add booking agent fields: profile personal info, agent_logs table, virtual_card_id on bookings

Revision ID: 003
Revises: 002
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users: add personal info fields needed by the booking agent ---
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(30), nullable=True))

    # --- bookings: add virtual_card_id for Stripe Issuing card management ---
    op.add_column("bookings", sa.Column("virtual_card_id", sa.String, nullable=True))

    # --- agent_logs: step-by-step log of each booking agent run ---
    op.create_table(
        "agent_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "booking_id",
            UUID(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            nullable=False,
        ),
        sa.Column("step", sa.String(100), nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("screenshot_b64", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_logs_booking_id", "agent_logs", ["booking_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_logs_booking_id", table_name="agent_logs")
    op.drop_table("agent_logs")
    op.drop_column("bookings", "virtual_card_id")
    op.drop_column("users", "phone")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
