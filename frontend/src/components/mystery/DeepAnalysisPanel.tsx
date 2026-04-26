"use client";

import { useState } from "react";
import {
  ShieldCheck, ShieldAlert, ShieldX, ChevronDown, ChevronUp,
  Brain, Link2, AlertTriangle
} from "lucide-react";

export interface VerdictData {
  event_cluster_id: string;
  summary: string;
  connected_events: string[];
  pattern_detected: boolean;
  confidence: number;
  reasoning: string;
  classification: "coincidence" | "emerging_pattern" | "anomaly";
  verdict: "no strong connection" | "weak signal" | "strong signal";
  data_gaps?: string;
  credibility_note?: string;
  llm_used: boolean;
  analyzed_at: string;
}

const CLASSIFICATION_STYLE: Record<string, { border: string; label: string; icon: React.ReactNode }> = {
  coincidence: {
    border: "border-[#2A2A2A]",
    label: "Coincidence",
    icon: <ShieldCheck className="w-4 h-4 text-[#555]" />,
  },
  emerging_pattern: {
    border: "border-yellow-400/20",
    label: "Emerging Pattern",
    icon: <ShieldAlert className="w-4 h-4 text-yellow-400" />,
  },
  anomaly: {
    border: "border-red-400/20",
    label: "Confirmed Anomaly",
    icon: <ShieldX className="w-4 h-4 text-red-400" />,
  },
};

const VERDICT_STYLE: Record<string, string> = {
  "no strong connection": "text-[#555] bg-[#1A1A1A]",
  "weak signal": "text-yellow-400 bg-yellow-400/8",
  "strong signal": "text-red-400 bg-red-400/8",
};

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 75 ? "bg-red-400" : pct >= 55 ? "bg-yellow-400" : "bg-[#444]";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[#555] text-xs w-20">Confidence</span>
      <div className="flex-1 h-1.5 bg-[#1E1E1E] rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-mono w-8 text-right ${color.replace("bg-", "text-")}`}>
        {pct}%
      </span>
    </div>
  );
}

function VerdictCard({ verdict }: { verdict: VerdictData }) {
  const [expanded, setExpanded] = useState(false);
  const classStyle = CLASSIFICATION_STYLE[verdict.classification] ?? CLASSIFICATION_STYLE.coincidence;
  const verdictStyle = VERDICT_STYLE[verdict.verdict] ?? VERDICT_STYLE["no strong connection"];

  return (
    <div className={`bg-[#0F0F0F] border rounded-xl overflow-hidden ${classStyle.border}`}>
      {/* Header */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-[#1A1A1A] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {classStyle.icon}
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium truncate">{verdict.summary}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded ${verdictStyle}`}>
              {verdict.verdict.toUpperCase()}
            </span>
            <span className="text-[#444] text-xs">{classStyle.label}</span>
            <span className="text-[#333] text-xs">·</span>
            <span className="text-[#444] text-xs">
              {verdict.connected_events.length} events
            </span>
            {!verdict.llm_used && (
              <span className="text-[#444] text-xs bg-[#1A1A1A] px-1.5 rounded">
                rule-based
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-[#444] text-xs font-mono">
            {Math.round(verdict.confidence * 100)}%
          </span>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-[#444]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#444]" />
          )}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-[#1E1E1E] p-4 space-y-4">
          <ConfidenceBar confidence={verdict.confidence} />

          {/* Connected events */}
          {verdict.connected_events.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Link2 className="w-3.5 h-3.5 text-[#555]" />
                <span className="text-[#666] text-xs font-medium uppercase tracking-wide">
                  Connected Events
                </span>
              </div>
              <div className="space-y-1">
                {verdict.connected_events.map((title, i) => (
                  <p key={i} className="text-[#888] text-sm leading-snug">
                    {i + 1}. {title}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Brain className="w-3.5 h-3.5 text-[#555]" />
              <span className="text-[#666] text-xs font-medium uppercase tracking-wide">
                Reasoning {verdict.llm_used ? "(LLM)" : "(Rule-based)"}
              </span>
            </div>
            <p className="text-[#777] text-sm leading-relaxed">{verdict.reasoning}</p>
          </div>

          {/* Data gaps */}
          {verdict.data_gaps && (
            <div className="bg-[#1A1A1A] rounded-lg p-3">
              <p className="text-[#555] text-xs font-medium mb-1">Data Gaps</p>
              <p className="text-[#666] text-xs">{verdict.data_gaps}</p>
            </div>
          )}

          {/* Credibility note */}
          {verdict.credibility_note && (
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-yellow-400/70 text-xs">{verdict.credibility_note}</p>
            </div>
          )}

          <p className="text-[#333] text-xs">
            Analyzed: {new Date(verdict.analyzed_at).toUTCString()}
          </p>
        </div>
      )}
    </div>
  );
}

interface Props {
  verdicts: VerdictData[];
}

export function DeepAnalysisPanel({ verdicts }: Props) {
  const strong = verdicts.filter((v) => v.verdict === "strong signal");
  const weak = verdicts.filter((v) => v.verdict === "weak signal");
  const none = verdicts.filter((v) => v.verdict === "no strong connection");

  return (
    <div className="space-y-4">
      {verdicts.length === 0 ? (
        <div className="text-center text-[#333] py-16">
          <Brain className="w-8 h-8 text-[#222] mx-auto mb-3" />
          <p className="text-sm">No verdicts yet. System analyses patterns as events accumulate.</p>
        </div>
      ) : (
        <>
          {strong.length > 0 && (
            <section>
              <p className="text-red-400 text-xs font-medium uppercase tracking-wide mb-2">
                Strong Signals ({strong.length})
              </p>
              <div className="space-y-2">
                {strong.map((v, i) => <VerdictCard key={i} verdict={v} />)}
              </div>
            </section>
          )}
          {weak.length > 0 && (
            <section>
              <p className="text-yellow-400 text-xs font-medium uppercase tracking-wide mb-2">
                Weak Signals ({weak.length})
              </p>
              <div className="space-y-2">
                {weak.map((v, i) => <VerdictCard key={i} verdict={v} />)}
              </div>
            </section>
          )}
          {none.length > 0 && (
            <section>
              <p className="text-[#444] text-xs font-medium uppercase tracking-wide mb-2">
                No Connection Found ({none.length})
              </p>
              <div className="space-y-2">
                {none.map((v, i) => <VerdictCard key={i} verdict={v} />)}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
