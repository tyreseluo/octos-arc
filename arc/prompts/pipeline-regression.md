The finished web application failed its acceptance check (build, boot, the
GET / smoke, a page audit, or one of the requirement-derived browser
self-checks under checks/). The failure output is shown below. Fix the
application so the check passes, without breaking what already works.

You are editing an existing workspace: `frontend/src/*.html` (+ `assets/`),
`backend/server.js` (router on `process.env.PORT || {port}`; do not rewrite it),
`backend/routes/<area>.js`, `backend/store.js`, `backend/seeds/`, `backend/lib/`.
The workspace map at the end of the failure output lists every file and route.
Grep for the names a failure points at and read only those files or line
ranges before changing them; put independent reads in one response. Change files with edit_file — nothing you put in
chat is saved.

Rules:
- Fix the cause in the application code; never special-case the failure output.
- Keep every label, accessible name and route the application already exposes.
- Write only the app's own files under frontend/ and backend/. No reports,
  notes, summaries or other .md files: nobody reads them and they cost output.
- If the output below shows no failure, reply "nothing to fix" and stop.
{ports}
Finish by writing the files. Reply with one short sentence when done.
