"""baseline: schema as created by Base.metadata.create_all before migrations

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("applicant_name", sa.String(255), nullable=False),
        sa.Column("applicant_email", sa.String(320), nullable=False),
        sa.Column("submission_date", sa.DateTime, nullable=False),
        sa.Column("receipt", sa.String(100), nullable=False),
    )
    op.create_index("ix_applications_applicant_email", "applications", ["applicant_email"])
    op.create_index("ix_applications_submission_date", "applications", ["submission_date"])
    op.create_index("ix_applications_receipt", "applications", ["receipt"], unique=True)
    op.create_table(
        "stages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("application_id", sa.Integer, sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("entered_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_stages_application_id", "stages", ["application_id"])
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("stage_id", sa.Integer, sa.ForeignKey("stages.id"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_notes_stage_id", "notes", ["stage_id"])


def downgrade() -> None:
    op.drop_table("notes")
    op.drop_table("stages")
    op.drop_table("applications")
