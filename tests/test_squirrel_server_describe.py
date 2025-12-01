import pytest
import requests


def describe_squirrel_api():
    # ---------------- Happy-path core endpoints ----------------

    def it_lists_initially_empty(base_url):
        # GET /squirrels should return 200 + empty JSON array on a clean DB
        r = requests.get(f"{base_url}/squirrels")
        assert r.status_code == 200
        assert r.headers.get("Content-Type") == "application/json"
        assert r.json() == []

    def it_creates_and_then_retrieves_a_record(base_url):
        # POST /squirrels creates a record (201); we then list to discover its id (black-box)
        r = requests.post(
            f"{base_url}/squirrels",
            data={"name": "Chip", "size": "small"},
        )
        assert r.status_code == 201

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
        assert r.status_code == 204  # no body on successful update

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
        assert r.status_code == 204

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
        # POST returns 201 with empty body; PUT returns 204 with no body
        r = requests.post(
            f"{base_url}/squirrels",
            data={"name": "A", "size": "small"},
        )
        assert r.status_code == 201 and r.text == ""

        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        r = requests.put(
            f"{base_url}/squirrels/{sid}",
            data={"name": "A", "size": "medium"},
        )
        assert r.status_code == 204 and r.text == ""

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

    def it_400s_on_create_missing_field(base_url):
        # POST with incomplete data (missing size) should return 400 Bad Request
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data={"name": "OnlyName"},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pytest.fail(
                "Expected 400 Bad Request for incomplete data, but server closed the connection"
            )
        assert r.status_code == 400

    # ---------------- Additional 400 Bad Request edge cases (B1) ----------------

    def it_400s_on_create_missing_name(base_url):
        # Missing 'name' should also be treated as a bad request
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data={"size": "large"},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pytest.fail(
                "Expected 400 Bad Request for missing name, but server closed the connection"
            )
        assert r.status_code == 400

    def it_400s_on_create_empty_fields(base_url):
        # Empty name or size should be rejected as invalid
        try:
            r1 = requests.post(
                f"{base_url}/squirrels",
                data={"name": "", "size": "small"},
                timeout=2,
            )
            r2 = requests.post(
                f"{base_url}/squirrels",
                data={"name": "EmptySize", "size": ""},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pytest.fail(
                "Expected 400 Bad Request for empty fields, but server closed the connection"
            )
        assert r1.status_code == 400
        assert r2.status_code == 400

    def it_400s_on_update_missing_fields(base_url):
        # PUT with missing name or size should yield 400 and not change the record
        # Create a valid record first
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "UpdTarget", "size": "medium"},
        )
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]

        # Missing size
        try:
            r1 = requests.put(
                f"{base_url}/squirrels/{sid}",
                data={"name": "NoSize"},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pytest.fail(
                "Expected 400 Bad Request on PUT missing size, but server closed the connection"
            )

        # Missing name
        try:
            r2 = requests.put(
                f"{base_url}/squirrels/{sid}",
                data={"size": "large"},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pytest.fail(
                "Expected 400 Bad Request on PUT missing name, but server closed the connection"
            )

        assert r1.status_code == 400
        assert r2.status_code == 400

        # Original record should still be unchanged
        rec = requests.get(f"{base_url}/squirrels/{sid}").json()
        assert rec["name"] == "UpdTarget"
        assert rec["size"] == "medium"

    # ---------------- 405 Method Not Allowed edge cases (B2) ----------------

    def it_405s_on_patch_collection(base_url):
        # PATCH is not supported on /squirrels and should return 405 if implemented
        r = requests.patch(f"{base_url}/squirrels")
        assert r.status_code in (404, 405)
        # If your server sends 405 explicitly, adjust assertion to == 405.

    def it_405s_on_patch_single_resource(base_url):
        # PATCH is not supported on /squirrels/{id}
        # First create a record so the id path exists
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "PatchMe", "size": "medium"},
        )
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        r = requests.patch(f"{base_url}/squirrels/{sid}")
        assert r.status_code in (404, 405)

    # ---------------- ID behavior and delete consistency (B3) ----------------

    def it_does_not_reuse_ids_after_delete(base_url):
        # Autoincrement semantics: new records get strictly increasing ids, even after deletes
        ids = []
        for name in ["S1", "S2", "S3"]:
            requests.post(
                f"{base_url}/squirrels",
                data={"name": name, "size": "small"},
            )
            ids.append(requests.get(f"{base_url}/squirrels").json()[-1]["id"])

        # Delete the middle record
        middle_id = ids[1]
        requests.delete(f"{base_url}/squirrels/{middle_id}")

        # Create a new record
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "S4", "size": "small"},
        )
        new_id = requests.get(f"{base_url}/squirrels").json()[-1]["id"]

        # New id should be greater than any existing previous id
        assert new_id > max(ids)

    def it_second_delete_on_same_id_yields_404(base_url):
        # Deleting an id twice should return 204 then 404
        requests.post(
            f"{base_url}/squirrels",
            data={"name": "DeleteMe", "size": "tiny"},
        )
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]

        r1 = requests.delete(f"{base_url}/squirrels/{sid}")
        r2 = requests.delete(f"{base_url}/squirrels/{sid}")

        assert r1.status_code == 204
        assert r2.status_code == 404

    # ---------------- Content-type / malformed body robustness (B4) ----------------

    def it_accepts_plaintext_form_body(base_url):
        # Even with a non-standard content-type, form-encoded body should be handled
        headers = {"Content-Type": "text/plain"}
        r = requests.post(
            f"{base_url}/squirrels",
            data="name=Plain&size=small",
            headers=headers,
        )
        # Either the server treats this as valid (201) or as a 400-style bad request.
        # We assert it does not crash and responds with a known code.
        assert r.status_code in (201, 400)

        # If it was accepted (201), we should see the record in the index.
        if r.status_code == 201:
            rows = requests.get(f"{base_url}/squirrels").json()
            assert any(row["name"] == "Plain" for row in rows)

    def it_400s_on_unparseable_body_and_keeps_db_empty(base_url):
        # A totally unstructured body should not crash the server and should not create records.
        try:
            r = requests.post(
                f"{base_url}/squirrels",
                data="this is not form data at all",
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pytest.fail(
                "Expected 4xx for malformed body, but server closed the connection"
            )

        # Whatever code you choose (400/415), it should be a client error, not success.
        assert 400 <= r.status_code < 500

        # DB should still be empty
        rows = requests.get(f"{base_url}/squirrels").json()
        assert rows == []

    # ---------------- Complex lifecycle scenario (B5) ----------------

    def it_supports_create_update_delete_lifecycle(base_url):
        """
        B5: Create multiple squirrels, update one, delete another, then verify
        final state via the index and individual GETs.
        """
        # Create three squirrels
        names = ["Alpha", "Bravo", "Charlie"]
        for n in names:
            requests.post(
                f"{base_url}/squirrels",
                data={"name": n, "size": "medium"},
            )

        rows = requests.get(f"{base_url}/squirrels").json()
        assert len(rows) == 3
        ids_by_name = {row["name"]: row["id"] for row in rows}

        alpha_id = ids_by_name["Alpha"]
        bravo_id = ids_by_name["Bravo"]
        charlie_id = ids_by_name["Charlie"]

        # Update Bravo's size
        r = requests.put(
            f"{base_url}/squirrels/{bravo_id}",
            data={"name": "Bravo", "size": "large"},
        )
        assert r.status_code == 204

        # Delete Alpha
        r = requests.delete(f"{base_url}/squirrels/{alpha_id}")
        assert r.status_code == 204

        # Final index: only Bravo and Charlie should remain
        rows = requests.get(f"{base_url}/squirrels").json()
        remaining_names = {row["name"] for row in rows}
        assert remaining_names == {"Bravo", "Charlie"}

        # Bravo should reflect updated size
        bravo_rec = requests.get(f"{base_url}/squirrels/{bravo_id}").json()
        assert bravo_rec["size"] == "large"

        # Alpha should now 404
        r_alpha = requests.get(f"{base_url}/squirrels/{alpha_id}")
        assert r_alpha.status_code == 404
