"use client";

import { Database, Cpu, Zap, Activity } from "lucide-react";
import type { SystemStats, CrawlerStats } from "@/types";

interface Props {
  stats: SystemStats | null;
  crawler: { running: boolean; stats: CrawlerStats } | null;
}

export function StatsCards({ stats, crawler }: Props) {
  const cards = [
    {
      label: "Total Articles",
      value: stats?.total?.toLocaleString() ?? "—",
      sub: `${stats?.last_day?.toLocaleString() ?? 0} today`,
      icon: Database,
      color: "text-blue-400",
      bg: "bg-blue-400/5 border-blue-400/10",
    },
    {
      label: "Active Crawlers",
      value: crawler?.stats?.active_crawlers?.toString() ?? "0",
      sub: crawler?.running ? "Running" : "Stopped",
      icon: Cpu,
      color: "text-emerald-400",
      bg: "bg-emerald-400/5 border-emerald-400/10",
    },
    {
      label: "Articles / Min",
      value: crawler?.stats?.crawlers_per_minute?.toString() ?? "0",
      sub: "Rolling 5-min avg",
      icon: Zap,
      color: "text-yellow-400",
      bg: "bg-yellow-400/5 border-yellow-400/10",
    },
    {
      label: "Sources Online",
      value: stats?.sources?.toString() ?? "—",
      sub: `${stats?.last_hour?.toLocaleString() ?? 0} last hour`,
      icon: Activity,
      color: "text-purple-400",
      bg: "bg-purple-400/5 border-purple-400/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map(({ label, value, sub, icon: Icon, color, bg }) => (
        <div
          key={label}
          className={`rounded-xl border p-5 flex items-start justify-between ${bg}`}
        >
          <div>
            <p className="text-[#666] text-xs mb-1">{label}</p>
            <p className="text-white text-2xl font-bold tabular-nums">{value}</p>
            <p className="text-[#555] text-xs mt-1">{sub}</p>
          </div>
          <Icon className={`w-5 h-5 ${color} mt-0.5`} />
        </div>
      ))}
    </div>
  );
}
