/*
 * LID marketing site — enhancement script.
 *
 * Two behaviors, both small and opt-in:
 *   1. Scroll-triggered reveal of the hero schematic (the arrow-of-intent
 *      drawing animates in when it enters the viewport; re-triggers when it
 *      re-enters so scrolling back up still feels alive).
 *   2. Copy-to-clipboard buttons on command blocks — quickstart steps and
 *      the .cmd blocks on the Start page. Hidden until hover / focus.
 *
 * No third-party libraries. ~80 lines. Loaded with `defer` so it never
 * blocks first paint.
 *
 * Respects prefers-reduced-motion by jumping the schematic straight to its
 * final state instead of animating.
 */

(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ── 1. Schematic reveal ────────────────────────────────────────────────
  // Fire once on page load. The CSS transitions + per-node `--d` delays
  // produce the staggered draw-in. `prefers-reduced-motion` is honored
  // via the global reduce rule at the bottom of main.css, which collapses
  // transition durations to ~0 and shows the final state immediately.
  const schematic = document.querySelector(".hero-schematic");
  if (schematic) schematic.classList.add("in-view");

  // ── 2. Copy-to-clipboard ───────────────────────────────────────────────
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
