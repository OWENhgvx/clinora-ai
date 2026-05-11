import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-[var(--badge-px)] py-[var(--badge-py)] text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-clinora-background text-clinora-textSecondary",
        rose:
          "border-clinora-blue/40 bg-clinora-blue/10 text-clinora-blue",
        sage:
          "border-clinora-teal/40 bg-clinora-lightTeal text-clinora-teal",
        amber:
          "border-clinora-deepBlue/30 bg-clinora-deepBlue/10 text-clinora-deepBlue",
        navy:
          "border-clinora-deepBlue/30 bg-clinora-deepBlue/10 text-clinora-deepBlue",
        gold:
          "border-clinora-teal/40 bg-clinora-lightTeal text-clinora-teal",
        plum:
          "border-clinora-blue/40 bg-clinora-blue/10 text-clinora-blue",
        outline: "border-clinora-border text-clinora-textSecondary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({ className, variant, ...props }) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
