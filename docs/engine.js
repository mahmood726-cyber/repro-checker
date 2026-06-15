/* reprocheck — browser/Node engine (pure, no DOM).
 *
 * Faithful JS port of reprocheck/recompute.py + compare.py + flags.py. Pooling
 * is inverse-variance random-effects (DerSimonian-Laird + REML) on the log
 * scale; 0.5 continuity correction only when a cell is zero; prediction interval
 * uses t_{k-1}. Verified against the Python engine under Node (see
 * tests/verify_js_engine.cjs): 105 -> OR 3.40, 106 -> RR 0.523, GLP-1 -> 0.86.
 *
 * Truth-first: a quantity is only "reproduces" if it recomputed and agreed;
 * missing data is "cannot-verify"; nothing is fabricated.
 */
(function (global) {
  "use strict";

  // ---- normal / t / chi-square helpers -----------------------------------
  function normPpf(p) {
    var a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    var b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01];
    var c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    var d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00];
    var plow = 0.02425, phigh = 1 - 0.02425, q, r;
    if (p < plow) {
      q = Math.sqrt(-2 * Math.log(p));
      return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
             ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
    }
    if (p > phigh) {
      q = Math.sqrt(-2 * Math.log(1 - p));
      return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
              ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
    }
    q = p - 0.5; r = q * q;
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
  }

  function tPpf(p, df) {
    if (df <= 0) return normPpf(p);
    var x = normPpf(p);
    var g1 = (Math.pow(x,3)+x)/4;
    var g2 = (5*Math.pow(x,5)+16*Math.pow(x,3)+3*x)/96;
    var g3 = (3*Math.pow(x,7)+19*Math.pow(x,5)+17*Math.pow(x,3)-15*x)/384;
    var g4 = (79*Math.pow(x,9)+776*Math.pow(x,7)+1482*Math.pow(x,5)-1920*Math.pow(x,3)-945*x)/92160;
    return x + g1/df + g2/(df*df) + g3/Math.pow(df,3) + g4/Math.pow(df,4);
  }

  var LG = [676.5203681218851, -1259.1392167224028, 771.32342877765313,
            -176.61502916214059, 12.507343278686905, -0.13857109526572012,
            9.9843695780195716e-6, 1.5056327351493116e-7];
  function lgamma(x) {
    if (x < 0.5) return Math.log(Math.PI / Math.sin(Math.PI*x)) - lgamma(1 - x);
    x -= 1; var a = 0.99999999999980993, t = x + 7.5;
    for (var i = 0; i < LG.length; i++) a += LG[i] / (x + i + 1);
    return 0.5*Math.log(2*Math.PI) + (x+0.5)*Math.log(t) - t + Math.log(a);
  }

  function gammaincc(a, x) {
    if (x < a + 1) {
      var ap = a, s = 1/a, term = 1/a;
      for (var i = 0; i < 500; i++) { ap += 1; term *= x/ap; s += term;
        if (Math.abs(term) < Math.abs(s)*1e-12) break; }
      return 1 - s*Math.exp(-x + a*Math.log(x) - lgamma(a));
    }
    var tiny = 1e-300, b = x+1-a, c = 1/tiny, d = 1/b, h = d;
    for (var j = 1; j < 500; j++) {
      var an = -j*(j-a); b += 2; d = an*d + b; if (Math.abs(d) < tiny) d = tiny;
      c = b + an/c; if (Math.abs(c) < tiny) c = tiny; d = 1/d;
      var delta = d*c; h *= delta; if (Math.abs(delta-1) < 1e-12) break;
    }
    return h*Math.exp(-x + a*Math.log(x) - lgamma(a));
  }
  function chisqSf(x, k) { return x <= 0 ? 1 : gammaincc(k/2, x/2); }

  // ---- per-study effect ---------------------------------------------------
  function studyLogEffect(s, measure) {
    if (s.shape === "effect") {
      var eff = s.effect, lci = s.elci, uci = s.euci;
      var logEff = Math.log(eff);
      var z = normPpf(0.975);
      var se = (Math.log(uci) - Math.log(lci)) / (2*z);
      return { logEff: logEff, varr: se*se, est: eff, lci: lci, uci: uci };
    }
    var a = s.tE, b = s.tN - s.tE, c = s.cE, d = s.cN - s.cE;
    if (Math.min(a, b, c, d) === 0) { a += 0.5; b += 0.5; c += 0.5; d += 0.5; }
    var le, v;
    if (measure === "RR") {
      var r1 = a/(a+b), r2 = c/(c+d);
      le = Math.log(r1/r2); v = 1/a - 1/(a+b) + 1/c - 1/(c+d);
    } else { // OR
      le = Math.log((a*d)/(b*c)); v = 1/a + 1/b + 1/c + 1/d;
    }
    var se2 = Math.sqrt(v), zz = normPpf(0.975);
    return { logEff: le, varr: v, est: Math.exp(le),
             lci: Math.exp(le - zz*se2), uci: Math.exp(le + zz*se2) };
  }

  function remlTau2(logs, vars_, init) {
    var tau2 = Math.max(0, init || 0);
    for (var it = 0; it < 200; it++) {
      var w = vars_.map(function (v) { return 1/(v+tau2); });
      var sw = w.reduce(function (x, y) { return x+y; }, 0);
      var mu = 0; for (var i=0;i<w.length;i++) mu += w[i]*logs[i]; mu /= sw;
      var sw2 = w.reduce(function (x, y) { return x+y*y; }, 0);
      var num = 0;
      for (var j=0;j<w.length;j++) num += w[j]*w[j]*((logs[j]-mu)*(logs[j]-mu)-vars_[j]);
      var next = Math.max(0, num/sw2 + 1/sw);
      if (Math.abs(next - tau2) < 1e-10) { tau2 = next; break; }
      tau2 = next;
    }
    return tau2;
  }

  function metaAnalyze(studies, measure) {
    var logs = [], vars_ = [], per = [];
    studies.forEach(function (s) {
      var e = studyLogEffect(s, measure);
      logs.push(e.logEff); vars_.push(e.varr);
      per.push({ name: s.name, est: e.est, lci: e.lci, uci: e.uci,
                 se: Math.sqrt(e.varr) });
    });
    var k = studies.length;
    var wf = vars_.map(function (v) { return 1/v; });
    var sw = wf.reduce(function (x, y) { return x+y; }, 0);
    var muF = 0; for (var i=0;i<wf.length;i++) muF += wf[i]*logs[i]; muF /= sw;
    var Q = 0; for (var j=0;j<wf.length;j++) Q += wf[j]*(logs[j]-muF)*(logs[j]-muF);
    var Qdf = k - 1;
    var cdl = sw - wf.reduce(function (x, y) { return x+y*y; }, 0)/sw;
    var tau2dl = cdl > 0 ? Math.max(0, (Q-Qdf)/cdl) : 0;
    var tau2 = remlTau2(logs, vars_, tau2dl);
    var wre = vars_.map(function (v) { return 1/(v+tau2); });
    var swre = wre.reduce(function (x, y) { return x+y; }, 0);
    var mu = 0; for (var m=0;m<wre.length;m++) mu += wre[m]*logs[m]; mu /= swre;
    var se = Math.sqrt(1/swre);
    var z = normPpf(0.975);
    var I2 = Q > 0 ? Math.max(0, (Q-Qdf)/Q)*100 : 0;
    var piL = NaN, piU = NaN;
    if (k >= 2) {
      var tt = tPpf(0.975, k-1);
      var half = tt*Math.sqrt(tau2 + se*se);
      piL = Math.exp(mu - half); piU = Math.exp(mu + half);
    }
    per.forEach(function (st, idx) { st.weight_pct = 100*wre[idx]/swre; });
    return {
      perStudy: per,
      pooled: { measure: measure, est: Math.exp(mu), lci: Math.exp(mu - z*se),
        uci: Math.exp(mu + z*se), log_est: mu, se: se, Q: Q, Qdf: Qdf,
        Qp: chisqSf(Q, Qdf), I2: I2, tau2: tau2, tau2_dl: tau2dl,
        pi_lci: piL, pi_uci: piU, k: k, estimator: "REML" }
    };
  }

  // ---- compare ------------------------------------------------------------
  var RATIO = { OR:1, RR:1, HR:1, IRR:1, RATERATIO:1 };
  function ratioClose(a, b, rel) {
    if (a == null || b == null || a <= 0 || b <= 0) return false;
    return Math.abs(Math.log(a) - Math.log(b)) <= Math.log(1+rel);
  }
  function absClose(a, b, tol) { return a != null && b != null && Math.abs(a-b) <= tol; }

  function verdict(claimed, recomputed, ok, tol, quantity, reason) {
    if (claimed == null)
      return { quantity: quantity, claimed: null, recomputed: recomputed,
               verdict: "cannot-verify", tolerance: tol,
               reason: "paper did not state this quantity" };
    if (recomputed == null)
      return { quantity: quantity, claimed: claimed, recomputed: null,
               verdict: "cannot-verify", tolerance: tol,
               reason: reason || "no sourceable data to recompute" };
    return { quantity: quantity, claimed: claimed, recomputed: recomputed,
             verdict: ok ? "reproduces" : "diverges", tolerance: tol, reason: "" };
  }

  function compare(claimed, pooled, opts) {
    opts = opts || {};
    var t = { rel_est: 0.05, rel_ci: 0.08, abs_est: 0.05, abs_ci: 0.10,
              i2_pts: 5.0, q_abs: 1.0, pi_rel: 0.15 };
    var measure = (claimed.measure || (pooled ? pooled.measure : "") || "").toUpperCase();
    var isRatio = !!RATIO[measure];
    var out = [];
    function cmpEffect(name, cv, rv, rel, ab) {
      var ok, td;
      if (isRatio) { ok = ratioClose(cv, rv, rel); td = "±"+(rel*100)+"% relative (log)"; }
      else { ok = absClose(cv, rv, ab); td = "±"+ab+" absolute"; }
      return verdict(cv, rv, ok, td, name, opts.recompute_reason);
    }
    var p = pooled;
    out.push(cmpEffect("pooled "+(measure||"effect"), claimed.est, p?p.est:null, t.rel_est, t.abs_est));
    out.push(cmpEffect("95% CI lower", claimed.lci, p?p.lci:null, t.rel_ci, t.abs_ci));
    out.push(cmpEffect("95% CI upper", claimed.uci, p?p.uci:null, t.rel_ci, t.abs_ci));
    out.push(verdict(claimed.I2, p?round(p.I2,1):null, absClose(claimed.I2, p?p.I2:null, t.i2_pts),
                     "±"+t.i2_pts+" pts", "I^2 (%)", opts.recompute_reason));
    if (claimed.Q != null)
      out.push(verdict(claimed.Q, p?round(p.Q,3):null, absClose(claimed.Q, p?p.Q:null, t.q_abs),
                       "±"+t.q_abs, "Cochran's Q", opts.recompute_reason));
    if (claimed.k != null)
      out.push(verdict(claimed.k, p?p.k:null, p!=null && claimed.k===p.k, "exact",
                       "k (studies pooled)", "no poolable trials re-sourced"));
    if (claimed.pi_lci != null && p && !isNaN(p.pi_lci)) {
      out.push(verdict(claimed.pi_lci, round(p.pi_lci,3),
                       isRatio?ratioClose(claimed.pi_lci,p.pi_lci,t.pi_rel):absClose(claimed.pi_lci,p.pi_lci,t.abs_ci*2),
                       "±"+(t.pi_rel*100)+"%", "prediction interval lower"));
      out.push(verdict(claimed.pi_uci, round(p.pi_uci,3),
                       isRatio?ratioClose(claimed.pi_uci,p.pi_uci,t.pi_rel):absClose(claimed.pi_uci,p.pi_uci,t.abs_ci*2),
                       "±"+(t.pi_rel*100)+"%", "prediction interval upper"));
    }
    return out;
  }
  function round(x, n) { var f = Math.pow(10, n); return Math.round(x*f)/f; }

  // ---- flags --------------------------------------------------------------
  var PLACEHOLDERS = [
    [/\bn participants\b/, "literal 'n participants' (unfilled count token)"],
    [/\bN participants\b/, "literal 'N participants' (unfilled count token)"],
    [/\{\{[^}]+\}\}/, "mustache placeholder {{...}}"],
    [/\bREPLACE_ME\b/, "REPLACE_ME placeholder"],
    [/__PLACEHOLDER__/, "__PLACEHOLDER__ token"],
    [/\bTODO\b/, "TODO marker in body"],
    [/\bLorem ipsum\b/, "Lorem ipsum filler"],
    [/\bAuthor(?:s)? et al\.?(?=\s|$)/, "unfilled 'Author et al' citation"],
    [/\bNone trials\b/, "Python None leaked into text"],
    [/\bNone participants\b/, "Python None leaked into text"],
    [/\/None\b/, "URL ending in /None (None leak)"]
  ];

  function flagsFor(sub, sourcing) {
    var F = [];
    var blob = (sub.raw_text||"") + "\n" + (sub.title||"") + "\n" +
               (sub.trials||[]).map(function (t) { return t.name||""; }).join("\n");
    PLACEHOLDERS.forEach(function (pr) {
      var m = pr[0].exec(blob);
      if (m) F.push({ id:"placeholder-artifact", severity:"low",
        title:"Template/placeholder artifact", detail: pr[1],
        subject: "..."+blob.slice(Math.max(0,m.index-25), m.index+25).replace(/\n/g," ").trim()+"..." });
    });
    (sub.trials||[]).forEach(function (t) {
      var sh = shapeOf(t);
      if (sh === "count") {
        [["treatment",t.tE,t.tN],["control",t.cE,t.cN]].forEach(function (arm) {
          var e=arm[1], n=arm[2];
          if (e==null||n==null) return;
          if (e<0||n<0) F.push({id:"impossible-count",severity:"high",title:"Negative count",detail:arm[0]+": events="+e+", n="+n,subject:t.name});
          else if (e>n) F.push({id:"impossible-count",severity:"high",title:"Events exceed arm size",detail:arm[0]+": events="+e+" > n="+n+" (extraction/unit error)",subject:t.name});
        });
      } else if (sh === "effect") {
        if (t.effect != null && t.effect <= 0) F.push({id:"impossible-effect",severity:"high",title:"Non-positive ratio effect",detail:"effect="+t.effect,subject:t.name});
        if (t.elci!=null && t.euci!=null && t.elci>t.euci) F.push({id:"ci-order",severity:"medium",title:"CI bounds reversed",detail:"lci="+t.elci+" > uci="+t.euci,subject:t.name});
        if (t.effect!=null&&t.elci!=null&&t.euci!=null&&!(t.elci<=t.effect&&t.effect<=t.euci))
          F.push({id:"effect-outside-ci",severity:"medium",title:"Point estimate lies outside its own 95% CI",detail:"effect="+t.effect+", CI "+t.elci+"-"+t.euci+" (arithmetic/transcription error)",subject:t.name});
      } else {
        F.push({id:"no-usable-data",severity:"info",title:"Trial has no usable per-arm or effect data",detail:"cannot recompute this study's contribution",subject:t.name});
      }
    });
    var usable = (sub.trials||[]).filter(function (t) { return shapeOf(t)!=null; });
    if (sub.claimed && sub.claimed.k!=null && (sub.trials||[]).length) {
      if (sub.claimed.k !== sub.trials.length)
        F.push({id:"k-mismatch",severity:"medium",title:"Study-count (k) mismatch",detail:"paper claims k="+sub.claimed.k+" trials but the study table lists "+sub.trials.length,subject:""});
      if (usable.length < sub.trials.length)
        F.push({id:"k-poolable-mismatch",severity:"medium",title:"Fewer poolable trials than listed",detail:sub.trials.length+" trials listed, only "+usable.length+" carry usable data",subject:""});
    }
    (sourcing||[]).forEach(function (s) {
      if (s.verdict==="not-real") F.push({id:"citation-not-real",severity:"high",title:"Cited trial does not exist",detail:(s.notes||[]).join("; ")||"identifier did not resolve",subject:s.name});
      else if (s.verdict==="not-a-trial") F.push({id:"citation-not-a-trial",severity:"high",title:"Citation is not a primary trial",detail:(s.notes||[]).join("; ")||"publication type is a review/methods paper",subject:s.name});
      else if (s.verdict==="cannot-verify") F.push({id:"citation-unverified",severity:"info",title:"Citation could not be independently re-sourced",detail:(s.notes||[]).join("; ")||"no resolvable identifier / network",subject:s.name});
    });
    return F;
  }

  function shapeOf(t) {
    if (t.tE!=null && t.tN!=null && t.cE!=null && t.cN!=null) return "count";
    if (t.effect!=null && t.elci!=null && t.euci!=null) return "effect";
    return null;
  }
  function toStudy(t) {
    var sh = shapeOf(t);
    if (sh==="count") return {name:t.name,shape:"count",tE:t.tE,tN:t.tN,cE:t.cE,cN:t.cN};
    if (sh==="effect") return {name:t.name,shape:"effect",effect:t.effect,elci:t.elci,euci:t.euci};
    return null;
  }

  // ---- overall + check ----------------------------------------------------
  function overall(claims, flags, pooled, reason) {
    var high = flags.filter(function (f) { return f.severity==="high"; });
    var est = claims.find(function (c) { return c.quantity.indexOf("pooled")===0; });
    var diverged = claims.filter(function (c) { return c.verdict==="diverges"; });
    if (high.length) return ["FAIL — integrity issue", high.length+" high-severity flag(s) (e.g. "+high[0].title+": "+high[0].detail+")."];
    if (est && est.verdict==="diverges") return ["DIVERGES — does not reproduce", "The pooled estimate recomputes to "+fmt(est.recomputed)+" but the paper claims "+fmt(est.claimed)+". "+diverged.length+" quantity(ies) diverge."];
    if (est && est.verdict==="cannot-verify") return ["INCONCLUSIVE — cannot verify", "The pooled estimate could not be independently recomputed ("+(reason||est.reason)+"). Honest non-result; not a pass."];
    if (diverged.length) return ["PARTIAL — pooled reproduces, secondary divergence", "The pooled estimate reproduces, but "+diverged.length+" secondary quantity(ies) diverge."];
    if (!pooled) return ["INCONCLUSIVE — cannot verify", "Insufficient sourceable data."];
    return ["REPRODUCES", "Every claimed quantity that could be recomputed agreed within tolerance."];
  }
  function fmt(v) { return v==null?"—":(typeof v==="number"?(Math.round(v*10000)/10000):v); }

  function check(sub, opts) {
    opts = opts || {};
    var claimed = sub.claimed || {};
    var measure = (claimed.measure||"OR").toUpperCase();
    var studies = (sub.trials||[]).map(toStudy).filter(Boolean);
    var pooled = null, reason = "";
    if (studies.length >= 1) {
      try { pooled = metaAnalyze(studies, (measure==="RR"?"RR":"OR")).pooled; }
      catch (e) { reason = "recompute failed: "+e; }
    } else { reason = "no poolable trial data supplied"; }
    var claims = compare(claimed, pooled, { recompute_reason: reason });
    var flags = flagsFor(sub, opts.sourcing);
    var ov = overall(claims, flags, pooled, reason);
    return { title: sub.title||"", source: sub.source||"", overall: ov[0],
             overall_detail: ov[1], measure: measure, recomputed: pooled,
             claims: claims, flags: flags, sourcing: opts.sourcing||[],
             generated: opts.generated||"" };
  }

  var RC = { metaAnalyze: metaAnalyze, compare: compare, flagsFor: flagsFor,
             check: check, normPpf: normPpf, tPpf: tPpf, chisqSf: chisqSf };
  global.RC = RC;
  if (typeof module !== "undefined" && module.exports) module.exports = RC;
})(typeof window !== "undefined" ? window : globalThis);
