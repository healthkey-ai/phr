/**
 * Brand palettes for the portal.
 *
 * The whole design system is HSL triplets in CSS custom properties on `:root`
 * / `.dark` (see index.css), consumed as `hsl(var(--x))`. Nothing names a
 * colour in a component. So a brand is just a set of token values, and
 * switching brands is writing those values onto the root element — no
 * rebuild, no per-brand bundle, no component changes.
 *
 * Brands only ever set **host** tokens. The federated remotes are re-pointed
 * at those same host tokens in CSS (index.css), so they follow a brand switch
 * without any JavaScript reaching into their styling — which would be
 * impossible anyway, since their stylesheets are cross-origin and
 * `cssRules` throws on them.
 *
 * Values are HSL triplets *without* the `hsl()` wrapper, matching how
 * index.css declares them.
 */

export type BrandId = "generic" | "lymphoma" | "partner";

export type BrandTokens = Record<string, string>;

export interface Brand {
  id: BrandId;
  label: string;
  /** One line, shown under the label in the picker. */
  description: string;
  /** Swatches for the picker: [primary, secondary, accent] as HSL triplets. */
  swatches: [string, string, string];
  light: BrandTokens;
  dark: BrandTokens;
}

/**
 * The default. Deliberately empty: applying it *removes* the overrides so the
 * stylesheet's own `:root` / `.dark` values govern again. Listing the current
 * values here instead would mean every future edit to index.css had to be
 * mirrored, and would silently drift the day someone forgot.
 */
const GENERIC: Brand = {
  id: "generic",
  label: "HealthKey",
  description: "The default palette.",
  swatches: ["212 87% 33%", "210 40% 96.1%", "212 95% 40%"],
  light: {},
  dark: {},
};

/**
 * Lymphoma Research Foundation — lymphoma.org.
 *
 * Taken from the site's own theme palette (`--theme-palette-color-*` in
 * wp-content/uploads/blocksy/css/global.css) and converted to HSL triplets:
 *
 *   #280D50 deep purple   #9F73F8 lavender   #8851F6 violet
 *   #7DFFFF cyan          #A3FF4A lime       #C7E9F0 pale cyan
 *   #F8F4FF pale lavender #4B4F58 body grey
 *
 * Refined against screenshots of the live site, which is where the exact
 * values below come from: header #250E4D, left menu #9974F1, buttons #9974F0
 * on a #F8F5FF page, pill-shaped with white labels.
 *
 * The lavender carries fills — buttons, the menu — and the deep purple carries
 * the header and any brand-coloured *text*. That split is deliberate: at 70%
 * lightness the lavender is fine behind a large white button label and fails
 * behind small text on white, so `--text-brand-secondary-700` stays purple
 * while `--primary` and `--brand-700` go lavender.
 */
const LYMPHOMA: Brand = {
  id: "lymphoma",
  label: "Lymphoma Research Foundation",
  description: "Deep purple and lavender, from lymphoma.org.",
  swatches: ["262 69% 18%", "258 81% 70%", "258 100% 98%"],
  light: {
    // Sampled from the site itself: header #250E4D, left menu #9974F1,
    // buttons #9974F0 on a #F8F5FF page.
    "--primary": "258 81% 70%",
    "--primary-foreground": "0 0% 100%",
    "--background": "258 100% 98%",
    "--secondary": "258 100% 98%",
    "--secondary-foreground": "262 69% 18%",
    "--accent": "258 100% 98%",
    "--accent-foreground": "262 69% 18%",
    "--muted": "258 100% 98%",
    "--muted-foreground": "222 8% 32%",
    "--ring": "258 81% 70%",

    // Chrome. The deep purple carries the header, the lavender the menu —
    // both against white text, which is how the site uses them.
    "--header-bg": "262 69% 18%",
    "--header-foreground": "0 0% 100%",
    "--header-border": "262 69% 18%",
    "--sidebar-bg": "258 82% 70%",
    "--sidebar-foreground": "0 0% 100%",
    "--sidebar-border": "258 60% 62%",
    "--sidebar-accent": "258 70% 62%",
    "--sidebar-accent-foreground": "0 0% 100%",
    "--sidebar-active": "0 0% 100%",
    "--sidebar-active-foreground": "0 0% 100%",

    // Pill buttons.
    "--radius-control": "9999px",

    "--brand-25": "258 100% 98%",
    "--brand-50": "258 100% 95%",
    "--brand-200": "258 82% 85%",
    "--brand-700": "258 81% 70%",
    "--brand-primary-alt": "260 90% 64%",
    // Drives the federated CTAs (exact's "View Trial", hk-labs' accents), so
    // it follows the brand rather than staying green.
    "--brand-green-500": "258 81% 70%",
    "--link-primary": "260 90% 64%",
    "--link-primary-hover": "262 69% 18%",
    // Brand text on white needs the deep purple; the lavender is a fill
    // colour and cannot carry small text at 70% lightness.
    "--text-brand-secondary-700": "262 69% 18%",
  },
  dark: {
    // On a dark ground the lavender is the readable brand colour and the
    // deep purple becomes the surface it sits on.
    "--primary": "258 81% 70%",
    "--primary-foreground": "262 69% 18%",
    "--secondary": "262 40% 22%",
    "--secondary-foreground": "258 100% 98%",
    "--accent": "262 40% 22%",
    "--accent-foreground": "258 100% 98%",
    "--muted": "262 40% 22%",
    "--muted-foreground": "258 30% 75%",
    "--ring": "258 81% 70%",

    "--header-bg": "262 69% 12%",
    "--header-foreground": "0 0% 100%",
    "--header-border": "262 40% 22%",
    "--sidebar-bg": "262 55% 20%",
    "--sidebar-foreground": "258 40% 88%",
    "--sidebar-border": "262 40% 26%",
    "--sidebar-accent": "262 45% 28%",
    "--sidebar-accent-foreground": "0 0% 100%",
    "--sidebar-active": "258 81% 70%",
    "--sidebar-active-foreground": "258 81% 78%",

    "--radius-control": "9999px",

    "--brand-25": "262 50% 16%",
    "--brand-50": "262 45% 20%",
    "--brand-200": "258 60% 40%",
    "--brand-700": "258 81% 70%",
    "--brand-primary-alt": "258 85% 78%",
    "--brand-green-500": "258 81% 70%",
    "--link-primary": "258 85% 78%",
    "--link-primary-hover": "258 85% 85%",
    "--text-brand-secondary-700": "258 81% 70%",
  },
};

