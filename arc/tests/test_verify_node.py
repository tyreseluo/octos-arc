"""The page audit catches the UI defects requirements imply, on HTML we wrote
for this test -- never on evaluation material."""
import tempfile
import unittest
from pathlib import Path

import verify_node


class AuditPages(unittest.TestCase):
    def audit(self, html: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            (dist / "index.html").write_text(html)
            return verify_node.audit_pages(dist)

    def test_duplicate_named_entry_on_one_page_is_flagged(self):
        problems = self.audit('<a href="/signin">Sign in</a><p><a href="/signin">Sign in</a></p>')
        self.assertTrue(any("Sign in" in p and "links named" in p for p in problems))

    def test_single_named_entry_passes(self):
        self.assertEqual(self.audit('<a href="/signin">Sign in</a><a href="/up">Sign up</a>'), [])

    def test_input_without_label_is_flagged(self):
        problems = self.audit('<input type="text" id="u">')
        self.assertTrue(any("no visible label" in p for p in problems))

    def test_input_with_label_for_aria_or_wrapping_passes(self):
        self.assertEqual(self.audit('<label for="u">User</label><input id="u">'), [])
        self.assertEqual(self.audit('<input aria-label="User">'), [])
        self.assertEqual(self.audit('<label>User <input type="text"></label>'), [])

    def test_password_and_checkbox_need_labels_too(self):
        self.assertTrue(self.audit('<input type="checkbox">'))
        self.assertFalse(self.audit('<label for="t">Terms</label><input type="checkbox" id="t">'))

    def test_unnamed_button_is_flagged(self):
        self.assertTrue(self.audit('<button></button>'))
        self.assertEqual(self.audit('<button>Go</button>'), [])
        self.assertEqual(self.audit('<button aria-label="Go"></button>'), [])

    def test_hidden_and_submit_inputs_are_exempt(self):
        self.assertEqual(self.audit('<input type="hidden"><input type="submit" value="Go">'), [])


class CrashPattern(unittest.TestCase):
    def test_crash_signatures(self):
        self.assertTrue(verify_node.CRASH_RE.search("Error [ERR_HTTP_HEADERS_SENT]: nope"))
        self.assertTrue(verify_node.CRASH_RE.search("Traceback (most recent call last):"))
        self.assertFalse(verify_node.CRASH_RE.search("backend listening on port 3000"))


class E2eFileList(unittest.TestCase):
    """A grouped implement node's several self-checks run against ONE shared
    boot via --e2e-list; a single (ungrouped) node still uses --e2e alone."""

    def test_e2e_list_wins_and_splits_on_comma(self):
        self.assertEqual(
            verify_node.parse_e2e_files("checks/ignored.mjs", "checks/a.mjs,checks/b.mjs"),
            ["checks/a.mjs", "checks/b.mjs"])

    def test_single_e2e_used_when_no_list(self):
        self.assertEqual(verify_node.parse_e2e_files("checks/a.mjs", None), ["checks/a.mjs"])

    def test_neither_given_is_empty(self):
        self.assertEqual(verify_node.parse_e2e_files(None, None), [])

    def test_e2e_list_drops_blanks_from_stray_commas(self):
        self.assertEqual(verify_node.parse_e2e_files(None, "checks/a.mjs,,checks/b.mjs,"),
                         ["checks/a.mjs", "checks/b.mjs"])


if __name__ == "__main__":
    unittest.main()


class SelfCheckModuleResolution(unittest.TestCase):
    """Self-checks are ES modules (`import { chromium } from '@playwright/test'`).
    Node never consults NODE_PATH for `import`, so pointing NODE_PATH at the
    runner's Playwright left every .mjs check failing with ERR_MODULE_NOT_FOUND
    and every requirement burning its repair rounds on a broken checker."""

    def run_check(self, script: str, name: str = "x.mjs") -> int:
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pwroot"
            pkg = root / "node_modules" / "@playwright" / "test"
            pkg.mkdir(parents=True)
            (pkg / "package.json").write_text('{"name":"@playwright/test","version":"0.0.0","main":"index.js"}')
            (pkg / "index.js").write_text("exports.chromium = 'stub';")
            checks = Path(tmp) / "run" / "checks"
            checks.mkdir(parents=True)
            (checks / name).write_text(script)
            old = os.environ.get("OCTOS_ARC_PLAYWRIGHT_ROOT")
            os.environ["OCTOS_ARC_PLAYWRIGHT_ROOT"] = str(root)
            try:
                return verify_node.playwright_run([checks / name], dict(os.environ), 9)
            finally:
                if old is None:
                    os.environ.pop("OCTOS_ARC_PLAYWRIGHT_ROOT")
                else:
                    os.environ["OCTOS_ARC_PLAYWRIGHT_ROOT"] = old

    def test_should_resolve_playwright_when_check_is_an_es_module(self):
        rc = self.run_check("import { chromium } from '@playwright/test';\n"
                            "if (chromium !== 'stub') process.exit(3);\n")
        self.assertEqual(rc, 0)

    def test_should_still_resolve_playwright_when_check_is_commonjs(self):
        rc = self.run_check("const { chromium } = require('@playwright/test');\n"
                            "if (chromium !== 'stub') process.exit(3);\n", name="x.cjs")
        self.assertEqual(rc, 0)


class WorkspaceMap(unittest.TestCase):
    """The next implement node starts from this map instead of list_dir and a
    re-read of every file (measured: 90 reads vs 18 edits on five requirements)."""

    def make_app(self, root: Path):
        (root / "backend" / "routes").mkdir(parents=True)
        (root / "backend" / "data").mkdir()
        (root / "frontend" / "src").mkdir(parents=True)
        (root / "backend" / "server.js").write_text("a\nb\n")
        (root / "backend" / "data" / "store.json").write_text("{}")
        (root / "backend" / "routes" / "items.js").write_text(
            'module.exports = (api) => {\n'
            '  api.get("/api/items", list);\n'
            "  api.post('/api/items/:id/close', close);\n"
            '  api.page("/items/:id", "item.html");\n'
            '};\n')
        (root / "frontend" / "src" / "index.html").write_text("<p>x</p>\n")

    def test_should_list_routes_per_module_when_backend_registers_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_app(Path(tmp))
            text = verify_node.inventory(Path(tmp))
        self.assertIn("backend/routes/items.js (5 lines): GET /api/items, POST /api/items/:id/close, "
                      "page /items/:id -> item.html", text)
        self.assertIn("backend/server.js (2 lines)", text)
        self.assertIn("frontend/src/index.html (1 lines)", text)

    def test_should_leave_out_runtime_data_when_mapping_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_app(Path(tmp))
            self.assertNotIn("store.json", verify_node.inventory(Path(tmp)))

    def test_should_print_the_map_when_seeding_the_run_dir(self):
        import contextlib, io, os
        with tempfile.TemporaryDirectory() as tmp:
            src, run = Path(tmp) / "src", Path(tmp) / "run"
            self.make_app(src)
            run.mkdir()
            cwd, buf = os.getcwd(), io.StringIO()
            os.chdir(run)
            try:
                with contextlib.redirect_stdout(buf):
                    verify_node.seed(src)
            finally:
                os.chdir(cwd)
        self.assertIn("GET /api/items", buf.getvalue())
