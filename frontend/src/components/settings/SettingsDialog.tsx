import { Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useBrand } from "@/contexts/BrandContext";
import { BRANDS } from "@/lib/branding";
import type { Brand } from "@/lib/branding";
import { cn } from "@/lib/utils";

function Swatches({ brand }: { brand: Brand }) {
  return (
    <span className="flex shrink-0 items-center gap-1" aria-hidden="true">
      {brand.swatches.map((triplet, i) => (
        <span
          key={i}
          className="h-5 w-5 rounded-full border border-border"
          style={{ backgroundColor: `hsl(${triplet})` }}
        />
      ))}
    </span>
  );
}

export default function SettingsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { brandId, setBrandId } = useBrand();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Choose how the portal looks. Saved on this device.
          </DialogDescription>
        </DialogHeader>

        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-foreground">Brand</legend>
          {BRANDS.map((brand) => {
            const selected = brand.id === brandId;
            return (
              <label
                key={brand.id}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors",
                  selected
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-accent",
                )}
              >
                <input
                  type="radio"
                  name="brand"
                  value={brand.id}
                  checked={selected}
                  onChange={() => setBrandId(brand.id)}
                  className="sr-only"
                />
                <Swatches brand={brand} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">
                    {brand.label}
                  </span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {brand.description}
                  </span>
                </span>
                {selected && <Check className="h-4 w-4 shrink-0 text-primary" />}
              </label>
            );
          })}
        </fieldset>
      </DialogContent>
    </Dialog>
  );
}