/**
 * Partner brand — green.
 *
 * #457350 primary, #1B3E50 secondary, #D26056 destructive, #F6F5F4 surface.
 * Sourced from a sibling record product that uses the identical token names
 * and triplet format, so these values transfer unchanged.
 */
const PARTNER: Brand = {
  id: "partner",
  label: "Partner (green)",
  description: "Forest green and deep teal.",
  swatches: ["134 25% 36%", "200 49% 21%", "40 11% 96%"],
  light: {
    "--primary": "134 25% 36%",
    "--primary-foreground": "0 0% 100%",
    "--secondary": "200 49% 21%",
    "--secondary-foreground": "0 0% 100%",
    "--accent": "40 11% 96%",
    "--accent-foreground": "0 0% 9.4%",
    "--muted": "40 11% 96%",
    "--muted-foreground": "0 0% 40%",
    "--destructive": "5 58% 58%",
    "--destructive-foreground": "0 0% 100%",
    "--ring": "134 25% 36%",
    "--brand-25": "134 30% 96%",
    "--brand-50": "134 28% 90%",
    "--brand-200": "134 25% 70%",
    "--brand-700": "134 25% 36%",
    "--brand-primary-alt": "134 25% 30%",
    "--brand-green-500": "134 25% 45%",
    "--link-primary": "134 25% 30%",
    "--link-primary-hover": "134 25% 24%",
    "--text-brand-secondary-700": "134 25% 36%",
  },
  dark: {
    "--primary": "134 25% 55%",
    "--primary-foreground": "0 0% 9.4%",
    "--secondary": "200 40% 28%",
    "--secondary-foreground": "0 0% 100%",
    "--accent": "150 8% 20%",
    "--accent-foreground": "0 0% 98%",
    "--muted": "150 8% 20%",
    "--muted-foreground": "150 8% 70%",
    "--destructive": "5 58% 58%",
    "--destructive-foreground": "0 0% 100%",
    "--ring": "134 25% 55%",
    "--brand-25": "134 20% 14%",
    "--brand-50": "134 20% 18%",
    "--brand-200": "134 22% 35%",
    "--brand-700": "134 25% 55%",
    "--brand-primary-alt": "134 25% 62%",
    "--brand-green-500": "134 30% 60%",
    "--link-primary": "134 25% 62%",
    "--link-primary-hover": "134 25% 72%",
    "--text-brand-secondary-700": "134 25% 55%",
  },
};

export const BRANDS: Brand[] = [GENERIC, LYMPHOMA, PARTNER];

export const DEFAULT_BRAND: BrandId = "generic";

export function getBrand(id: string | null | undefined): Brand {
  return BRANDS.find((b) => b.id === id) ?? GENERIC;
}

const STORAGE_KEY = "phr.brand";

/**
 * Per-device, not per-account: the choice is cosmetic, and putting it on the
 * user record would need an API field and a migration to buy cross-device
 * persistence nobody has asked for. Revisit if branding becomes a property of
 * the installation rather than the viewer (#43).
 */
export function loadBrandId(): BrandId {
  try {
    return getBrand(localStorage.getItem(STORAGE_KEY)).id;
  } catch {
    // Private browsing / storage disabled — fall back rather than break boot.
    return DEFAULT_BRAND;
  }
}

export function saveBrandId(id: BrandId): void {
  try {
    if (id === DEFAULT_BRAND) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Not being able to remember the choice is not a reason to refuse it.
  }
}

/** Every token any brand touches — used to clear cleanly between brands. */
const ALL_TOKENS = Array.from(
  new Set(BRANDS.flatMap((b) => [...Object.keys(b.light), ...Object.keys(b.dark)])),
);

/**
 * Write a brand's tokens onto `root` as inline custom properties.
 *
 * Inline beats any stylesheet declaration without `!important`, which is what
 * makes this work against the remotes' own CSS as well as our own.
 *
 * Every token is cleared first, so switching between two brands that touch
 * different token sets cannot leave the previous brand's values behind.
 */
export function applyBrand(
  id: BrandId,
  root: HTMLElement = document.documentElement,
  isDark: boolean = root.classList.contains("dark"),
): void {
  const brand = getBrand(id);
  const tokens = isDark ? brand.dark : brand.light;

  for (const name of ALL_TOKENS) root.style.removeProperty(name);
  for (const [name, value] of Object.entries(tokens)) {
    root.style.setProperty(name, value);
  }
}
