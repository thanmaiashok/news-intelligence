"use client";

import type { TrendItem, CategoryCount } from "@/types";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from "recharts";
import { Flame } from "lucide-react";

interface Props {
  trends: TrendItem[];
  categories: CategoryCount[];
}

export function TrendChart({ trends, categories }: Props) {
  const topTrends = trends.slice(0, 10);
  const radarData = categories.slice(0, 8).map((c) => ({
    category: c.category.replace(/_/g, " "),
    count: c.count,
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Velocity bar chart */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Flame className="w-4 h-4 text-orange-400" />
          <p className="text-white text-sm font-medium">Trending Velocity</p>
          <span className="text-[#555] text-xs ml-auto">current / prev window</span>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={topTrends} layout="vertical">
            <XAxis
              type="number"
              tick={{ fill: "#555", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={130}
              tick={{ fill: "#888", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: string) => v.slice(0, 18)}
            />
            <Tooltip
              contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
              labelStyle={{ color: "#888" }}
              formatter={(v: number) => [`${v}x`, "Velocity"]}
            />
            <Bar
              dataKey="velocity"
              fill="#fff"
              radius={[0, 4, 4, 0]}
              label={{
                position: "right",
                fill: "#555",
                fontSize: 10,
                formatter: (v: number) => v > 2.5 ? "🔥" : "",
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Category radar */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-4">Category Distribution (24h)</p>
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={radarData}>
            <PolarGrid stroke="#1E1E1E" />
            <PolarAngleAxis
              dataKey="category"
              tick={{ fill: "#666", fontSize: 10 }}
            />
            <Radar
              dataKey="count"
              stroke="#fff"
              fill="#fff"
              fillOpacity={0.08}
              strokeWidth={1.5}
            />
            <Tooltip
              contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
              labelStyle={{ color: "#888" }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Spike alerts */}
      <div className="lg:col-span-2 bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-3">Active Spikes</p>
        <div className="flex flex-wrap gap-2">
          {trends.filter((t) => t.is_spike).length === 0 ? (
            <p className="text-[#444] text-sm">No spikes detected in current window.</p>
          ) : (
            trends
              .filter((t) => t.is_spike)
              .map((t) => (
                <div
                  key={t.key}
                  className="flex items-center gap-2 bg-orange-400/5 border border-orange-400/15 rounded-lg px-3 py-2"
                >
                  <Flame className="w-3.5 h-3.5 text-orange-400" />
                  <span className="text-white text-sm">{t.name.replace(/:/g, " → ")}</span>
                  <span className="text-orange-400 text-xs font-mono">{t.velocity.toFixed(1)}x</span>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}
