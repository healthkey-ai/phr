import css from "./labs.css?inline";

let injected = false;

export function injectStyles() {
  if (injected) return;
  injected = true;

  const imports: string[] = [];
  let rest = css.replace(
    /@import\s+(?:url\([^)]+\)|"[^"]+"|'[^']+')\s*;?/g,
    (match) => { imports.push(match); return ""; },
  );

  // Scope :root selectors to .hk-labs-root so remote theme/fallback vars
  // don't leak into the host's global scope. The remote's internal Tailwind
  // layers (theme, base, utilities) merge with the host's layers naturally.
  rest = rest.replace(/:root/g, ".hk-labs-root");

  if (imports.length > 0) {
    const fontStyle = document.createElement("style");
    fontStyle.setAttribute("data-mf", "labs-remote-fonts");
    fontStyle.textContent = imports.join("\n");
    document.head.appendChild(fontStyle);
  }

  const style = document.createElement("style");
  style.setAttribute("data-mf", "labs-remote");
  style.textContent = rest;
  document.head.appendChild(style);
}
