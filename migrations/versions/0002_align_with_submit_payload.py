"""rename columns to the submit.py payload names and add the link columns

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_applications_applicant_email", "applications")
    op.drop_index("ix_applications_submission_date", "applications")
    with op.batch_alter_table("applications") as batch:
        batch.alter_column("applicant_name", new_column_name="name")
        batch.alter_column("applicant_email", new_column_name="email")
        batch.alter_column("submission_date", new_column_name="timestamp")
        batch.add_column(sa.Column("resume_link", sa.String(2048), nullable=True))
        batch.add_column(sa.Column("repository_link", sa.String(2048), nullable=True))
        batch.add_column(sa.Column("action_run_link", sa.String(2048), nullable=True))
    op.create_index("ix_applications_email", "applications", ["email"])
    op.create_index("ix_applications_timestamp", "applications", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_applications_email", "applications")
    op.drop_index("ix_applications_timestamp", "applications")
    with op.batch_alter_table("applications") as batch:
        batch.drop_column("action_run_link")
        batch.drop_column("repository_link")
        batch.drop_column("resume_link")
        batch.alter_column("timestamp", new_column_name="submission_date")
        batch.alter_column("email", new_column_name="applicant_email")
        batch.alter_column("name", new_column_name="applicant_name")
    op.create_index("ix_applications_applicant_email", "applications", ["applicant_email"])
    op.create_index("ix_applications_submission_date", "applications", ["submission_date"])
