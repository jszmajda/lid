// The examples showcase's two enhancements. Both pages work without this script: pictures are
// links to their full-size files, and named tree nodes carry native tooltips.

// Pictures open in a dialog over the page. @spec ONB-SHOWCASE-030, ONB-SHOWCASE-031, ONB-SHOWCASE-032
const zoom = document.getElementById("zoom");
if (zoom && typeof zoom.showModal === "function") {
  const img = zoom.querySelector("img");
  const close = zoom.querySelector(".zoom-close");
  let opener = null;
  document.querySelectorAll("a[data-zoom]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const pic = link.querySelector("img");
      img.src = link.href;
      img.alt = pic ? pic.alt : "";
      opener = link;
      zoom.showModal();
      close.focus();
    });
  });
  // A click anywhere in the dialog closes it; Escape closes it through the dialog's cancel event.
  zoom.addEventListener("click", () => zoom.close());
  zoom.addEventListener("close", () => {
    img.removeAttribute("src");
    if (opener) opener.focus();
  });
}

// Tree nodes show their names on hover, focus, or tap. @spec ONB-SHOWCASE-043, ONB-SHOWCASE-044
document.querySelectorAll(".tree-wrap").forEach((wrap) => {
  const tip = wrap.querySelector(".t-tip");
  if (!tip) return;
  let current = null;
  const hide = () => {
    tip.hidden = true;
    if (current) current.classList.remove("on");
    current = null;
  };
  const show = (node) => {
    if (current && current !== node) current.classList.remove("on");
    current = node;
    node.classList.add("on");
    tip.replaceChildren();
    const name = document.createElement("b");
    name.textContent = node.dataset.name;
    const note = document.createElement("span");
    note.textContent = node.dataset.note;
    tip.append(name, note);
    tip.hidden = false;
    const box = node.getBoundingClientRect();
    const outer = wrap.getBoundingClientRect();
    const x = box.left + box.width / 2 - outer.left + wrap.scrollLeft;
    tip.style.left = `${Math.min(Math.max(x, 90 + wrap.scrollLeft), wrap.scrollLeft + outer.width - 90)}px`;
    tip.style.top = `${box.top - outer.top - 8}px`;
  };
  wrap.querySelectorAll(".t-node").forEach((node) => {
    // The label replaces the native tooltip; the accessible name moves to aria-label.
    const title = node.querySelector("title");
    if (title) {
      node.setAttribute("aria-label", title.textContent);
      title.remove();
    }
    node.addEventListener("pointerenter", () => show(node));
    node.addEventListener("pointerleave", hide);
    node.addEventListener("focus", () => show(node));
    node.addEventListener("blur", hide);
    node.addEventListener("click", (event) => {
      event.stopPropagation();
      show(node);
    });
  });
  document.addEventListener("click", (event) => {
    if (current && !wrap.contains(event.target)) hide();
  });
  document.addEventListener("focusin", (event) => {
    if (current && !current.contains(event.target)) hide();
  });
});
