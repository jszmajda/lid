/*
 * LID marketing site: small enhancements. Nothing a page needs in order to be read.
 *   1. Copy buttons on command blocks (the Home Quickstart and the Start page's commands).
 *   2. A border under the navigation once the page has scrolled.
 * The rings drawing has its own module, assets/js/rings.js, loaded on the home page.
 */
(() => {
  "use strict";

  const copy = (button, text) => {
    const done = () => {
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = "Copy"; }, 1600);
    };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => {});
  };

  document.querySelectorAll("button.copy[data-cmd]").forEach((button) => {
    button.addEventListener("click", () => copy(button, button.dataset.cmd));
  });

  if (navigator.clipboard) {
    document.querySelectorAll("pre.cmd").forEach((block) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "copy";
      button.textContent = "Copy";
      button.addEventListener("click", () => {
        const text = block.querySelector("code").innerText.split("\n").filter((line) => !line.trim().startsWith("#")).join("\n").trim();
        copy(button, text);
      });
      block.appendChild(button);
    });
  }

  const bar = document.getElementById("nav-bar");
  if (bar) {
    const mark = () => bar.classList.toggle("scrolled", window.scrollY > 4);
    window.addEventListener("scroll", mark, { passive: true });
    mark();
  }
})();
