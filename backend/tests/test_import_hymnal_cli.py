"""import_hymnal.py, the ops CLI kept beside Settings → Hymns (6a spec;
slice 6a-2): a bundled hymnal needs no --csv, and importing the module reads
no .env file."""
import ast
from pathlib import Path

import pytest

import import_hymnal
from repos.hymns import list_hymns


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    """main() reads a .env file; a developer's must not reach the tests."""
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)


def test_a_bundled_hymnal_imports_without_csv_and_again_adds_nothing(tmp_db, make_church, capsys):
    cid = make_church(name="Grace")
    import_hymnal.main(["--church-id", str(cid), "--hymnal", "PH1990"])
    assert len(list_hymns(cid, hymnal="PH1990")) == 605
    import_hymnal.main(["--church-id", str(cid), "--hymnal", "PH1990"])
    out = capsys.readouterr().out
    assert "Imported PH1990: {'inserted': 605, 'updated': 0, 'total': 605}" in out
    assert "Imported PH1990: {'inserted': 0, 'updated': 0, 'total': 0}" in out
    assert len(list_hymns(cid, hymnal="PH1990")) == 605


def test_a_csv_is_still_required_for_a_hymnal_that_is_not_bundled(tmp_db, make_church, tmp_path, capsys):
    cid = make_church(name="Grace")
    with pytest.raises(SystemExit):
        import_hymnal.main(["--church-id", str(cid), "--hymnal", "XX2000"])
    assert "--csv is required: XX2000 is not a bundled hymnal (PH1990)" in capsys.readouterr().err
    path = tmp_path / "XX2000.csv"
    path.write_text("number,title\n1,First Hymn\n", encoding="utf-8")
    import_hymnal.main(["--church-id", str(cid), "--hymnal", "XX2000", "--csv", str(path)])
    assert [h["Hymn Title"] for h in list_hymns(cid, hymnal="XX2000")] == ["First Hymn"]


def test_importing_the_module_does_not_load_a_dotenv_file():
    tree = ast.parse(Path(import_hymnal.__file__).read_text(encoding="utf-8"))
    top_level_calls = [node.value.func.id for node in tree.body
                       if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Name)]
    assert "load_dotenv" not in top_level_calls
    assert "data/hymnals" not in Path(import_hymnal.__file__).read_text(encoding="utf-8")
