import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from squirrel_db import SquirrelDB


class SquirrelServerHandler(BaseHTTPRequestHandler):
    # HTTP METHODS

    def do_GET(self):
        resourceName, resourceId = self.parsePath()
        if resourceName == "squirrels":
            if resourceId:
                self.handleSquirrelsRetrieve(resourceId)
            else:
                self.handleSquirrelsIndex()
        else:
            self.handle404()

    def do_POST(self):
        resourceName, resourceId = self.parsePath()
        if resourceName == "squirrels":
            if resourceId:
                # POST with an id in the path is not allowed for this resource.
                self.handle404()
            else:
                self.handleSquirrelsCreate()
        else:
            self.handle404()

    def do_PUT(self):
        resourceName, resourceId = self.parsePath()
        if resourceName == "squirrels":
            if resourceId:
                self.handleSquirrelsUpdate(resourceId)
            else:
                # PUT without an id is invalid for this API.
                self.handle404()
        else:
            self.handle404()

    def do_DELETE(self):
        resourceName, resourceId = self.parsePath()
        if resourceName == "squirrels":
            if resourceId:
                self.handleSquirrelsDelete(resourceId)
            else:
                # DELETE without an id is invalid for this API.
                self.handle404()
        else:
            self.handle404()

    def do_PATCH(self):
        """
        PATCH is not supported by this API. Explicitly return 405 instead of
        the default 501 from BaseHTTPRequestHandler.
        """
        self.send_response(405)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"405 Method Not Allowed")

    # HELPERS

    def getRequestData(self):
        """
        Read and parse the request body as URL-encoded form data.

        Returns a dict of single string values:
            {"name": "...", "size": "...", ...}

        If the body cannot be parsed, returns an empty dict.
        """
        try:
            length_header = self.headers.get("Content-Length")
            if not length_header:
                return {}
            length = int(length_header)
        except (TypeError, ValueError):
            # Missing or invalid Content-Length
            return {}

        try:
            body = self.rfile.read(length).decode("utf-8")
        except Exception:
            return {}

        data = parse_qs(body)
        # Convert {"key": ["val", ...]} to {"key": "val"}
        return {key: vals[0] for key, vals in data.items()}

    def parsePath(self):
        """
        Split paths like:
          /squirrels          -> ("squirrels", None)
          /squirrels/123      -> ("squirrels", "123")
          /                   -> ("", None)
        """
        if self.path.startswith("/"):
            parts = self.path[1:].split("/")
            resourceName = parts[0] if parts[0] else ""
            resourceId = None
            if len(parts) > 1 and parts[1]:
                resourceId = parts[1]
            return (resourceName, resourceId)
        return ("", None)

    def handle400(self, message="400 Bad Request"):
        """Send a simple 400 response with a plain-text message."""
        self.send_response(400)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    # ACTIONS

    def handleSquirrelsIndex(self):
        db = SquirrelDB()
        squirrelsList = db.getSquirrels()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(squirrelsList).encode("utf-8"))

    def handleSquirrelsRetrieve(self, squirrelId):
        db = SquirrelDB()
        squirrel = db.getSquirrel(squirrelId)
        if squirrel:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(squirrel).encode("utf-8"))
        else:
            self.handle404()

    def handleSquirrelsCreate(self):
        """
        Create a new squirrel from form data.

        Required form fields:
          - name (non-empty)
          - size (non-empty)

        On success: 201 Created with empty body.
        On bad input: 400 Bad Request (tests expect server not to crash).
        """
        db = SquirrelDB()
        body = self.getRequestData()

        name = body.get("name")
        size = body.get("size")

        # Validate required fields: must both be present and non-empty.
        if not name or not size:
            self.handle400("Missing or empty 'name' or 'size'")
            return

        try:
            db.createSquirrel(name, size)
        except Exception:
            # Any unexpected error while creating is treated as bad request here
            # rather than crashing the connection.
            self.handle400("Could not create squirrel with provided data")
            return

        self.send_response(201)
        self.end_headers()

    def handleSquirrelsUpdate(self, squirrelId):
        """
        Update an existing squirrel record.

        Required form fields:
          - name (non-empty)
          - size (non-empty)

        On success: 204 No Content.
        On missing record: 404.
        On bad input: 400 Bad Request.
        """
        db = SquirrelDB()
        squirrel = db.getSquirrel(squirrelId)
        if not squirrel:
            self.handle404()
            return

        body = self.getRequestData()
        name = body.get("name")
        size = body.get("size")

        # Validate required fields: must both be present and non-empty.
        if not name or not size:
            self.handle400("Missing or empty 'name' or 'size'")
            return

        try:
            db.updateSquirrel(squirrelId, name, size)
        except Exception:
            # Treat unexpected update errors as bad inputs for this assignment.
            self.handle400("Could not update squirrel with provided data")
            return

        self.send_response(204)
        self.end_headers()

    def handleSquirrelsDelete(self, squirrelId):
        db = SquirrelDB()
        squirrel = db.getSquirrel(squirrelId)
        if squirrel:
            db.deleteSquirrel(squirrelId)
            self.send_response(204)
            self.end_headers()
        else:
            self.handle404()

    def handle404(self):
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"404 Not Found")


def run():
    print("squirrel_server running at 127.0.0.1:8080")
    listen = ("127.0.0.1", 8080)
    server = HTTPServer(listen, SquirrelServerHandler)
    server.serve_forever()


if __name__ == "__main__":
    run()
