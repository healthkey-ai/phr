import { forwardRef, type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative w-full rounded border px-3 py-2 text-sm",
  {
    variants: {
      variant: {
        default: "border-border bg-background text-foreground",
        destructive: "border-destructive/50 bg-error-50 text-destructive",
        success: "border-green-400/50 bg-success-50 text-green-100",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

const Alert = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>
>(({ className, variant, ...props }, ref) => (
  <div ref={ref} role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
));
Alert.displayName = "Alert";

export { Alert };
