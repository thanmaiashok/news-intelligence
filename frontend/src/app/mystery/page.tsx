"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { MysteryFeed } from "@/components/mystery/MysteryFeed";
import { AnomalyScoreboard } from "@/components/mystery/AnomalyScoreboard";
import { DeepAnalysisPanel } from "@/components/mystery/DeepAnalysisPanel";
import { MysteryGraphView } from "@/components/mystery/MysteryGraphView";
import { usePolling } from "@/hooks/useNewsData";
import {
  getMysteryFeed,
  getMysteryVerdicts,
  getMysteryGraphData,
  getMysteryScoreboard,
} from "@/lib/api";
import type { MysteryEventData } from "@/components/mystery/MysteryCard";
import type { VerdictData } from "@/components/mystery/DeepAnalysisPanel";
import type { GraphData } from "@/types";
import { AlertTriangle, Rss, BarChart2, Network, Brain, RefreshCw } from "lucide-react";

type Tab = "feed" | "scoreboard" | "graph" | "analysis";

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: "feed", label: "Mystery Feed", icon: Rss },
  { key: "scoreboard", label: "Anomaly Scoreboard", icon: BarChart2 },
  { key: "graph", label: "Connection View", icon: Network },
  { key: "analysis", label: "Deep Analysis", icon: Brain },
];

export default function MysteryPage() {
  const [activeTab, setActiveTab] = useState<Tab>("feed");

  const { data: feedData, loading: feedLoading } = usePolling<MysteryEventData[]>(
    () => getMysteryFeed(100),
    30000
  );

  const { data: verdicts, loading: verdictsLoading } = usePolling<VerdictData[]>(
    () => getMysteryVerdicts(50),
    60000
  );

  const { data: graphData, loading: graphLoading } = usePolling<GraphData>(
    () => getMysteryGraphData(200),
    120000
  );

  const { data: scoreboard } = usePolling<MysteryEventData[]>(
    () => getMysteryScoreboard(25),
    30000
  );

  const events = feedData ?? [];
  const strongSignals = verdicts?.filter((v) => v.verdict !== "no strong connection").length ?? 0;

  return (
    <div className="flex flex-col h-screen">
      <Header
        title="Mystery Intelligence"
        subtitle="Anomaly detection · Pattern analysis · LLM-verified signals only"
      />

      {/* Warning banner */}
      <div className="mx-6 mt-4 flex items-start gap-2 bg-yellow-400/5 border border-yellow-400/15 rounded-xl px-4 py-3">
        <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
        <p className="text-yellow-400/80 text-xs leading-relaxed">
          <span className="font-medium">Evidence-first system.</span> All connections require{" "}
          confidence &gt; 55% and multiple independent sources. Low-credibility sources are
          rejected. Uncertainty is explicitly stated. This is not entertainment — treat all outputs
          as hypotheses requiring further verification.
        </p>
      </div>

      {/* Stats strip */}
      <div className="flex items-center gap-4 px-6 mt-4 flex-wrap">
        <div className="bg-[#111] border border-[#1E1E1E] rounded-lg px-4 py-2 flex items-center gap-2">
          <span className="text-white font-bold">{events.length}</span>
          <span className="text-[#555] text-sm">mystery events</span>
        </div>
        <div className="bg-[#111] border border-[#1E1E1E] rounded-lg px-4 py-2 flex items-center gap-2">
          <span className="text-red-400 font-bold">{strongSignals}</span>
          <span className="text-[#555] text-sm">active signals</span>
        </div>
        <div className="bg-[#111] border border-[#1E1E1E] rounded-lg px-4 py-2 flex items-center gap-2">
          <span className="text-white font-bold">{verdicts?.length ?? 0}</span>
          <span className="text-[#555] text-sm">LLM analyses</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-6 mt-4 border-b border-[#1E1E1E] pb-0">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm transition-all border-b-2 -mb-px ${
              activeTab === key
                ? "text-white border-white"
                : "text-[#555] border-transparent hover:text-[#888]"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "feed" && (
          feedLoading && !feedData ? (
            <div className="flex items-center justify-center h-40">
              <RefreshCw className="w-5 h-5 text-[#444] animate-spin" />
            </div>
          ) : (
            <MysteryFeed events={events} />
          )
        )}

        {activeTab === "scoreboard" && (
          <AnomalyScoreboard events={scoreboard ?? events} />
        )}

        {activeTab === "graph" && (
          <div className="h-[calc(100vh-320px)] min-h-[400px]">
            {graphLoading || !graphData ? (
              <div className="w-full h-full bg-[#111] border border-[#1E1E1E] rounded-xl flex items-center justify-center">
                <RefreshCw className="w-5 h-5 text-[#444] animate-spin" />
              </div>
            ) : (
              <MysteryGraphView data={graphData} />
            )}
          </div>
        )}

        {activeTab === "analysis" && (
          verdictsLoading && !verdicts ? (
            <div className="flex items-center justify-center h-40">
              <RefreshCw className="w-5 h-5 text-[#444] animate-spin" />
            </div>
          ) : (
            <DeepAnalysisPanel verdicts={verdicts ?? []} />
          )
        )}
      </div>
    </div>
  );
}
