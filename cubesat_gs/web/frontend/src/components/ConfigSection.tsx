import { useEffect, useState } from "react";
import { AlarmBadge } from "@/components/AlarmBadge";
import { Panel } from "@/components/Panel";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export type ConfigFieldType = "text" | "number" | "select" | "textarea";
export type ConfigFieldOption = { value: string; label: string };
export type ConfigField = {
  key: string;
  label: string;
  type: ConfigFieldType;
  options?: ConfigFieldOption[];
  step?: string;
};
export type ConfigSaveResult = { appliedLive: string[]; restartRequired: boolean };

const APPLY_TONE: Record<"live" | "restart", "nominal" | "warn"> = { live: "nominal", restart: "warn" };

function toDraft(values: Record<string, unknown>, fields: ConfigField[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const f of fields) out[f.key] = values[f.key] == null ? "" : String(values[f.key]);
  return out;
}

/** A numeric field's raw draft is invalid once emptied/whitespace or not parseable — `Number("")`
 * is `0`, not "no value", so an emptied field must be caught here rather than trusted as a real 0. */
function isInvalidNumber(raw: string): boolean {
  const trimmed = raw.trim();
  return trimmed === "" || Number.isNaN(Number(trimmed));
}

/**
 * One writable config section (`gs_config.yaml`): a local draft of `values`, a "live"/"restart"
 * badge per field (from `applies`), and a Save button enabled only once the draft differs from the
 * last-saved values. Save sends only the changed keys — numbers coerced with `Number()` — and shows
 * the outcome ("Applied live" or a restart notice) for 4 s. A numeric field left empty or non-numeric
 * is invalid rather than treated as `0`: it's excluded from the save payload, shown with an inline
 * error, and disables Save for the whole section until fixed.
 */
export function ConfigSection({
  name,
  title,
  values,
  fields,
  applies,
  onSave,
}: {
  name: string;
  title: string;
  values: Record<string, unknown>;
  fields: ConfigField[];
  applies: Record<string, "live" | "restart">;
  onSave: (section: string, changed: Record<string, unknown>) => Promise<ConfigSaveResult>;
}) {
  const [draft, setDraft] = useState<Record<string, string>>(() => toDraft(values, fields));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Re-sync the draft from fresh `values` (e.g. after a save round-trips through the query cache) —
  // but only while there are no unsaved edits, so a background refetch never clobbers typing.
  useEffect(() => {
    if (!dirty) setDraft(toDraft(values, fields));
  }, [values, fields, dirty]);

  const computeChanged = (): Record<string, unknown> => {
    const out: Record<string, unknown> = {};
    for (const f of fields) {
      const raw = draft[f.key] ?? "";
      if (f.type === "number") {
        if (isInvalidNumber(raw)) continue; // invalid — excluded; Save is disabled while this holds
        const coerced = Number(raw);
        if (coerced !== values[f.key]) out[f.key] = coerced;
        continue;
      }
      if (raw !== values[f.key]) out[f.key] = raw;
    }
    return out;
  };

  const anyInvalid = fields.some((f) => f.type === "number" && isInvalidNumber(draft[f.key] ?? ""));
  const changed = computeChanged();
  const changedKeys = Object.keys(changed);
  const canSave = changedKeys.length > 0 && !saving && !anyInvalid;

  const setField = (key: string, value: string) => {
    setDirty(true);
    setDraft((d) => ({ ...d, [key]: value }));
  };

  const save = async () => {
    const payload = computeChanged();
    setSaving(true);
    try {
      const result = await onSave(name, payload);
      const fullKeys = Object.keys(payload).map((k) => `${name}.${k}`);
      const allLive = fullKeys.length > 0 && fullKeys.every((k) => result.appliedLive.includes(k));
      setMessage(allLive ? "Applied live" : "Saved — restart the ground station to apply");
      setDirty(false);
      window.setTimeout(() => setMessage(null), 4000);
    } catch {
      // Already reported to the user by `onSave` (a toast) — nothing more to do here.
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title={title} bodyClassName="flex flex-col gap-3 p-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {fields.map((f) => {
          const id = `${name}-${f.key}`;
          const applyKind = applies[`${name}.${f.key}`];
          return (
            <div key={f.key} className="space-y-1">
              <div className="flex items-center gap-2">
                <Label htmlFor={id}>{f.label}</Label>
                {applyKind && <AlarmBadge tone={APPLY_TONE[applyKind]} text={applyKind} />}
              </div>
              {f.type === "select" ? (
                <Select value={draft[f.key] ?? ""} onValueChange={(v) => setField(f.key, v)}>
                  <SelectTrigger id={id} aria-label={f.label} className="h-8 w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(f.options ?? []).map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : f.type === "textarea" ? (
                <Textarea
                  id={id}
                  className="font-mono"
                  value={draft[f.key] ?? ""}
                  onChange={(e) => setField(f.key, e.target.value)}
                />
              ) : (
                <>
                  <Input
                    id={id}
                    type={f.type === "number" ? "number" : "text"}
                    step={f.step}
                    className="h-8"
                    value={draft[f.key] ?? ""}
                    onChange={(e) => setField(f.key, e.target.value)}
                  />
                  {f.type === "number" && isInvalidNumber(draft[f.key] ?? "") && (
                    <p className="label text-alarm">Enter a number</p>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={!canSave}
          onClick={() => void save()}
          className="label rounded border border-line px-2 py-1 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
        >
          Save {title}
        </button>
        {message && <span className="label text-info">{message}</span>}
      </div>
    </Panel>
  );
}
