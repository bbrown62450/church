import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_readme_documents_multiuser_ops():
    readme = _read("README.md")
    assert "[auth]" in readme                          # Streamlit login secrets block
    assert "/oauth2callback" in readme                 # login redirect URI (URI #1)
    assert "bare app root" in readme                   # app-root gmail.send redirect (URI #2)
    assert "pooler.supabase.com" in readme             # session-pooler DATABASE_URL
    assert "python migrate_to_db.py" in readme         # migration command
    assert ("keep-alive" in readme.lower()) or ("keepalive" in readme.lower())


def test_env_example_updated():
    env = _read(".env.example")
    assert "DATABASE_URL" in env
    for removed in ("APP_PASSWORD", "GMAIL_APP_PASSWORD", "GMAIL_ADDRESS"):
        assert removed not in env


def test_manual_verification_checklist_exists():
    checklist = _read("docs/manual-verification.md").lower()
    assert ("oauth2callback" in checklist) or ("cors" in checklist)
    assert "invite" in checklist
    assert "login" in checklist
