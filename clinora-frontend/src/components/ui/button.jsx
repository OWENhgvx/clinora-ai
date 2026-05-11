import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  // Base: shared across all variants and sizes
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinora-blue focus-visible:ring-offset-2 focus-visible:ring-offset-clinora-background disabled:pointer-events-none disabled:opacity-40 active:scale-[0.97]",
  {
    variants: {
      variant: {
        // Primary action
        default:
          "bg-clinora-blue text-clinora-card shadow-sm hover:bg-clinora-blueHover",
        // Subtle bordered — for secondary actions
        outline:
          "border border-clinora-border bg-transparent text-clinora-textPrimary hover:border-clinora-blue hover:bg-clinora-lightTeal hover:text-clinora-deepBlue",
        // Filled secondary action
        secondary:
          "bg-clinora-deepBlue text-clinora-card shadow-sm hover:bg-clinora-blueHover",
        // No background — for subtle inline actions
        ghost:
          "text-clinora-textPrimary hover:bg-clinora-lightTeal hover:text-clinora-deepBlue",
        // Destructive — keep true danger actions red.
        danger:
          "border border-red-200 bg-red-50 text-red-700 hover:border-red-300 hover:bg-red-100",
      },
      size: {
        // Compact inline — card action buttons, detail-panel buttons
        xs: "h-8 px-[var(--btn-px-xs)] text-[13px] rounded-md",
        // Small — toolbar buttons, secondary page actions
        sm: "h-9 px-[var(--btn-px-sm)] text-sm rounded-[9px]",
        // Standard — default for most buttons
        default: "h-10 px-[var(--btn-px-md)] text-sm rounded-[10px]",
        // Large — prominent actions, modal submit buttons
        lg: "h-11 px-[var(--btn-px-lg)] text-[15px] rounded-[11px]",
        // Extra large — primary page CTA
        xl: "h-[52px] px-[var(--btn-px-xl)] text-base rounded-[12px]",
        // Square icon button (standard)
        icon: "h-10 w-10 rounded-lg p-0 text-base",
        // Square icon button (small — close buttons, etc.)
        "icon-sm": "h-8 w-8 rounded-md p-0 text-lg leading-none",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({ className, variant, size, asChild = false, ...props }) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
