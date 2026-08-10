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

export interface Brand {
  id: BrandId;
  label: string;
  /** One line, shown under the label in the picker. */
  description: string;
  /**
   * Swatches for the picker: [primary, secondary, accent] as HSL triplets.
   * The only colours still named in TypeScript — everything else lives in
   * index.css under `[data-brand]`. Keep them in step with that block.
   */
  swatches: [string, string, string];
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
};

/**
 * Lymphoma Research Foundation — lymphoma.org.
 *
 * Palette taken from the site's own theme variables and refined against
 * screenshots of it: header #250E4D, left menu #9974F1, buttons #9974F0 on a
 * #F8F5FF page, pill-shaped with white labels.
 *
 * The lavender carries fills — buttons, the menu — and the deep purple carries
 * the header and any brand-coloured *text*. At 70% lightness the lavender sits
 * fine behind a large white button label and fails behind small text on white,
 * so `--text-brand-secondary-700` stays purple while `--primary` and
 * `--brand-700` go lavender.
 *
 * Known and accepted: white on this lavender measures **3.41:1**. That clears
 * the 3:1 bar for large text but not WCAG AA's 4.5:1 for the 14px labels on
 * buttons and menu items. Keeping it is a deliberate call — it is the colour
 * lymphoma.org actually uses, and matching the brand won over the ratio.
 * Dropping lightness to 64% reaches 4.51:1 if that trade is ever revisited.
 * Please do not "fix" this without that conversation.
 */
const LYMPHOMA: Brand = {
  id: "lymphoma",
  label: "Lymphoma Research Foundation",
  description: "Deep purple and lavender, from lymphoma.org.",
  swatches: ["262 69% 18%", "258 81% 70%", "258 100% 98%"],
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

/**
 * Point the document at a brand. The values themselves live in index.css under
 * `[data-brand="..."]`, so this only has to stamp the attribute.
 *
 * They used to be written here as inline custom properties. That worked, but it
 * could only run after mount, so every load showed one frame of the default
 * palette first; and because inline styles cannot express `.dark`, it needed a
 * MutationObserver to re-apply on theme changes. Moving the values to CSS costs
 * nothing and removes both problems — index.html sets the attribute before
 * React mounts, and the `.dark` variants are ordinary selectors.
 */
export function applyBrand(
  id: BrandId,
  root: HTMLElement = document.documentElement,
): void {
  const brand = getBrand(id);
  if (brand.id === DEFAULT_BRAND) root.removeAttribute("data-brand");
  else root.setAttribute("data-brand", brand.id);
}
