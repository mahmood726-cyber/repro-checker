// R path (docs/rpath.js): the generated script carries the page's own numbers at full
// precision, and an un-pooled submission yields NOT CHECKED rather than a script.
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const docs = path.join(__dirname, "..", "docs");
const ctx = { console }; ctx.window = ctx; ctx.globalThis = ctx; vm.createContext(ctx);
for (const f of ["examples.js", "engine.js", "rpath.js"]) vm.runInContext(fs.readFileSync(path.join(docs, f), "utf8"), ctx);
let fail = 0;
function ok(c, m) { console.log((c ? "PASS  " : "FAIL  ") + m); if (!c) fail++; }
for (const k of Object.keys(ctx.RC_EXAMPLES)) {
  const sub = ctx.RC_EXAMPLES[k], rep = ctx.RC.check(sub, {});
  const b = ctx.RCR.buildScript(sub, rep);
  if (!rep.recomputed) { ok(!b.ok && /did not re-pool/.test(b.reason), k + ": NOT CHECKED"); continue; }
  ok(b.ok, k + ": script built");
  ok(b.script.includes("est = " + String(rep.recomputed.est) + ","), k + ": page est embedded exactly");
  ok(/MATCH %d\/%d/.test(b.script) && /MISMATCH/.test(b.script), k + ": script prints MATCH/MISMATCH");
}
const md = { claimed: { measure: "MD", est: -1 }, trials: [{ name: "x", effect: 1.1, elci: 0.9, euci: 1.3 }] };
const bm = ctx.RCR.buildScript(md, ctx.RC.check(md, {}));
ok(!bm.ok && /not supported/.test(bm.reason), "MD: NOT CHECKED with the engine's reason");
console.log(fail ? fail + " FAILED" : "all rpath checks pass");
process.exit(fail ? 1 : 0);
