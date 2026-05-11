import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative w-full rounded-md border px-6 py-4 text-sm",
  {
    variants: {
      variant: {
        info: "border-clinora-deepBlue/30 bg-clinora-deepBlue/10 text-clinora-textPrimary",
        success:
          "border-clinora-teal/40 bg-clinora-lightTeal text-clinora-textPrimary",
        warn: "border-red-200 bg-red-50 text-red-800",
        error:
          "border-red-200 bg-red-50 text-red-800",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  },
);

function Alert({ className, variant, style, ...props }) {
  return (
    <div
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      style={{
        paddingLeft: 24,
        paddingRight: 24,
        paddingTop: 16,
        paddingBottom: 16,
        ...style,
      }}
      {...props}
    />
  );
}

export { Alert };
