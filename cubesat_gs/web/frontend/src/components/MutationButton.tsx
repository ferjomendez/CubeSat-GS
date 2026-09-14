import type { ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const DISCONNECTED_TITLE = "Ground station connection lost";

/**
 * A mutation button gated on `!connected`. Chromium suppresses the native `title` tooltip on
 * disabled controls, so when disconnected the button is wrapped in a Radix tooltip instead —
 * Radix needs a focusable, non-disabled trigger element, hence the `span` wrapper (the standard
 * pattern for tooltips on disabled controls). Only wrapped while actually disconnected: when
 * connected, `disabled` may still be true for other reasons (e.g. invalid input) that have
 * nothing to do with the connection, so no connection tooltip is shown for those.
 */
export function MutationButton({
  connected,
  disabled,
  onClick,
  className,
  children,
}: {
  connected: boolean;
  disabled?: boolean;
  onClick: () => void;
  className: string;
  children: ReactNode;
}) {
  const button = (
    <button type="button" disabled={!connected || disabled} onClick={onClick} className={className}>
      {children}
    </button>
  );
  if (connected) return button;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0}>{button}</span>
      </TooltipTrigger>
      <TooltipContent>{DISCONNECTED_TITLE}</TooltipContent>
    </Tooltip>
  );
}
