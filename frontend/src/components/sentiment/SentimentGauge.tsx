"use client";

import type { SentimentData } from "@/types";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";

const COLORS: Record<string, string> = {
  positive: "#34d399",
  negative: "#f87171",
  neutral: "#6b7280",
};

interface Props {
  breakdown: SentimentData[];
}

export function SentimentGauge({ breakdown }: Props) {
  const total = breakdown.reduce((s, d) => s + d.count, 0);

  const pieData = breakdown.map((d) => ({
    name: d.label,
    value: d.count,
    color: COLORS[d.label] ?? "#888",
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Donut */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-2">Overall Sentiment (24h)</p>
        <p className="text-[#555] text-xs mb-4">{total.toLocaleString()} articles analyzed</p>

        <div className="flex items-center gap-6">
          <ResponsiveContainer width={180} height={180}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
              >
                {pieData.map((d) => (
                  <Cell key={d.name} fill={d.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
                formatter={(v: number) => [v.toLocaleString(), "articles"]}
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="space-y-3">
            {breakdown.map((d) => (
              <div key={d.label}>
                <div className="flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: COLORS[d.label] ?? "#888" }}
                  />
                  <span className="text-[#888] text-sm capitalize">{d.label}</span>
                </div>
                <p className="text-white font-bold text-xl ml-4.5">
                  {total > 0 ? Math.round((d.count / total) * 100) : 0}%
                </p>
                <p className="text-[#555] text-xs ml-4.5">
                  {d.count.toLocaleString()} · avg {d.avg_score.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bar breakdown */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-4">Volume by Sentiment</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={breakdown} barCategoryGap="30%">
            <CartesianGrid vertical={false} stroke="#1A1A1A" />
            <XAxis
              dataKey="label"
              tick={{ fill: "#666", fontSize: 12, textTransform: "capitalize" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#555", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {breakdown.map((d) => (
                <Cell key={d.label} fill={COLORS[d.label] ?? "#888"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
