import { useState } from "react";
import type { CommandDefOut } from "@/api/types";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { fmtBytes } from "@/lib/format";

/**
 * Send confirmation for a defined command: payload preview, an optional hex override, and — for
 * critical commands — an alarm-dim warning callout whose checkbox gates the confirm button.
 */
export function CommandDialog({
  cmd,
  open,
  onOpenChange,
  onConfirm,
}: {
  cmd: CommandDefOut;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (payloadHexOverride: string | null) => void;
}) {
  // The dialog only exists in the tree while `open` — the parent renders it conditionally on the
  // selected command and unmounts it on cancel/confirm — so a fresh mount already starts with
  // reset state; no effect is needed to clear it.
  const [override, setOverride] = useState("");
  const [understood, setUnderstood] = useState(false);

  const confirm = () => {
    const hex = override.trim().replace(/\s+/g, "").toUpperCase();
    onConfirm(hex ? hex : null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send {cmd.name}</DialogTitle>
          <DialogDescription>{cmd.description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <div className="label">Payload</div>
            <div className="font-mono text-[13px] tabular-nums">
              {cmd.payload_text ?? cmd.payload_hex} <span className="text-dim">({fmtBytes(cmd.payload_hex)})</span>
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="payload-override">Override payload (hex)</Label>
            <Input
              id="payload-override"
              className="font-mono"
              value={override}
              onChange={(e) => setOverride(e.target.value)}
              placeholder={cmd.payload_hex}
            />
          </div>
        </div>

        {cmd.critical && (
          <div className="border-alarm/40 bg-alarm/10 text-alarm space-y-2 rounded border p-2 text-[13px]">
            <p>This command is marked critical. It will be sent exactly once.</p>
            <div className="flex items-center gap-2">
              <Checkbox id="confirm-critical" checked={understood} onCheckedChange={(v) => setUnderstood(v === true)} />
              <Label htmlFor="confirm-critical" className="text-alarm">
                I understand this is a critical command
              </Label>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={confirm} disabled={cmd.critical && !understood}>
            Send {cmd.name}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
