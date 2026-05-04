"use client";

import { usePolling } from "@/hooks/useNewsData";
import { Header } from "@/components/layout/Header";
import { TrendChart } from "@/components/trends/TrendChart";
import { getTrends, getCategoryDistribution, getTrendingTopics } from "@/lib/api";

const INTERVAL = 30_000;

export default function TrendsPage() {
  const { data: trends } = usePolling(getTrends, INTERVAL);
  const { data: categories } = usePolling(() => getCategoryDistribution(24), INTERVAL);
  const { data: topics } = usePolling(getTrendingTopics, INTERVAL);

  return (
    <div className="flex flex-col h-screen">
      <Header
        title="Trend Analytics"
        subtitle="Velocity spikes, category distribution, trending topics"
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <TrendChart
          trends={trends ?? []}
          categories={categories ?? []}
        />
        <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
          <p className="text-white text-sm font-medium mb-4">Top Topics (Graph DB)</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {(topics ?? []).map((t, i) => (
              <div
                key={t.name}
                className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg p-3"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-[#444] text-xs font-mono">#{i + 1}</span>
                  <span className="text-white text-sm font-medium truncate">{t.name}</span>
                </div>
                <p className="text-[#555] text-xs">{t.count} mentions</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
