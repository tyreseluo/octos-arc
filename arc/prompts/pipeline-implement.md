Implement requirement {node_id} of this web application, then stop.

{description}

Public acceptance example (implement the FULL requirement, not just this case):
{spec}

You are editing an existing workspace. Write files with the write_file tool —
nothing you put in chat is saved, only tool calls change the app.

Layout (already scaffolded; extend it by ADDING small files, keep each file
under ~300 lines and split by feature instead of growing one file):
- `frontend/src/<page>.html` — one file per route (`index.html` is `/`,
  `<name>.html` is `/<name>`). Shared client code and styles go in
  `frontend/src/assets/*.js` / `*.css`, loaded with `/assets/<file>`.
- `backend/server.js` — the zero-dependency entry and router on
  `process.env.PORT || {port}`. Do not rewrite it: its header comment documents
  the `api` helpers. Each API area is its own module `backend/routes/<area>.js`
  (`module.exports = (api) => { api.get("/api/items", handler) }`);
  `api.page("/items/:id", "item.html")` maps a dynamic URL to a page.
- `backend/store.js` — JSON persistence: `store.collection(name)`, then
  `store.save()` after every change. Seed data goes in
  `backend/seeds/<area>.js` (`module.exports = (store) => { store.collection("users").push(user) }`); each seed
  module runs once per store, so add a new seed module rather than editing an
  old one.
- Shared backend helpers (sessions, validation, hashing) go in `backend/lib/*.js`.
- The two package.json manifests already exist (build copies src/* to dist,
  start runs server.js). Update them only if a dependency or build step changes.
- If the workspace already holds an app with a different layout, keep that
  layout and add to it the same way: small files, one per feature.

Reading (input tokens are the main cost): the workspace map at the end of your
input lists every app file, its line count and each route module's endpoints —
use it instead of list_dir. grep for the names you need and read only the files,
or line ranges, you will change or call; `backend/server.js`, `backend/store.js`
and the package.json manifests are described above, so do not read them. Put
independent tool calls in ONE response (read three files at once, not one per
turn). Never re-read a file you already read unless you changed it since.
Change existing files with edit_file; use write_file for new files.

Rules:
- Build ONLY what this requirement needs: the smallest app that satisfies it.
  Later requirements extend the same files; do not build their features early.
- Implement for general valid inputs and preserve behaviour already built by
  earlier requirements. Never hardcode the values the acceptance example uses.
- Use the exact labels, accessible names and test ids the requirement names.
- One primary entry per action name per page: two links or buttons with the
  same accessible name on one page are rejected. Every form control needs a
  visible label; every button and link needs an accessible name.
- Navigation completeness: every entry point this requirement names (links,
  tabs, menu items, buttons) must exist on the page the requirement puts it
  on, be visible, and lead to a real route — no dead entries.
- Seed data: provision every account, organization, team, repository and
  relationship the requirement's scenarios name, with the exact names, roles,
  ownership and visibility the requirement states, in this requirement's own
  `backend/seeds/<area>.js`. Every seeded account must be able to sign in with
  the stated credential.
- Write only the app's own files under frontend/ and backend/. No reports,
  notes, summaries or other .md files: nobody reads them and they cost output.
- Prefer zero runtime dependencies; if you must install, the registry is
  already pointed at the official npm registry.
{ports}
Then write your own acceptance check as `checks/{node_id}.mjs`: a Node script
that derives its steps from THIS requirement's text above (never from any
external test file), launches chromium from '@playwright/test'
(`import { chromium, expect } from '@playwright/test'`), opens
`process.env.E2E_BASE_URL`, and walks EVERY scenario the requirement lists,
in order: for each GIVEN/WHEN/THEN it opens the named page, clicks, fills,
and asserts the expected visible result with `expect` — when the requirement
names seeded accounts or entry points, the script signs in as each named
account and opens each named entry to prove they exist and work. Print one
`SELF-CHECK OK` line per scenario and exit 0; any failed expectation must
exit non-zero. Keep the whole script under 120 lines and under 4 minutes.
The pipeline runs it against your freshly built app right after this turn and
shows you its output on failure.

If a previous acceptance failure is shown to you below, fix exactly what it
reports — do not rewrite working code around it.

Finish by writing the files. Reply with one short sentence when done.
