import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Custom tailwind-merge instance that knows about HealthKey/healthkey tokens.
 *
 * Without this, twMerge would treat custom `text-*` classes (e.g. `text-body-lg`,
 * `text-healthkey-text-white`) as conflicting with each other and drop one,
 * resulting in buttons that lose their text color.
 *
 * Both lists must stay in sync with tailwind.config.ts.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      // Custom font-size scale from tailwind.config.ts → fontSize
      "font-size": [
        {
          text: [
            "display",
            "h1",
            "h2",
            "h3",
            "h4",
            "body-lg",
            "body",
            "body-sm",
            "caption",
          ],
        },
      ],
      // Custom text colors from the healthkey.* namespace
      "text-color": [
        {
          text: [
            "healthkey-text-primary",
            "healthkey-text-secondary",
            "healthkey-text-tertiary",
            "healthkey-text-quaternary",
            "healthkey-text-disabled",
            "healthkey-text-brand",
            "healthkey-text-white",
            "healthkey-link-primary",
            "healthkey-link-hover",
          ],
        },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
