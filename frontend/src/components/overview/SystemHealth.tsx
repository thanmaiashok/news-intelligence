"use client";

import { CheckCircle2, XCircle, Circle } from "lucide-react";
import type { VolumePoint } from "@/types";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const SERVICES = [
  "Kafka Broker",
  "PostgreSQL",
  "ClickHouse",
  "Neo4j",
  "Redis",
  "S3 / MinIO",
  "Vector Store",
  "API Server",
];

interface Props {
  volumeData: VolumePoint[];
}

export function SystemHealth({ volumeData }: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Volume Chart */}
      <div className="lg:col-span-2 bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-4">Articles Ingested (last 60 min)</p>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={volumeData}>
            <defs>
              <linearGradient id="vg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#fff" stopOpacity={0.12} />
                <stop offset="95%" stopColor="#fff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="minute"
              tickFormatter={(v: string) => v.slice(11, 16)}
              tick={{ fill: "#555", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#555", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip
              contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
              labelStyle={{ color: "#888" }}
              itemStyle={{ color: "#fff" }}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#fff"
              strokeWidth={1.5}
              fill="url(#vg)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Services status */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-4">Service Health</p>
        <div className="space-y-2.5">
          {SERVICES.map((svc) => (
            <div key={svc} className="flex items-center justify-between">
              <span className="text-[#888] text-sm">{svc}</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
