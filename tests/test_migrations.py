import sqlite3

from sqlalchemy import inspect

from app.database import make_engine
from app.migrate import upgrade_to_head


def test_fresh_database_migrates_to_head(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    upgrade_to_head(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("applications")}
    assert {"name", "email", "timestamp", "resume_link", "repository_link", "action_run_link"} <= cols


def test_legacy_database_is_adopted_and_data_survives(tmp_path):
    path = tmp_path / "legacy.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY, applicant_name VARCHAR(255) NOT NULL,
            applicant_email VARCHAR(320) NOT NULL, submission_date DATETIME NOT NULL,
            receipt VARCHAR(100) NOT NULL);
        CREATE INDEX ix_applications_applicant_email ON applications (applicant_email);
        CREATE INDEX ix_applications_submission_date ON applications (submission_date);
        CREATE UNIQUE INDEX ix_applications_receipt ON applications (receipt);
        CREATE TABLE stages (id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL
            REFERENCES applications (id), name VARCHAR(30) NOT NULL, entered_at DATETIME NOT NULL);
        CREATE INDEX ix_stages_application_id ON stages (application_id);
        CREATE TABLE notes (id INTEGER PRIMARY KEY, stage_id INTEGER NOT NULL
            REFERENCES stages (id), content TEXT NOT NULL, created_at DATETIME NOT NULL);
        CREATE INDEX ix_notes_stage_id ON notes (stage_id);
        INSERT INTO applications VALUES (1, 'Ada', 'ada@example.com', '2026-01-02 03:04:05', 'r-1');
        """
    )
    con.commit()
    con.close()

    engine = make_engine(f"sqlite:///{path}")
    upgrade_to_head(engine)
    upgrade_to_head(engine)  # idempotent
    with engine.connect() as c:
        row = c.exec_driver_sql(
            "SELECT name, email, timestamp, resume_link FROM applications"
        ).one()
    assert tuple(row) == ("Ada", "ada@example.com", "2026-01-02 03:04:05", None)
    assert {i["name"] for i in inspect(engine).get_indexes("applications")} >= {
        "ix_applications_email", "ix_applications_timestamp", "ix_applications_receipt"}
