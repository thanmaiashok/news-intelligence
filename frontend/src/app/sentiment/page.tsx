"use client";

import { usePolling } from "@/hooks/useNewsData";
import { Header } from "@/components/layout/Header";
import { SentimentGauge } from "@/components/sentiment/SentimentGauge";
import { getSentimentBreakdown, getSentimentBySource } from "@/lib/api";

const INTERVAL = 30_000;

export default function SentimentPage() {
  const { data: breakdown } = usePolling(() => getSentimentBreakdown(24), INTERVAL);
  const { data: bySrc } = usePolling(() => getSentimentBySource(24), INTERVAL);

  return (
    <div className="flex flex-col h-screen">
      <Header
        title="Sentiment Dashboard"
        subtitle="Positive / Negative / Neutral breakdown across sources"
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <SentimentGauge breakdown={breakdown ?? []} />
        <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
          <p className="text-white text-sm font-medium mb-4">Articles by Source (24h)</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#555] border-b border-[#1E1E1E]">
                  <th className="text-left pb-3 font-normal">Source</th>
                  <th className="text-right pb-3 font-normal">Articles</th>
                  <th className="text-right pb-3 font-normal">Last Seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1A1A1A]">
                {(bySrc ?? []).slice(0, 30).map((s) => (
                  <tr key={s.source} className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 text-[#ccc]">{s.source}</td>
                    <td className="py-2.5 text-right text-white font-mono">{s.count}</td>
                    <td className="py-2.5 text-right text-[#555] text-xs">
                      {new Date(s.last_seen).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
