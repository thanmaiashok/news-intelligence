"use client";

import type { MysteryEventData } from "./MysteryCard";
import { Flame, ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

interface Props {
  events: MysteryEventData[];
}

function credIcon(score: number) {
  if (score >= 0.65) return <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />;
  if (score >= 0.4) return <ShieldAlert className="w-3.5 h-3.5 text-yellow-400" />;
  return <ShieldX className="w-3.5 h-3.5 text-red-400" />;
}

function anomalyColor(score: number): string {
  if (score >= 0.8) return "text-red-400";
  if (score >= 0.65) return "text-orange-400";
  if (score >= 0.5) return "text-yellow-400";
  return "text-[#666]";
}

export function AnomalyScoreboard({ events }: Props) {
  const ranked = [...events]
    .sort((a, b) => b.anomaly_score - a.anomaly_score)
    .slice(0, 20);

  return (
    <div className="bg-[#111] border border-[#1E1E1E] rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-[#1E1E1E]">
        <Flame className="w-4 h-4 text-orange-400" />
        <p className="text-white text-sm font-medium">Anomaly Scoreboard</p>
        <span className="text-[#444] text-xs ml-auto">ranked by anomaly score</span>
      </div>

      {ranked.length === 0 ? (
        <div className="text-center text-[#333] py-8 text-sm">No anomalies detected yet.</div>
      ) : (
        <div className="divide-y divide-[#1A1A1A]">
          {ranked.map((event, i) => (
            <div
              key={event.article_hash}
              className="flex items-center gap-3 px-5 py-3 hover:bg-[#1A1A1A] transition-colors"
            >
              {/* Rank */}
              <span className="text-[#333] font-mono text-sm w-6 flex-shrink-0">
                #{i + 1}
              </span>

              {/* Score */}
              <div className="flex-shrink-0 w-14 text-center">
                <span className={`text-lg font-bold tabular-nums ${anomalyColor(event.anomaly_score)}`}>
                  {Math.round(event.anomaly_score * 100)}
                </span>
                <p className="text-[#333] text-xs">score</p>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <a
                  href={event.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white text-sm hover:text-[#ccc] transition-colors block truncate"
                >
                  {event.title}
                </a>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[#555] text-xs">{event.subcategory_label}</span>
                  <span className="text-[#333] text-xs">·</span>
                  <span className="text-[#555] text-xs">{event.source}</span>
                  {event.region && (
                    <>
                      <span className="text-[#333] text-xs">·</span>
                      <span className="text-[#555] text-xs">{event.region}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Credibility */}
              <div className="flex flex-col items-center flex-shrink-0">
                {credIcon(event.credibility_score)}
                <span className="text-[#444] text-xs mt-0.5">
                  {Math.round(event.credibility_score * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
