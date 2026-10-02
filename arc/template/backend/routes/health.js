// Example route module: one module per API area (see the top of server.js).
"use strict";

module.exports = (api) => {
  api.get("/api/health", (req, res) => api.json(res, 200, { ok: true }));
};
