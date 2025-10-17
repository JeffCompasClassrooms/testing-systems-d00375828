from pathlib import Path
from mydb import MyDB

def describe_mydb():
    def it_creates_file_if_missing(tmp_path: Path):
        # Constructor should create the backing file on first use
        db_path = tmp_path / "strings.db"
        assert not db_path.exists()
        MyDB(str(db_path))
        # File exists and is non-empty (pickle header at minimum)
        assert db_path.exists() and db_path.stat().st_size > 0

    def it_saves_and_loads_empty_list(tmp_path: Path):
        # Fresh DB loads as an empty list
        db = MyDB(str(tmp_path / "x.db"))
        data = db.loadStrings()
        assert isinstance(data, list)
        assert data == []

    def it_saveStrings_overwrites_entire_collection(tmp_path: Path):
        # saveStrings replaces the entire list
        db = MyDB(str(tmp_path / "x.db"))
        db.saveStrings(["a", "b", "c"])
        assert db.loadStrings() == ["a", "b", "c"]
        db.saveStrings(["z"])
        assert db.loadStrings() == ["z"]

    def it_saveString_appends_one_item(tmp_path: Path):
        # saveString appends a single value to the existing list
        db = MyDB(str(tmp_path / "x.db"))
        db.saveStrings(["base"])
        db.saveString("one")
        db.saveString("two")
        assert db.loadStrings() == ["base", "one", "two"]

    def it_persists_across_instances(tmp_path: Path):
        # Data persists across distinct MyDB instances (black-box persistence)
        db_path = tmp_path / "z.db"
        MyDB(str(db_path)).saveStrings(["one"])
        db2 = MyDB(str(db_path))
        assert db2.loadStrings() == ["one"]

    def it_handles_unicode_and_long_strings(tmp_path: Path):
        # Unicode and long strings round-trip correctly via pickle
        s = "🧪 café — 長い文字列" * 50
        db = MyDB(str(tmp_path / "u.db"))
        db.saveString(s)
        assert db.loadStrings() == [s]
