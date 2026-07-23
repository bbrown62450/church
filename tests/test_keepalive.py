import pathlib

from keepalive import ping

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_ping_ok_on_sqlite(tmp_path):
    url = f"sqlite:///{tmp_path / 'keepalive.db'}"
    assert ping(url) is True


def test_ping_false_on_empty_url():
    assert ping("") is False


def test_ping_false_on_unreachable():
    assert ping("postgresql+psycopg2://u:p@127.0.0.1:1/none") is False


def test_keepalive_workflow_has_daily_cron():
    text = (ROOT / ".github" / "workflows" / "keepalive.yml").read_text(encoding="utf-8")
    assert "schedule:" in text
    assert "cron:" in text
    assert "python keepalive.py" in text


def test_backup_workflow_present():
    text = (ROOT / ".github" / "workflows" / "backup.yml").read_text(encoding="utf-8")
    assert "pg_dump" in text
    assert "schedule:" in text
