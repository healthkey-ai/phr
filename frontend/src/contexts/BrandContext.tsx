import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { applyBrand, loadBrandId, saveBrandId } from "@/lib/branding";
import type { BrandId } from "@/lib/branding";

interface BrandContextValue {
  brandId: BrandId;
  setBrandId: (id: BrandId) => void;
}

const BrandContext = createContext<BrandContextValue | null>(null);

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brandId, setBrandIdState] = useState<BrandId>(() => loadBrandId());

  // Applied in an effect rather than at render: writing to documentElement is
  // a side effect on shared state, and React may render more than once.
  useEffect(() => {
    applyBrand(brandId);
  }, [brandId]);

  // Brands carry separate light and dark token sets, and the applied values
  // are inline on the root element, so they cannot re-resolve on their own
  // when the theme flips. Watch the class that drives dark mode and re-apply.
  // Nothing toggles `.dark` in the portal today; this exists so that whoever
  // adds a theme switch does not have to discover the coupling first.
  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => applyBrand(brandId, root));
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, [brandId]);

  const setBrandId = useCallback((id: BrandId) => {
    setBrandIdState(id);
    saveBrandId(id);
  }, []);

  const value = useMemo(() => ({ brandId, setBrandId }), [brandId, setBrandId]);

  return <BrandContext.Provider value={value}>{children}</BrandContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useBrand(): BrandContextValue {
  const ctx = useContext(BrandContext);
  if (!ctx) throw new Error("useBrand must be used within a BrandProvider");
  return ctx;
}
