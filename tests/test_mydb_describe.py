from pathlib import Path
from mydb import MyDB


def describe_mydb():
    # ---------------- Core behavior (existing tests) ----------------

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

    # ---------------- Additional edge cases (A1–A4) ----------------

    def it_preserves_empty_and_whitespace_strings(tmp_path: Path):
        """
        A1: MyDB should faithfully store and return empty and whitespace-only strings.
        """
        db = MyDB(str(tmp_path / "whitespace.db"))
        values = ["", " ", "   ", "\t", "\n", " mix \t\n "]
        db.saveStrings(values)
        loaded = db.loadStrings()
        assert isinstance(loaded, list)
        assert loaded == values

    def it_handles_large_number_of_items(tmp_path: Path):
        """
        A2: MyDB should handle a reasonably large list of items,
        not just a handful of strings.
        """
        db = MyDB(str(tmp_path / "many.db"))
        items = [f"item-{i}" for i in range(500)]
        db.saveStrings(items)
        loaded = db.loadStrings()
        assert len(loaded) == len(items)
        # Spot-check a few positions to avoid depending on implementation details
        assert loaded[0] == "item-0"
        assert loaded[123] == "item-123"
        assert loaded[-1] == "item-499"

    def it_allows_multiple_overwrite_cycles_on_same_file(tmp_path: Path):
        """
        A3: Repeated calls to saveStrings on the same file should fully overwrite
        the previous content with no stale data left behind.
        """
        db_path = tmp_path / "cycle.db"
        db = MyDB(str(db_path))

        db.saveStrings(["one", "two"])
        assert db.loadStrings() == ["one", "two"]

        db.saveStrings([])
        assert db.loadStrings() == []

        db.saveStrings(["final"])
        assert db.loadStrings() == ["final"]

    def it_interleaves_saveStrings_and_saveString_correctly(tmp_path: Path):
        """
        A4: Mixed usage of saveStrings (overwrite) and saveString (append)
        should behave consistently over time.
        """
        db_path = tmp_path / "mixed.db"
        db = MyDB(str(db_path))

        # Start with two items
        db.saveStrings(["a", "b"])
        assert db.loadStrings() == ["a", "b"]

        # Append one, then another
        db.saveString("c")
        assert db.loadStrings() == ["a", "b", "c"]

        # Overwrite the whole collection
        db.saveStrings(["X"])
        assert db.loadStrings() == ["X"]

        # Append again
        db.saveString("Y")
        assert db.loadStrings() == ["X", "Y"]
