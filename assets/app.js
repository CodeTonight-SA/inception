/* INCEPTION — witness stack homepage interactions.
   Vanilla JS, no frameworks. Every dynamic value is inserted via
   textContent or createElement — never innerHTML with data (XSS-safe). */

(function () {
  "use strict";

  var RECORDED_KIT_ROOT =
    "sha256:b5121f7899d48a739dcf33484390ef5e0d489ac4753ae1cbf5d8fcf925baea1c";
  var MOAT_SLUG = "the-grip-sovereign-moat-grip-convergent-";

  /* ---- KIT STAMP ---- */
  var stampEl = document.getElementById("kit-stamp");
  var recheckBtn = document.getElementById("recheck");
  var footerRootEl = document.getElementById("footer-root");

  function renderStamp(parts) {
    stampEl.textContent = "";
    for (var i = 0; i < parts.length; i++) {
      var span = document.createElement("span");
      span.textContent = parts[i].text;
      if (parts[i].cls) span.className = parts[i].cls;
      stampEl.appendChild(span);
    }
  }

  function renderFooterRoot(root) {
    footerRootEl.textContent = "";
    var key = document.createElement("span");
    key.className = "k";
    key.textContent = "KIT ROOT  ";
    footerRootEl.appendChild(key);
    footerRootEl.appendChild(document.createTextNode(root));
  }

  function loadVerify() {
    if (recheckBtn) {
      recheckBtn.disabled = true;
      recheckBtn.textContent = "CHECKING…";
      recheckBtn.setAttribute("aria-busy", "true");
    }
    fetch("/api/verify")
      .then(function (res) {
        if (!res.ok) throw new Error("verify non-200");
        return res.json();
      })
      .then(function (data) {
        var isVerified = data && (data.stamp === "VERIFIED" || data.ok === true);
        if (isVerified) {
          var root = String(data.kit_root || RECORDED_KIT_ROOT);
          var hex = root.indexOf("sha256:") === 0 ? root.slice(7) : root;
          var prefix = hex.slice(0, 12);
          renderStamp([
            { text: "KIT: " },
            { text: "VERIFIED", cls: "stamp-state" },
            { text: " · " + data.files_checked + " FILES · ROOT " + prefix }
          ]);
          renderFooterRoot(root);
        } else {
          var broken =
            data && typeof data.files_broken === "number"
              ? data.files_broken
              : "?";
          renderStamp([
            { text: "KIT: " },
            { text: "BROKEN", cls: "stamp-state" },
            { text: " · " + broken + " FILE(S) ALTERED" }
          ]);
        }
      })
      .catch(function () {
        renderStamp([
          { text: "KIT: UNREACHABLE — START THE DAEMON: python3 server.py" }
        ]);
      })
      .then(function () {
        if (recheckBtn) {
          recheckBtn.disabled = false;
          recheckBtn.textContent = "RECHECK";
          recheckBtn.removeAttribute("aria-busy");
        }
      });
  }

  /* ---- MOAT SEED (live from /api/list, recorded fallback stays) ---- */
  var moatSourceEl = document.getElementById("moat-source");
  var moatDeadlineEl = document.getElementById("moat-deadline");
  var moatArchetypeEl = document.getElementById("moat-archetype");
  var moatHypothesisEl = document.getElementById("moat-hypothesis");
  var moatSeedEl = document.getElementById("moat-seed");
  var moatRootEl = document.getElementById("moat-root");

  function loadList() {
    fetch("/api/list")
      .then(function (res) {
        if (!res.ok) throw new Error("list non-200");
        return res.json();
      })
      .then(function (data) {
        if (!Array.isArray(data)) return;
        var moat = null;
        for (var i = 0; i < data.length; i++) {
          if (data[i] && data[i].slug === MOAT_SLUG) {
            moat = data[i];
            break;
          }
        }
        if (!moat) return;
        if (moat.deadline != null) moatDeadlineEl.textContent = String(moat.deadline);
        if (moat.archetype != null) moatArchetypeEl.textContent = String(moat.archetype);
        if (moat.hypothesis != null) moatHypothesisEl.textContent = String(moat.hypothesis);
        if (moat.seed != null) moatSeedEl.textContent = String(moat.seed);
        if (moat.root != null) moatRootEl.textContent = String(moat.root);
        if (moatSourceEl) moatSourceEl.textContent = "live from the daemon";
      })
      .catch(function () {
        /* daemon down — recorded fallback values stay in the DOM */
      });
  }

  /* ---- PLANT A SEED ---- */
  var form = document.getElementById("plant-form");
  var domainEl = document.getElementById("domain");
  var deadlineEl = document.getElementById("deadline");
  var archetypeEl = document.getElementById("archetype");
  var plantBtn = document.getElementById("plant-btn");
  var resultEl = document.getElementById("plant-result");

  function resultLine(text, cls) {
    var p = document.createElement("p");
    p.className = "result-line" + (cls ? " " + cls : "");
    p.textContent = text;
    return p;
  }

  function resultKV(key, value) {
    var p = document.createElement("p");
    p.className = "result-line";
    var k = document.createElement("span");
    k.className = "result-key";
    k.textContent = key + "  ";
    p.appendChild(k);
    p.appendChild(document.createTextNode(value == null ? "" : String(value)));
    return p;
  }

  function renderPlantCard(data) {
    resultEl.textContent = "";
    resultEl.appendChild(resultLine("$ incept.py " + (data.domain || ""), "result-dim"));

    var hypoLine = String(data.hypothesis_id || "");
    if (data.domain) hypoLine += " · " + data.domain;
    if (data.deadline) hypoLine += " · " + data.deadline;
    resultEl.appendChild(resultKV("HYPOTHESIS", hypoLine));

    if (data.hypothesis) {
      resultEl.appendChild(resultLine(data.hypothesis, "result-dim"));
    }
    if (data.falsifier != null) {
      resultEl.appendChild(resultKV("FALSIFIER", data.falsifier));
    }

    resultEl.appendChild(resultKV("CHAIN", "seed ⊂ genesis.md ⊂ tool"));
    resultEl.appendChild(resultLine("  seed        " + (data.seed || ""), "result-dim"));
    resultEl.appendChild(resultLine("  genesis.md  " + (data.genesis_file || ""), "result-dim"));
    resultEl.appendChild(resultLine("  tool        " + (data.tool || ""), "result-dim"));

    if (data.root != null) {
      resultEl.appendChild(resultKV("ROOT", data.root));
    }
    resultEl.appendChild(resultLine("don't trust it — witness it", "result-dim"));
  }

  function renderError(message) {
    resultEl.textContent = "";
    resultEl.appendChild(resultLine(message, "result-error"));
  }

  function onSubmit(e) {
    e.preventDefault();

    var body = { domain: domainEl.value.trim() };
    var deadline = deadlineEl.value.trim();
    var archetype = archetypeEl.value;
    if (deadline) body.deadline = deadline;
    if (archetype && archetype !== "auto") body.archetype = archetype;

    plantBtn.disabled = true;
    plantBtn.textContent = "PLANTING…";

    fetch("/api/plant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(function (res) {
        return res.json().catch(function () {
          return null;
        }).then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (r) {
        if (r.ok && r.data) {
          renderPlantCard(r.data);
        } else if (r.data && r.data.error) {
          renderError(r.data.error);
        } else {
          renderError("The daemon rejected the request.");
        }
      })
      .catch(function () {
        renderError("The daemon is not running. Start it: python3 server.py");
      })
      .then(function () {
        plantBtn.disabled = false;
        plantBtn.textContent = "PLANT";
      });
  }

  if (form) form.addEventListener("submit", onSubmit);
  if (recheckBtn) recheckBtn.addEventListener("click", loadVerify);

  loadVerify();
  loadList();
})();
