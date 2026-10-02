# Web Template

The initial workspace the platform lays out from the submission bundle and
hands to `main.py` (`ARCBENCH_TEMPLATE_DIR`). Zero-dependency by design: the
container's route to npmjs is slow, so nothing here may require
`npm install`.

- `frontend/src/`: hand-written HTML/CSS/JS, one `.html` per route plus shared
  `assets/`. `npm run build` (frontend/package.json) copies `src/*` to
  `frontend/dist/` verbatim.
- `backend/server.js`: `npm start` runs it. A CommonJS Node http server with no
  dependencies on `process.env.PORT`: it loads every `backend/routes/*.js`
  module (one per API area), then serves `../frontend/dist` (`index.html` for
  `/`, `<name>.html` for `/<name>`) and answers 404 for anything else.
- `backend/store.js`: JSON persistence with run-once seed modules from
  `backend/seeds/`.

Small files, one per feature, keep every implementation turn's reads small:
later requirements add modules instead of re-reading one growing file.
