"""Добавляет статусы вызовов модели и события этапов обработки.

Revision ID: 0002_llm_activity
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_llm_activity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_calls",
        sa.Column(
            "status",
            sa.String(16),
            server_default=sa.text("'completed'"),
            nullable=False,
        ),
    )
    op.add_column("llm_calls", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("llm_calls", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.add_column("llm_calls", sa.Column("actual_model", sa.String(128), nullable=True))
    op.add_column("llm_calls", sa.Column("response_id", sa.String(128), nullable=True))
    op.add_column("llm_calls", sa.Column("prompt_hash", sa.String(64), nullable=True))
    op.add_column("llm_calls", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("llm_calls", sa.Column("page_end", sa.Integer(), nullable=True))
    op.add_column("llm_calls", sa.Column("parameters", sa.JSON(), nullable=True))
    op.add_column("llm_calls", sa.Column("result_summary", sa.JSON(), nullable=True))
    op.add_column("llm_calls", sa.Column("error_type", sa.String(128), nullable=True))
    op.add_column("llm_calls", sa.Column("error_message", sa.Text(), nullable=True))

    op.create_table(
        "processing_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_type", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processing_events_document_id",
        "processing_events",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_processing_events_job_id",
        "processing_events",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_processing_events_job_id", table_name="processing_events")
    op.drop_index("ix_processing_events_document_id", table_name="processing_events")
    op.drop_table("processing_events")
    op.drop_column("llm_calls", "error_message")
    op.drop_column("llm_calls", "error_type")
    op.drop_column("llm_calls", "result_summary")
    op.drop_column("llm_calls", "parameters")
    op.drop_column("llm_calls", "page_end")
    op.drop_column("llm_calls", "page_start")
    op.drop_column("llm_calls", "prompt_hash")
    op.drop_column("llm_calls", "response_id")
    op.drop_column("llm_calls", "actual_model")
    op.drop_column("llm_calls", "finished_at")
    op.drop_column("llm_calls", "started_at")
    op.drop_column("llm_calls", "status")
