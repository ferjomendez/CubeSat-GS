import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

/** Confirmation modal; when `critical` is set, the confirm button stays disabled until the checkbox is ticked. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  body,
  critical = false,
  confirmLabel,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  body: string;
  critical?: boolean;
  confirmLabel: string;
  onConfirm: () => void;
}) {
  const [understood, setUnderstood] = useState(false);

  const confirm = () => {
    onConfirm();
    onOpenChange(false);
    setUnderstood(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{body}</DialogDescription>
        </DialogHeader>
        {critical && (
          <div className="flex items-center gap-2">
            <Checkbox id="confirm-critical" checked={understood} onCheckedChange={(v) => setUnderstood(v === true)} />
            <Label htmlFor="confirm-critical">I understand this is a critical command</Label>
          </div>
        )}
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={confirm} disabled={critical && !understood}>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
