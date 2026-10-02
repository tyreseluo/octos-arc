"""The template backend is the skeleton every generated app grows from: route
modules under backend/routes/, run-once seed modules under backend/seeds/.
These boot the real template with node, the way verify_node and the grader do."""
import json
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TemplateBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="arc-tpl-"))
        shutil.copytree(TEMPLATE, self.tmp / "app")
        self.app = self.tmp / "app"
        subprocess.run(["npm", "run", "build"], cwd=self.app / "frontend", check=True, capture_output=True)
        self.proc = None

    def tearDown(self):
        self.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel: str, text: str):
        path = self.app / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def start(self):
        self.port = free_port()
        self.proc = subprocess.Popen(["node", "server.js"], cwd=self.app / "backend",
                                     env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:"
                                          + __import__("os").environ.get("PATH", ""), "PORT": str(self.port)},
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close()
                return
            except OSError:
                time.sleep(0.05)
        self.fail(self.proc.stdout.read().decode())

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=5)
            self.proc.stdout.close()
            self.proc = None

    def call(self, method: str, path: str, body=None, form=False):
        data, headers = None, {}
        if body is not None:
            if form:
                data = urllib.parse.urlencode(body).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_should_serve_index_and_pages_when_no_route_claims_the_path(self):
        self.write("frontend/src/about.html", "<h1>About</h1>")
        subprocess.run(["npm", "run", "build"], cwd=self.app / "frontend", check=True, capture_output=True)
        self.start()
        self.assertEqual(self.call("GET", "/")[0], 200)
        self.assertIn("About", self.call("GET", "/about")[1])
        self.assertEqual(self.call("GET", "/api/health"), (200, '{"ok":true}'))
        self.assertEqual(self.call("GET", "/missing")[0], 404)

    def test_should_route_params_and_prefer_literal_paths_when_both_match(self):
        self.write("backend/routes/a_items.js", """
module.exports = (api) => {
  api.get("/api/items/:id", (req, res) => api.json(res, 200, { id: req.params.id, q: req.query.q }));
};""")
        self.write("backend/routes/b_new.js", """
module.exports = (api) => {
  api.get("/api/items/new", (req, res) => api.json(res, 200, { literal: true }));
  api.post("/api/items", async (req, res) => api.json(res, 201, await api.body(req)));
  api.page("/items/:id", "index.html");
};""")
        self.start()
        self.assertEqual(json.loads(self.call("GET", "/api/items/a%20b?q=x")[1]), {"id": "a b", "q": "x"})
        self.assertEqual(json.loads(self.call("GET", "/api/items/new")[1]), {"literal": True})
        self.assertEqual(self.call("POST", "/api/items", {"name": "n"}), (201, '{"name":"n"}'))
        self.assertEqual(json.loads(self.call("POST", "/api/items", {"a": "1"}, form=True)[1]), {"a": "1"})
        status, body = self.call("GET", "/items/42")
        self.assertEqual(status, 200)
        self.assertIn("<html", body)

    def test_should_run_each_seed_once_and_keep_edits_when_restarted(self):
        self.write("backend/seeds/a_users.js",
                   'module.exports = (s) => { s.collection("users").push({ name: "alice" }); };')
        self.write("backend/routes/users.js", """
const store = require("../store");
module.exports = (api) => {
  api.get("/api/users", (req, res) => api.json(res, 200, store.collection("users").map((u) => u.name)));
  api.post("/api/users/rename", async (req, res) => {
    store.collection("users")[0].name = (await api.body(req)).name; store.save(); api.json(res, 200, {});
  });
};""")
        self.start()
        self.assertEqual(json.loads(self.call("GET", "/api/users")[1]), ["alice"])
        self.call("POST", "/api/users/rename", {"name": "alicia"})
        self.stop()
        # A seed module added by a later requirement still reaches the existing store.
        self.write("backend/seeds/b_more.js",
                   'module.exports = (s) => { s.collection("users").push({ name: "bob" }); };')
        self.start()
        self.assertEqual(json.loads(self.call("GET", "/api/users")[1]), ["alicia", "bob"])
        self.stop()
        self.start()
        self.assertEqual(json.loads(self.call("GET", "/api/users")[1]), ["alicia", "bob"])


if __name__ == "__main__":
    unittest.main()
