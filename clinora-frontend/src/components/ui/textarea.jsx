import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef(function Textarea(
  { className, style, ...props },
  ref,
) {
  return (
    <textarea
      className={cn(
        "min-h-[88px] w-full rounded-md border border-clinora-border bg-clinora-card px-5 py-3 text-sm text-clinora-textPrimary placeholder:text-clinora-textSecondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinora-blue focus-visible:ring-offset-2 focus-visible:ring-offset-clinora-background disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      style={{
        minHeight: 88,
        paddingLeft: 20,
        paddingRight: 20,
        paddingTop: 12,
        paddingBottom: 12,
        ...style,
      }}
      ref={ref}
      {...props}
    />
  );
});

export { Textarea };
