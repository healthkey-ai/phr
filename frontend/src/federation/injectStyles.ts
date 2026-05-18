import css from "./federation.css?inline";

let injected = false;

export function injectStyles() {
  if (injected) return;
  injected = true;
  const style = document.createElement("style");
  style.setAttribute("data-mf", "labs-remote");
  style.textContent = css;
  document.head.appendChild(style);
}
