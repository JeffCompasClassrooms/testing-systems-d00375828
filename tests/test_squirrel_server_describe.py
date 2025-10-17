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
        r = requests.post(f"{base_url}/squirrels", data={"name": "Chip", "size": "small"})
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
        requests.post(f"{base_url}/squirrels", data={"name": "Dale", "size": "medium"})
        rows = requests.get(f"{base_url}/squirrels").json()
        sid = rows[0]["id"]

        r = requests.put(f"{base_url}/squirrels/{sid}", data={"name": "Dale", "size": "large"})
        assert r.status_code == 204  # no body on successful update

        rec = requests.get(f"{base_url}/squirrels/{sid}").json()
        assert rec["size"] == "large"

    def it_deletes_then_cannot_be_retrieved(base_url):
        # Create → Delete → Verify GET returns 404
        requests.post(f"{base_url}/squirrels", data={"name": "Nuts", "size": "tiny"})
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
        r = requests.post(f"{base_url}/squirrels/123", data={"name": "X", "size": "Y"})
        assert r.status_code == 404

    def it_404s_on_put_without_id(base_url):
        # PUT requires an id path segment
        r = requests.put(f"{base_url}/squirrels", data={"name": "X", "size": "Y"})
        assert r.status_code == 404

    def it_404s_on_delete_without_id(base_url):
        # DELETE requires an id path segment
        r = requests.delete(f"{base_url}/squirrels")
        assert r.status_code == 404

    def it_404s_on_put_nonexistent_id(base_url):
        # Updating a missing id
        r = requests.put(f"{base_url}/squirrels/424242", data={"name": "Nope", "size": "Nope"})
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
        r = requests.post(f"{base_url}/squirrels", data={"name": "A", "size": "small"})
        assert r.status_code == 201 and r.text == ""

        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        r = requests.put(f"{base_url}/squirrels/{sid}", data={"name": "A", "size": "medium"})
        assert r.status_code == 204 and r.text == ""

    def it_index_is_sorted_by_id(base_url):
        # Index is ordered by id ascending (server uses ORDER BY id)
        for i in range(3):
            requests.post(f"{base_url}/squirrels", data={"name": f"N{i}", "size": "s"})
        rows = requests.get(f"{base_url}/squirrels").json()
        ids = [row["id"] for row in rows]
        assert ids == sorted(ids)

    def it_update_does_not_change_row_count(base_url):
        # PUT should not add rows
        requests.post(f"{base_url}/squirrels", data={"name": "E", "size": "s"})
        before = len(requests.get(f"{base_url}/squirrels").json())
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        requests.put(f"{base_url}/squirrels/{sid}", data={"name": "E2", "size": "m"})
        after = len(requests.get(f"{base_url}/squirrels").json())
        assert after == before

    def it_delete_reduces_row_count(base_url):
        # DELETE should remove exactly one row
        requests.post(f"{base_url}/squirrels", data={"name": "A", "size": "s"})
        requests.post(f"{base_url}/squirrels", data={"name": "B", "size": "m"})
        before = len(requests.get(f"{base_url}/squirrels").json())
        sid = requests.get(f"{base_url}/squirrels").json()[0]["id"]
        requests.delete(f"{base_url}/squirrels/{sid}")
        after = len(requests.get(f"{base_url}/squirrels").json())
        assert after == before - 1

    def it_alpha_ids_for_put_and_delete_404(base_url):
        # Non-numeric ids for PUT/DELETE are not valid resources
        assert requests.put(f"{base_url}/squirrels/abc", data={"name": "X", "size": "Y"}).status_code == 404
        assert requests.delete(f"{base_url}/squirrels/abc").status_code == 404

    def it_fails_on_create_missing_field(base_url):
        # POST missing a required field should not succeed (error or connection abort)
        try:
            r = requests.post(f"{base_url}/squirrels", data={"name": "OnlyName"}, timeout=2)
            assert r.status_code >= 400
        except requests.exceptions.ConnectionError:
            pass
