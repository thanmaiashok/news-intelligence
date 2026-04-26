"use client";

import { useState, useCallback, useRef } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { NewsCard } from "./NewsCard";
import type { Article } from "@/types";

const MAX_LIVE = 200;

const CATEGORIES = [
  "all", "politics", "finance", "technology", "war_conflict",
  "health_medical", "climate_environment", "sports", "business",
];

const SENTIMENTS = ["all", "positive", "negative", "neutral"];

interface Props {
  initialArticles: Article[];
}

export function NewsStream({ initialArticles }: Props) {
  const [articles, setArticles] = useState<Article[]>(initialArticles);
  const [catFilter, setCatFilter] = useState("all");
  const [sentFilter, setSentFilter] = useState("all");
  const [liveCount, setLiveCount] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleArticle = useCallback((article: Article) => {
    setArticles((prev) => {
      const next = [article, ...prev];
      return next.slice(0, MAX_LIVE);
    });
    setLiveCount((n) => n + 1);
  }, []);

  const { connected } = useWebSocket(handleArticle);

  const filtered = articles.filter((a) => {
    if (catFilter !== "all" && !a.categories.includes(catFilter)) return false;
    if (sentFilter !== "all" && a.sentiment_label !== sentFilter) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Filters */}
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <div className="flex items-center gap-1 flex-wrap">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => setCatFilter(c)}
              className={`text-xs px-3 py-1.5 rounded-full transition-all ${
                catFilter === c
                  ? "bg-white text-black font-medium"
                  : "bg-[#1A1A1A] text-[#666] hover:text-white border border-[#2A2A2A]"
              }`}
            >
              {c === "all" ? "All Categories" : c.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {SENTIMENTS.map((s) => (
            <button
              key={s}
              onClick={() => setSentFilter(s)}
              className={`text-xs px-3 py-1.5 rounded-full transition-all ${
                sentFilter === s
                  ? "bg-white text-black font-medium"
                  : "bg-[#1A1A1A] text-[#666] hover:text-white border border-[#2A2A2A]"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <div className="ml-auto text-xs text-[#555]">
          {liveCount > 0 && (
            <span className="text-emerald-400 mr-2">+{liveCount} live</span>
          )}
          {filtered.length} articles
        </div>
      </div>

      {/* Stream */}
      <div ref={containerRef} className="flex-1 overflow-y-auto space-y-2 pr-1">
        {filtered.length === 0 ? (
          <div className="text-center text-[#444] py-20 text-sm">
            {connected ? "Waiting for articles..." : "Connecting to live feed..."}
          </div>
        ) : (
          filtered.map((a) => <NewsCard key={a.content_hash} article={a} />)
        )}
      </div>
    </div>
  );
}
