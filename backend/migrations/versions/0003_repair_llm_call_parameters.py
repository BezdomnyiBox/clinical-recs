"""Restore the LLM call parameters column when an existing database drifted.

Revision ID: 0003_repair_llm_call_parameters
Revises: 0002_llm_activity
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_repair_llm_call_parameters"
down_revision = "0002_llm_activity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("llm_calls")}
    if "parameters" not in columns:
        op.add_column("llm_calls", sa.Column("parameters", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("llm_calls")}
    if "parameters" in columns:
        op.drop_column("llm_calls", "parameters")
