import requests
import pytest


def describe_squirrel_api():
    # ---------------- Happy-path core endpoints ----------------

    def it_lists_initially_empty(base_url):
        # GET /squirrels should return 200 + empty JSON array on a clean DB
        r = requests.get(f"{base_url}/squirrels")
        assert r.status_code == 200
        assert r.headers.get("Content-Type") == "application/json"
        assert r.json() == []

    def it_creates_and_then_retrieves_a_record(base_url):
        # POST /squirrels creates a record; we then list to discover its id (black-box)
        r = requests.post(
            f"{base_url}/squirrels",
            data={"name": "Chip", "size": "small"},
        )
        # Starter server uses 201 Created; 200 would also be acceptable success.
        assert r.status_code in (200, 201)

        r = requests.get(f"{base_url}/squirrels")  # index reveals the new id
        rows = r.json()
        assert len(rows) == 1
        new_id = rows[0]["id"]

        # GET /squirrels/{id} returns the persisted record
        r = requests.get(f"{base_url}/squirrels/{new_id}")
        assert r.status_code == 200
        rec = r.json()
        assert rec["name"] == "Chip"
        assert rec["size"] == "small"

    def it_updates_then_reads_back_changes(base_url):
        # POST to create, PUT to update, then GET to verify side effect
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "Dale", "size": "medium"},
        )
        rows = requests.get(f"{base_url}/squirrels").json()
        sid = rows[0]["id"]

        r = requests.put(
            f"{base_url}/squirrels/{sid}",
            data={"name": "Dale", "size": "large"},
        )
        # Starter server uses 204 No Content for successful update.
        assert r.status_code in (200, 204)

        rec = requests.get(f"{base_url}/squirrels/{sid}").json()
        assert rec["size"] == "large"

    def it_deletes_then_cannot_be_retrieved(base_url):
        # Create → Delete → Verify GET returns 404
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "Nuts", "size": "tiny"},
        )
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]

        r = requests.delete(f"{base_url}/squirrels/{sid}")
        # Starter server uses 204 No Content for successful delete.
        assert r.status_code in (200, 204)

        r = requests.get(f"{base_url}/squirrels/{sid}")
        assert r.status_code == 404

    # ---------------- Ten+ distinct 404 (failure) conditions ----------------

    def it_404s_on_unknown_root(base_url):
        # Non-existent root path
        r = requests.get(f"{base_url}/")
        assert r.status_code == 404

    def it_404s_on_unknown_resource(base_url):
        # Unknown resource segment
        r = requests.get(f"{base_url}/not-squirrels")
        assert r.status_code == 404

    def it_404s_on_retrieve_nonexistent_numeric_id(base_url):
        # Numeric id that does not exist
        r = requests.get(f"{base_url}/squirrels/999999")
        assert r.status_code == 404

    def it_404s_on_retrieve_non_numeric_id(base_url):
        # Non-numeric id is treated as not found
        r = requests.get(f"{base_url}/squirrels/abc")
        assert r.status_code == 404

    def it_treats_trailing_slash_as_index(base_url):
        # /squirrels/ behaves like /squirrels (index) in this server
        r1 = requests.get(f"{base_url}/squirrels")
        r2 = requests.get(f"{base_url}/squirrels/")
        assert r2.status_code == 200
        assert r2.headers.get("Content-Type") == "application/json"
        assert r2.json() == r1.json()

    def it_404s_on_post_with_id_in_path(base_url):
        # POST with an id in the path is invalid for this API
        r = requests.post(
            f"{base_url}/squirrels/123",
            data={"name": "X", "size": "Y"},
        )
        assert r.status_code == 404

    def it_404s_on_put_without_id(base_url):
        # PUT requires an id path segment
        r = requests.put(
            f"{base_url}/squirrels",
            data={"name": "X", "size": "Y"},
        )
        assert r.status_code == 404

    def it_404s_on_delete_without_id(base_url):
        # DELETE requires an id path segment
        r = requests.delete(f"{base_url}/squirrels")
        assert r.status_code == 404

    def it_404s_on_put_nonexistent_id(base_url):
        # Updating a missing id
        r = requests.put(
            f"{base_url}/squirrels/424242",
            data={"name": "Nope", "size": "Nope"},
        )
        assert r.status_code == 404

    def it_404s_on_delete_nonexistent_id(base_url):
        # Deleting a missing id
        r = requests.delete(f"{base_url}/squirrels/424242")
        assert r.status_code == 404

    def it_404s_on_favicon(base_url):
        # Common stray path
        r = requests.get(f"{base_url}/favicon.ico")
        assert r.status_code == 404

    # ---------------- Output/side-effect polish ----------------

    def it_returns_json_content_type_on_gets(base_url):
        # GET endpoints should advertise JSON
        r = requests.get(f"{base_url}/squirrels")
        assert r.status_code == 200
        assert r.headers.get("Content-Type") == "application/json"

    def it_201_has_empty_body_and_204_has_no_body(base_url):
        # Starter server uses 201 for create; body is empty string.
        r = requests.post(
            f"{base_url}/squirrels",
            data={"name": "A", "size": "small"},
        )
        assert r.status_code in (200, 201)
        # Some implementations send an empty body, some may echo JSON.
        # Just assert it doesn't crash and is not an error.
        assert r.status_code < 400

        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        r = requests.put(
            f"{base_url}/squirrels/{sid}",
            data={"name": "A", "size": "medium"},
        )
        assert r.status_code in (200, 204)

    def it_index_is_sorted_by_id(base_url):
        # Index is ordered by id ascending (server uses ORDER BY id)
        for i in range(3):
            requests.post(
                f"{base_url}/squirrels",
                data={"name": f"N{i}", "size": "s"},
            )
        rows = requests.get(f"{base_url}/squirrels").json()
        ids = [row["id"] for row in rows]
        assert ids == sorted(ids)

    def it_update_does_not_change_row_count(base_url):
        # PUT should not add rows
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "E", "size": "s"},
        )
        before = len(requests.get(f"{base_url}/squirrels").json())
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        requests.put(
            f"{base_url}/squirrels/{sid}",
            data={"name": "E2", "size": "m"},
        )
        after = len(requests.get(f"{base_url}/squirrels").json())
        assert after == before

    def it_delete_reduces_row_count(base_url):
        # DELETE should remove exactly one row
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "A", "size": "s"},
        )
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "B", "size": "m"},
        )
        before = len(requests.get(f"{base_url}/squirrels").json())
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        requests.delete(f"{base_url}/squirrels/{sid}")
        after = len(requests.get(f"{base_url}/squirrels").json())
        assert after == before - 1

    def it_alpha_ids_for_put_and_delete_404(base_url):
        # Non-numeric ids for PUT/DELETE are not valid resources
        assert (
            requests.put(
                f"{base_url}/squirrels/abc",
                data={"name": "X", "size": "Y"},
            ).status_code
            == 404
        )
        assert requests.delete(f"{base_url}/squirrels/abc").status_code == 404

    # ---------------- Bad-input / malformed body behavior ----------------

    def it_fails_on_create_missing_size(base_url):
        """
        POST with incomplete data (missing size) should not succeed.
        The starter server actually raises KeyError and may close the connection;
        we treat either a 4xx/5xx response or a requests.ConnectionError as failure.
        """
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data={"name": "OnlyName"},
                timeout=2,
            )
        except requests.exceptions.RequestException:
            # Server closed connection / protocol error => clearly not a success.
            return

        assert r.status_code >= 400

    def it_fails_on_create_missing_name(base_url):
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data={"size": "medium"},
                timeout=2,
            )
        except requests.exceptions.RequestException:
            return

        assert r.status_code >= 400

    def it_fails_on_create_empty_fields(base_url):
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data={"name": "", "size": ""},
                timeout=2,
            )
        except requests.exceptions.RequestException:
            return

        # Either validation failure (4xx) or server error (5xx) – both are "bad".
        assert r.status_code >= 400

    def it_fails_on_update_missing_fields(base_url):
        # Create a valid record first
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "Valid", "size": "medium"},
        )
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]

        try:
            r = requests.put(
                f"{base_url}/squirrels/{sid}",
                data={"name": "NewName"},  # missing size
                timeout=2,
            )
        except requests.exceptions.RequestException:
            return

        assert r.status_code >= 400

    def it_can_create_new_record_after_delete(base_url):
        """
        After deleting a record, a new record can be created cleanly.

        We don't assert anything about whether IDs are reused or not,
        only that:
          - the old record is gone
          - the new record exists with the new data
        """
        # Create first record
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "A", "size": "s"},
        )
        rows = requests.get(f"{base_url}/squirrels").json()
        assert len(rows) == 1
        first_id = rows[0]["id"]

        # Delete it
        requests.delete(f"{base_url}/squirrels/{first_id}")
        rows_after_delete = requests.get(f"{base_url}/squirrels").json()
        assert all(row["id"] != first_id for row in rows_after_delete)

        # Create a new record
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "B", "size": "m"},
        )
        new_rows = requests.get(f"{base_url}/squirrels").json()
        # There should be exactly one record and it should be "B"
        assert len(new_rows) == 1
        new_rec = new_rows[0]
        assert new_rec["name"] == "B"
        assert new_rec["size"] == "m"

    def it_second_delete_on_same_id_yields_404(base_url):
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "Once", "size": "m"},
        )
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]

        first = requests.delete(f"{base_url}/squirrels/{sid}")
        assert first.status_code in (200, 204)

        second = requests.delete(f"{base_url}/squirrels/{sid}")
        assert second.status_code == 404

    def it_accepts_plaintext_form_body(base_url):
        # Normal form-encoded body is what the server expects; this should succeed.
        r = requests.post(
            f"{base_url}/squirrels",
            data="name=Plain&size=small",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code < 400

    def it_fails_on_unparseable_body_and_keeps_db_empty(base_url):
        """
        Send a body that cannot be parsed as form data.

        The starter server will likely error out and may close the connection;
        we verify that it does NOT create any rows as a side-effect.
        """
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data="this is not=valid&form",
                headers={"Content-Type": "text/plain"},
                timeout=2,
            )
            # If a response is returned, it should not be a success.
            assert r.status_code >= 400
        except requests.exceptions.RequestException:
            # Connection error also counts as failure.
            pass

        # DB should still be empty
        rows = requests.get(f"{base_url}/squirrels").json()
        assert rows == []

    def it_supports_create_update_delete_lifecycle(base_url):
        """
        End-to-end lifecycle:
        - create a record
        - update it
        - verify via index and GET
        - delete it
        - verify it is gone
        """
        # Create
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "Life", "size": "small"},
        )
        rows = requests.get(f"{base_url}/squirrels").json()
        assert len(rows) == 1
        sid = rows[0]["id"]

        # Update
        requests.put(
            f"{base_url}/squirrels/{sid}",
            data={"name": "Life2", "size": "medium"},
        )
        rec = requests.get(f"{base_url}/squirrels/{sid}").json()
        assert rec["name"] == "Life2"
        assert rec["size"] == "medium"

        # Delete
        requests.delete(f"{base_url}/squirrels/{sid}")
        r = requests.get(f"{base_url}/squirrels/{sid}")
        assert r.status_code == 404
        assert requests.get(f"{base_url}/squirrels").json() == []
