// Backend entry and router. Zero dependencies on purpose (plain `node`,
// CommonJS): the container's route to npmjs is slow. Do not grow this file.
//
//   backend/routes/<area>.js   one module per API area, loaded in name order:
//                              module.exports = (api) => {
//                                api.get("/api/items", (req, res) => api.json(res, 200, items));
//                                api.post("/api/items/:id/close", async (req, res) => {
//                                  const body = await api.body(req);   // JSON or form fields
//                                  ... req.params.id, req.query, api.cookies(req) ...
//                                });
//                                api.page("/items/:id", "item.html"); // dynamic URL -> page
//                              };
//   backend/store.js           JSON persistence + run-once seed modules (backend/seeds/)
//   backend/lib/*.js           shared helpers (sessions, validation, hashing)
//
// Literal paths win over parameterised ones whatever the module order.
// Anything no route claims is served from ../frontend/dist: "/" is
// index.html and "/<name>" is <name>.html.
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");

const DIST_DIR = path.resolve(__dirname, "..", "frontend", "dist");
const ROUTES_DIR = path.join(__dirname, "routes");
const PORT = Number(process.env.PORT || 3000);

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".csv": "text/csv; charset=utf-8",
};

const routes = [];
const pages = [];

function compile(pattern) {
  const keys = [];
  const source = pattern.replace(/\/+$/, "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/:(\w+)/g, (_, key) => { keys.push(key); return "([^/]+)"; });
  return { re: new RegExp(`^${source}/?$`), keys };
}

function match(entry, pathname) {
  const m = entry.re.exec(pathname);
  if (!m) return null;
  return Object.fromEntries(entry.keys.map((key, i) => [key, decodeURIComponent(m[i + 1])]));
}

const api = {
  json(res, status, value, headers = {}) {
    const body = JSON.stringify(value);
    res.writeHead(status, { "Content-Type": "application/json; charset=utf-8",
      "Content-Length": Buffer.byteLength(body), ...headers });
    res.end(body);
  },
  text(res, status, body, headers = {}) {
    res.writeHead(status, { "Content-Type": "text/plain; charset=utf-8",
      "Content-Length": Buffer.byteLength(body), ...headers });
    res.end(body);
  },
  redirect(res, location, status = 303, headers = {}) {
    res.writeHead(status, { Location: location, ...headers });
    res.end();
  },
  body(req) {
    return new Promise((resolve, reject) => {
      const chunks = [];
      req.on("data", (c) => chunks.push(c));
      req.on("error", reject);
      req.on("end", () => {
        const raw = Buffer.concat(chunks).toString("utf8");
        const type = String(req.headers["content-type"] || "");
        if (!raw) return resolve({});
        if (type.includes("application/x-www-form-urlencoded")) {
          return resolve(Object.fromEntries(new URLSearchParams(raw)));
        }
        try { resolve(JSON.parse(raw)); } catch { resolve({ _raw: raw }); }
      });
    });
  },
  cookies(req) {
    return Object.fromEntries(String(req.headers.cookie || "").split(";").map((part) => {
      const i = part.indexOf("=");
      return i < 0 ? [part.trim(), ""] : [part.slice(0, i).trim(), decodeURIComponent(part.slice(i + 1).trim())];
    }).filter(([k]) => k));
  },
  page(pattern, file) {
    pages.push({ ...compile(pattern), file });
  },
};
for (const method of ["get", "post", "put", "patch", "delete"]) {
  api[method] = (pattern, handler) => routes.push({ method: method.toUpperCase(), ...compile(pattern), handler });
}

function serveFile(req, res, rels, i = 0) {
  if (i >= rels.length) return api.text(res, 404, "not found\n");
  const file = path.normalize(path.join(DIST_DIR, rels[i]));
  if (file !== DIST_DIR && !file.startsWith(DIST_DIR + path.sep)) return api.text(res, 404, "not found\n");
  fs.readFile(file, (err, data) => {
    if (err) return serveFile(req, res, rels, i + 1);
    const type = MIME_TYPES[path.extname(file).toLowerCase()] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": type, "Content-Length": data.length });
    res.end(req.method === "HEAD" ? undefined : data);
  });
}

if (fs.existsSync(ROUTES_DIR)) {
  for (const name of fs.readdirSync(ROUTES_DIR).filter((f) => f.endsWith(".js")).sort()) {
    require(path.join(ROUTES_DIR, name))(api);
  }
}
// Literal segments before parameters, registration order otherwise.
routes.sort((a, b) => a.keys.length - b.keys.length);
pages.sort((a, b) => a.keys.length - b.keys.length);

const server = http.createServer(async (req, res) => {
  let url;
  let pathname;
  try {
    url = new URL(req.url, "http://localhost");
    pathname = decodeURIComponent(url.pathname);
  } catch {
    return api.text(res, 400, "bad request\n");
  }
  req.query = Object.fromEntries(url.searchParams);
  const method = req.method === "HEAD" ? "GET" : req.method;
  for (const route of routes) {
    if (route.method !== method) continue;
    const params = match(route, pathname);
    if (!params) continue;
    req.params = params;
    try {
      await route.handler(req, res);
    } catch (err) {
      console.error(err);
      if (!res.headersSent) api.json(res, 500, { error: "internal error" });
    }
    return;
  }
  if (method !== "GET") return api.text(res, 404, "not found\n");
  for (const page of pages) {
    if (match(page, pathname)) return serveFile(req, res, [page.file]);
  }
  const rel = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  serveFile(req, res, path.extname(rel) ? [rel] : [rel + ".html", rel]);
});

server.listen(PORT, () => {
  console.log(`backend listening on port ${PORT}, serving ${DIST_DIR}`);
});
