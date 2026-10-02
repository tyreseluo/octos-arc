// JSON persistence. Memory is the source of truth; every change is written
// synchronously (temp file + rename), so parallel requests never lose an
// update. Call store.save() after each mutation.
//
// Seed data lives in backend/seeds/<area>.js, one module per area:
//   module.exports = (store) => { store.collection("users").push({...}); };
// Each seed module runs ONCE per store, in name order, the first time the
// store sees it -- so a seed added later still reaches an existing store, and
// later startups keep user edits and deletions.
"use strict";

const fs = require("fs");
const path = require("path");

const FILE = process.env.DATA_FILE || path.join(__dirname, "data", "store.json");
const SEEDS_DIR = path.join(__dirname, "seeds");

let db = {};
try {
  db = JSON.parse(fs.readFileSync(FILE, "utf8"));
} catch {
  db = {};
}
if (!Array.isArray(db._seeded)) db._seeded = [];
if (typeof db._seq !== "object" || db._seq === null) db._seq = {};

const store = {
  db,
  collection(name) {
    if (!Array.isArray(db[name])) db[name] = [];
    return db[name];
  },
  nextId(kind) {
    db._seq[kind] = (db._seq[kind] || 0) + 1;
    return db._seq[kind];
  },
  save() {
    fs.mkdirSync(path.dirname(FILE), { recursive: true });
    const tmp = `${FILE}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(db));
    fs.renameSync(tmp, FILE);
  },
};

let seeded = false;
if (fs.existsSync(SEEDS_DIR)) {
  for (const name of fs.readdirSync(SEEDS_DIR).filter((f) => f.endsWith(".js")).sort()) {
    if (db._seeded.includes(name)) continue;
    require(path.join(SEEDS_DIR, name))(store);
    db._seeded.push(name);
    seeded = true;
  }
}
if (seeded) store.save();

module.exports = store;
