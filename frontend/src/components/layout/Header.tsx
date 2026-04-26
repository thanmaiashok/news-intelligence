"use client";

import { useWebSocket } from "@/hooks/useWebSocket";
import { Wifi, WifiOff, Clock } from "lucide-react";
import { useEffect, useState } from "react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { connected } = useWebSocket();
  const [time, setTime] = useState("");

  useEffect(() => {
    const tick = () => setTime(new Date().toUTCString().slice(17, 25) + " UTC");
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="h-16 bg-[#0B0B0B] border-b border-[#1E1E1E] flex items-center justify-between px-6 flex-shrink-0">
      <div>
        <h1 className="text-white font-semibold text-lg leading-tight">{title}</h1>
        {subtitle && <p className="text-[#666] text-xs mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-[#555] text-xs">
          <Clock className="w-3.5 h-3.5" />
          <span className="font-mono">{time}</span>
        </div>

        <div
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
            connected
              ? "text-emerald-400 border-emerald-400/20 bg-emerald-400/5"
              : "text-red-400 border-red-400/20 bg-red-400/5"
          }`}
        >
          {connected ? (
            <Wifi className="w-3 h-3" />
          ) : (
            <WifiOff className="w-3 h-3" />
          )}
          <span>{connected ? "Live" : "Offline"}</span>
        </div>
      </div>
    </header>
  );
}
