/* P55 regression checks for the page engine (docs/engine.js). Each failed on b8aee89.
 * Run: node tests/p55_js_regressions.cjs   (exit 1 on any failure) */
const RC = require("../docs/engine.js");
let fails = 0;
function ok(cond, msg) { console.log((cond ? "PASS  " : "FAIL  ") + msg); if (!cond) fails++; }
const est = rep => rep.claims.find(c => c.quantity.indexOf("pooled") === 0);

// D1: single study -> no heterogeneity, Qp undefined (was I2 = 100% from a 1-ulp Q residue)
for (const [m, s] of [["OR", [23, 257, 17, 237]], ["OR", [7, 73, 28, 197]], ["OR", [21, 146, 30, 256]], ["RR", [64, 256, 101, 392]]]) {
  const p = RC.metaAnalyze([{ name: "s", shape: "count", tE: s[0], tN: s[1], cE: s[2], cN: s[3] }], m).pooled;
  ok(p.Q === 0 && p.I2 === 0 && isNaN(p.Qp), `k=1 ${m} ${s}: Q=${p.Q} I2=${p.I2} Qp=${p.Qp}`);
}
// D2: exact 97.5% normal quantile
ok(RC.normPpf(0.975) === 1.959963984540054, "normPpf(0.975) = qnorm(0.975)");
// D3/D4: claimed PI with k=1 and claimed tau2 stay visible
let r = RC.check({ claimed: { measure: "OR", est: 2, pi_lci: 0.2, pi_uci: 2 }, trials: [{ name: "a", tE: 15, tN: 100, cE: 25, cN: 100 }] });
ok(r.claims.filter(c => c.quantity.indexOf("prediction interval") === 0 && c.verdict === "cannot-verify").length === 2, "k=1 claimed PI -> 2 cannot-verify");
r = RC.check({ claimed: { measure: "OR", est: 0.6, tau2: 0.05 }, trials: [{ name: "a", tE: 15, tN: 100, cE: 25, cN: 100 }, { name: "b", tE: 30, tN: 120, cE: 32, cN: 118 }] });
ok(r.claims.some(c => /tau/i.test(c.quantity)), "claimed tau2 listed");
// D6/D7: unsupported measures
r = RC.check({ claimed: { measure: "MD", est: 1.5 }, trials: [{ name: "m1", effect: 1.2, elci: 0.4, euci: 2.0 }, { name: "m2", effect: 1.8, elci: 0.9, euci: 2.7 }] });
ok(est(r).verdict === "cannot-verify" && !r.overall.startsWith("FAIL"), "MD -> cannot-verify (" + r.overall + ")");
r = RC.check({ claimed: { measure: "SMD", est: -0.3 }, trials: [{ name: "s1", effect: -0.2, elci: -0.5, euci: 0.1 }, { name: "s2", effect: -0.4, elci: -0.7, euci: -0.1 }] });
ok(est(r).verdict === "cannot-verify" && !r.overall.startsWith("FAIL"), "SMD -> cannot-verify (" + r.overall + ")");
r = RC.check({ claimed: { measure: "HR", est: 0.6 }, trials: [{ name: "a", tE: 15, tN: 100, cE: 25, cN: 100 }, { name: "b", tE: 30, tN: 120, cE: 32, cN: 118 }] });
ok(est(r).verdict === "cannot-verify", "HR from counts -> cannot-verify");
// D8: invalid log input -> cannot-verify (Python parity), not a NaN that 'diverges'
r = RC.check({ claimed: { measure: "OR", est: 0.6 }, trials: [{ name: "z1", effect: 0.5, elci: 0, euci: 1.2 }, { name: "z2", effect: 0.7, elci: 0.5, euci: 0.98 }] });
ok(est(r).verdict === "cannot-verify" && r.overall.startsWith("INCONCLUSIVE"), "CI bound 0 -> INCONCLUSIVE (" + r.overall + ")");
// D5: unsourced REPRODUCES discloses it
const tr = [{ name: "a", tE: 15, tN: 100, cE: 25, cN: 100 }, { name: "b", tE: 30, tN: 120, cE: 32, cN: 118 }];
const e0 = RC.check({ claimed: { measure: "OR", est: 1 }, trials: tr }).recomputed.est;
r = RC.check({ claimed: { measure: "OR", est: e0 }, trials: tr }, { sourcing: tr.map(t => ({ name: t.name, verdict: "cannot-verify", notes: [] })) });
ok(r.overall.startsWith("REPRODUCES") && /re-sourced/.test(r.overall_detail), "unsourced REPRODUCES discloses");
if (fails) { console.error(fails + " failure(s)"); process.exit(1); }
console.log("all P55 page-engine regressions pass");
