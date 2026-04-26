"use client";

import { ExternalLink, ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

const SUBCAT_COLORS: Record<string, string> = {
  ufo_alien: "text-violet-400 bg-violet-400/8 border-violet-400/20",
  supernatural_paranormal: "text-indigo-400 bg-indigo-400/8 border-indigo-400/20",
  unexplained_scientific: "text-cyan-400 bg-cyan-400/8 border-cyan-400/20",
  rare_impossible: "text-orange-400 bg-orange-400/8 border-orange-400/20",
  emerging_pattern_signal: "text-yellow-400 bg-yellow-400/8 border-yellow-400/20",
};

export interface MysteryEventData {
  article_hash: string;
  url: string;
  title: string;
  source: string;
  published_at: string;
  subcategory: string;
  subcategory_label: string;
  credibility_score: number;
  anomaly_score: number;
  source_reliability: number;
  matched_signals: string[];
  region?: string;
  content_snippet: string;
}

function CredibilityBadge({ score }: { score: number }) {
  if (score >= 0.65)
    return (
      <span className="flex items-center gap-1 text-emerald-400 text-xs">
        <ShieldCheck className="w-3 h-3" /> VERIFIED
      </span>
    );
  if (score >= 0.4)
    return (
      <span className="flex items-center gap-1 text-yellow-400 text-xs">
        <ShieldAlert className="w-3 h-3" /> UNVERIFIED
      </span>
    );
  return (
    <span className="flex items-center gap-1 text-red-400 text-xs">
      <ShieldX className="w-3 h-3" /> LOW CREDIBILITY
    </span>
  );
}

function AnomalyBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.75 ? "bg-red-400" : score >= 0.55 ? "bg-orange-400" : "bg-[#444]";
  return (
    <div className="flex items-center gap-2 mt-2">
      <span className="text-[#555] text-xs w-20 flex-shrink-0">Anomaly</span>
      <div className="flex-1 h-1.5 bg-[#1E1E1E] rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[#666] text-xs font-mono w-8 text-right">{pct}%</span>
    </div>
  );
}

export function MysteryCard({ event }: { event: MysteryEventData }) {
  const catStyle = SUBCAT_COLORS[event.subcategory] ?? "text-[#888] bg-[#1A1A1A] border-[#2A2A2A]";

  function relativeTime(iso: string): string {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  return (
    <article className="bg-[#0F0F0F] border border-[#1E1E1E] rounded-xl p-4 hover:border-[#2A2A2A] transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <a
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-white text-sm font-medium leading-snug hover:text-[#ccc] transition-colors block"
          >
            {event.title}
          </a>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full border ${catStyle}`}>
              {event.subcategory_label}
            </span>
            <CredibilityBadge score={event.credibility_score} />
            {event.region && (
              <span className="text-[#444] text-xs">{event.region}</span>
            )}
            <span className="text-[#444] text-xs">{relativeTime(event.published_at)}</span>
          </div>
        </div>
        <a href={event.url} target="_blank" rel="noopener noreferrer" className="text-[#444] hover:text-white">
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>

      <AnomalyBar score={event.anomaly_score} />

      {event.content_snippet && (
        <p className="text-[#555] text-xs mt-2 leading-relaxed line-clamp-2">
          {event.content_snippet}
        </p>
      )}

      <div className="flex items-center gap-2 mt-2 flex-wrap">
        {event.matched_signals.slice(0, 4).map((sig) => (
          <span
            key={sig}
            className="text-[#444] text-xs bg-[#1A1A1A] px-2 py-0.5 rounded"
          >
            {sig}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between mt-2 text-[#444] text-xs">
        <span>{event.source}</span>
        <span className="font-mono">
          cred {Math.round(event.credibility_score * 100)}% ·{" "}
          src_rel {Math.round(event.source_reliability * 100)}%
        </span>
      </div>
    </article>
  );
}
