/*
 * LID marketing site — enhancement script.
 *
 * Three behaviors, all small and opt-in:
 *   1. Page-load reveal of the drafting-style schematics — the hero
 *      schematic, the DAG, and the inset legend. These sit high enough in
 *      the page flow that firing on load is fine; the cost of an
 *      IntersectionObserver would exceed the benefit.
 *   2. Scroll-triggered reveal of the trace strip — each of the five
 *      panels fades in with a staggered delay when the strip enters the
 *      viewport. Uses IntersectionObserver because the strip sits below
 *      the fold at most widths; firing on load would mean the cascade
 *      animation plays before the reader ever sees it.
 *   3. Copy-to-clipboard buttons on command blocks — quickstart steps and
 *      the .cmd blocks on the Start page. Hidden until hover / focus.
 *
 * No third-party libraries. Loaded with `defer` so it never blocks first
 * paint.
 *
 * Respects prefers-reduced-motion via the global reduce rule in main.css
 * which collapses transition durations to ~0 and shows the final state
 * immediately — no per-behavior branching needed here.
 */

(() => {
  "use strict";

  // ── 1. Schematic reveal (page-load) ────────────────────────────────────
  document
    .querySelectorAll(".hero-schematic, .dag-schematic, .arrow-inset-schematic")
    .forEach((el) => el.classList.add("in-view"));

  // ── 2. Trace strip reveal (scroll-triggered) ───────────────────────────
  // The five trace panels carry `--d: 0.10s` through `--d: 0.50s` delays
  // on their CSS transitions; the `.in-view` class on the strip lets them
  // fire. Using IntersectionObserver with a generous rootMargin means the
  // cascade plays a beat before the strip is fully on-screen, so the
  // animation lands under the reader's eye rather than in peripheral
  // vision. Re-triggers on re-entry so scrolling back up feels alive.
  const traceStrips = document.querySelectorAll(".trace-strip");
  if (traceStrips.length && "IntersectionObserver" in window) {
    const traceObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          entry.target.classList.toggle("in-view", entry.isIntersecting);
        });
      },
      { rootMargin: "0px 0px -15% 0px", threshold: 0.12 },
    );
    traceStrips.forEach((el) => traceObserver.observe(el));
  } else {
    // No IntersectionObserver (very old browsers) — fall back to always-visible
    traceStrips.forEach((el) => el.classList.add("in-view"));
  }

  // ── 3. Copy-to-clipboard ───────────────────────────────────────────────
  const COPY_SVG = `
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="square" aria-hidden="true">
      <rect x="7" y="4" width="10" height="13" rx="1"/>
      <path d="M13 4V3a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h2"/>
    </svg>`;
  const CHECK_SVG = `
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <polyline points="4 10 8 14 16 6"/>
    </svg>`;

  const canCopy =
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function";

  if (!canCopy) return;

  const targets = document.querySelectorAll(".qs-cmd, .audience-body .cmd");

  targets.forEach((el) => {
    // Wrap element in a positioning container so the button can anchor.
    const wrap = document.createElement("div");
    wrap.className = "copy-wrap";
    el.parentNode.insertBefore(wrap, el);
    wrap.appendChild(el);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.setAttribute("aria-label", "Copy to clipboard");
    btn.innerHTML = COPY_SVG;
    wrap.appendChild(btn);

    let resetT = 0;
    btn.addEventListener("click", async () => {
      const text = el.textContent.trim();
      try {
        await navigator.clipboard.writeText(text);
        btn.classList.add("is-copied");
        btn.setAttribute("aria-label", "Copied");
        btn.innerHTML = CHECK_SVG;
        clearTimeout(resetT);
        resetT = setTimeout(() => {
          btn.classList.remove("is-copied");
          btn.setAttribute("aria-label", "Copy to clipboard");
          btn.innerHTML = COPY_SVG;
        }, 1600);
      } catch (err) {
        // Clipboard denied — give feedback once, don't swallow silently
        btn.setAttribute("aria-label", "Copy failed");
        console.error("Copy failed:", err);
      }
    });
  });
})();
