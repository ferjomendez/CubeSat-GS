import { useEffect, useRef } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { Activity, Gauge, Orbit, Radio, Send, Settings2 } from "lucide-react";

import { connectWs } from "@/api/ws";
import { useGs } from "@/store/gs";
import { cn } from "@/lib/utils";
import { DisconnectedBanner } from "@/components/DisconnectedBanner";
import { StatusStrip } from "@/components/StatusStrip";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Overview } from "@/views/Overview";
import LiveFeed from "@/views/LiveFeed";
import { Telemetry } from "@/views/Telemetry";
import Telecommand from "@/views/Telecommand";
import { Passes } from "@/views/Passes";
import { Settings } from "@/views/Settings";

const queryClient = new QueryClient();

const NAV = [
  { to: "/", label: "Overview", icon: Gauge, end: true },
  { to: "/feed", label: "Feed", icon: Radio, end: false },
  { to: "/telemetry", label: "Telemetry", icon: Activity, end: false },
  { to: "/commands", label: "Commands", icon: Send, end: false },
  { to: "/passes", label: "Passes", icon: Orbit, end: false },
  { to: "/settings", label: "Settings", icon: Settings2, end: false },
] as const;

function Rail() {
  const alarmCount = useGs((s) => s.alarmsActive.length);
  const pendingCommand = useGs((s) => s.pendingCommand);

  return (
    <nav className="flex w-14 flex-col items-center gap-1 border-r border-line py-2" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          title={label}
          className={({ isActive }) =>
            cn(
              "relative flex h-10 w-10 items-center justify-center rounded text-dim hover:text-fg",
              isActive && "bg-raised text-info",
            )
          }
        >
          <Icon size={18} aria-hidden="true" />
          {to === "/telemetry" && alarmCount > 0 && (
            <span className="bg-alarm absolute right-1 top-1 h-1.5 w-1.5 rounded-full" aria-label={`${alarmCount} active alarms`} />
          )}
          {to === "/commands" && pendingCommand && (
            <span className="bg-info absolute right-1 top-1 h-1.5 w-1.5 rounded-full" aria-label="Command pending" />
          )}
          <span className="sr-only">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function Layout() {
  return (
    <div className="flex h-full">
      <Rail />
      <div className="flex min-w-0 flex-1 flex-col">
        <DisconnectedBanner />
        <StatusStrip />
        <main className="min-h-0 flex-1 overflow-auto p-4">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/feed" element={<LiveFeed />} />
            <Route path="/telemetry" element={<Telemetry />} />
            <Route path="/commands" element={<Telecommand />} />
            <Route path="/passes" element={<Passes />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function ToastBridge() {
  const toasts = useGs((s) => s.toasts);
  const shown = useRef(new Set<number>());

  useEffect(() => {
    for (const t of toasts) {
      if (shown.current.has(t.id)) continue;
      shown.current.add(t.id);
      if (t.kind === "alarm") toast.error(t.text);
      else toast(t.text);
    }
  }, [toasts]);

  return <Toaster theme="dark" />;
}

function WsBootstrap() {
  useEffect(() => {
    const { applyMessage, setConnected } = useGs.getState();
    const conn = connectWs(applyMessage, setConnected);
    return () => conn.close();
  }, []);
  return null;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <WsBootstrap />
          <ToastBridge />
          <Layout />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
