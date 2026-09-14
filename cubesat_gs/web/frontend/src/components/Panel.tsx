import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({
  title,
  actions,
  className,
  bodyClassName,
  children,
}: {
  title: string;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children?: ReactNode;
}) {
  return (
    <div className={cn("panel flex flex-col", className)}>
      <div className="panel-title">
        <span>{title}</span>
        {actions}
      </div>
      <div className={cn("min-h-0 flex-1", bodyClassName)}>{children}</div>
    </div>
  );
}
