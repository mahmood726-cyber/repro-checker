/* Node parity check: run every fixture through docs/engine.js and assert the
 * recomputed numbers and overall verdicts match the Python engine.
 * Run:  node tests/verify_js_engine.cjs
 */
const fs = require("fs");
const path = require("path");
const RC = require("../docs/engine.js");

const FIX = path.join(__dirname, "..", "fixtures");
function load(n) { return JSON.parse(fs.readFileSync(path.join(FIX, n), "utf8")); }

// expected recomputed pooled estimate (from the Python engine) + overall prefix
const CASES = [
  ["paper105_jak_ra.json",   3.40,  "REPRODUCES"],
  ["paper106_asthma.json",   0.523, "REPRODUCES"],
  ["paper105_corrupted.json", 2.17, "DIVERGES"],
  ["paper106_corrupted.json", 0.355, "DIVERGES"],
  ["glp1_elixa.json",         0.862, "DIVERGES"],
  ["paper30_structural.json", 0.553, "DIVERGES"], // offline (no live sourcing): pooled 0.55 vs claimed 0.70 diverges; the high-severity citation flags (fake NCT, miscited review) require live re-sourcing (CLI / opt-in browser fetch)
];

let fails = 0;
for (const [fname, wantEst, wantOverall] of CASES) {
  const sub = load(fname);
  const rep = RC.check(sub, {});           // offline: no sourcing -> recompute+structural only
  const est = rep.recomputed ? rep.recomputed.est : null;
  const estOk = est != null && Math.abs(est - wantEst) / wantEst < 0.01;  // 1% relative
  const ovOk = rep.overall.startsWith(wantOverall);
  const ok = estOk && ovOk;
  if (!ok) fails++;
  console.log(
    `${ok ? "PASS" : "FAIL"}  ${fname.padEnd(26)} est=${est == null ? "—" : est.toFixed(4)} ` +
    `(want ~${wantEst})  overall=${rep.overall.split(" ")[0]} (want ${wantOverall})`
  );
}

// extra: confirm 105 detailed parity (CI, I2, k)
const r105 = RC.check(load("paper105_jak_ra.json"), {});
const p = r105.recomputed;
console.log(`\n105 detail: OR=${p.est.toFixed(3)} CI=${p.lci.toFixed(3)}-${p.uci.toFixed(3)} ` +
            `I2=${p.I2.toFixed(1)} Q=${p.Q.toFixed(3)} k=${p.k}  (python: 3.397 / 2.889-3.994 / 0.0 / 0.74 / 4)`);

if (fails) { console.error(`\n${fails} parity check(s) FAILED`); process.exit(1); }
console.log("\nAll JS-engine parity checks passed.");
