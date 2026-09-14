import { useGs } from "@/store/gs";

/** Full-width bar shown whenever the WS link is down. */
export function DisconnectedBanner() {
  const connected = useGs((s) => s.connected);
  if (connected) return null;
  return (
    <div className="bg-alarm/[0.14] text-alarm label flex h-7 items-center justify-center border-b border-line">
      Connection to the ground station lost — reconnecting…
    </div>
  );
}
