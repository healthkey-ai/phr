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

  // index.html already stamped the attribute before mount, so this is a no-op
  // on first render and only does work when the user picks a different brand.
  // Still an effect rather than inline in render: it mutates shared document
  // state, and React may render more than once.
  useEffect(() => {
    applyBrand(brandId);
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
