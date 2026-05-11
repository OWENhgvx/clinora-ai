import * as React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { cn } from "@/lib/utils";

const Select = SelectPrimitive.Root;
const SelectValue = SelectPrimitive.Value;

const SelectTrigger = React.forwardRef(function SelectTrigger(
  { className, children, style, ...props },
  ref,
) {
  return (
    <SelectPrimitive.Trigger
      ref={ref}
      className={cn(
        "flex h-12 w-full items-center justify-between rounded-md border border-clinora-border bg-clinora-card px-5 py-3 text-sm text-clinora-textPrimary focus:outline-none focus:ring-2 focus:ring-clinora-blue focus:ring-offset-2 focus:ring-offset-clinora-background disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      style={{
        height: 48,
        paddingLeft: 20,
        paddingRight: 20,
        paddingTop: 12,
        paddingBottom: 12,
        ...style,
      }}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon className="text-clinora-textSecondary">
        ▾
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
});

const SelectContent = React.forwardRef(function SelectContent(
  { className, children, position = "popper", ...props },
  ref,
) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        ref={ref}
        position={position}
        className={cn(
          "z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-md border border-clinora-border bg-clinora-card text-clinora-textPrimary shadow-lg",
          position === "popper" && "translate-y-1",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="p-1">
          {children}
        </SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
});

const SelectItem = React.forwardRef(function SelectItem(
  { className, children, ...props },
  ref,
) {
  return (
    <SelectPrimitive.Item
      ref={ref}
      className={cn(
        "relative flex w-full cursor-default select-none items-center rounded-sm py-2.5 pl-10 pr-4 text-sm outline-none focus:bg-clinora-lightTeal",
        className,
      )}
      {...props}
    >
      <span className="absolute left-3 flex h-3.5 w-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>✓</SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
});

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue };
