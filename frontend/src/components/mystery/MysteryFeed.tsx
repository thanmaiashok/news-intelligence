"use client";

import { useState } from "react";
import type { MysteryEventData } from "./MysteryCard";
import { MysteryCard } from "./MysteryCard";
import { Eye } from "lucide-react";

const SUBCATEGORIES = [
  { key: "", label: "All Types" },
  { key: "ufo_alien", label: "UFO / Alien" },
  { key: "supernatural_paranormal", label: "Paranormal" },
  { key: "unexplained_scientific", label: "Scientific Anomaly" },
  { key: "rare_impossible", label: "Rare Event" },
  { key: "emerging_pattern_signal", label: "Pattern Signal" },
];

const CONFIDENCE_FILTERS = [
  { key: 0, label: "All Confidence" },
  { key: 0.5, label: "≥ 50%" },
  { key: 0.65, label: "≥ 65%" },
  { key: 0.8, label: "≥ 80%" },
];

interface Props {
  events: MysteryEventData[];
}

export function MysteryFeed({ events }: Props) {
  const [subcat, setSubcat] = useState("");
  const [minAnomaly, setMinAnomaly] = useState(0);

  const filtered = events.filter((e) => {
    if (subcat && e.subcategory !== subcat) return false;
    if (e.anomaly_score < minAnomaly) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="flex flex-wrap gap-1">
          {SUBCATEGORIES.map((s) => (
            <button
              key={s.key}
              onClick={() => setSubcat(s.key)}
              className={`text-xs px-3 py-1.5 rounded-full transition-all ${
                subcat === s.key
                  ? "bg-white text-black font-medium"
                  : "bg-[#1A1A1A] text-[#666] hover:text-white border border-[#2A2A2A]"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1 ml-2">
          {CONFIDENCE_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setMinAnomaly(f.key)}
              className={`text-xs px-3 py-1.5 rounded-full transition-all ${
                minAnomaly === f.key
                  ? "bg-white text-black font-medium"
                  : "bg-[#1A1A1A] text-[#666] hover:text-white border border-[#2A2A2A]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <span className="ml-auto text-[#444] text-xs">
          <Eye className="w-3.5 h-3.5 inline mr-1" />
          {filtered.length} events
        </span>
      </div>

      {/* Events */}
      {filtered.length === 0 ? (
        <div className="text-center text-[#333] py-16 text-sm">
          No mystery events detected matching filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {filtered.map((e) => (
            <MysteryCard key={e.article_hash} event={e} />
          ))}
        </div>
      )}
    </div>
  );
}
