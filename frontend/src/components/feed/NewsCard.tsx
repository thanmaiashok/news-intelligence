"use client";

import type { Article } from "@/types";
import { ExternalLink, Clock } from "lucide-react";

const SENTIMENT_STYLE = {
  positive: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  negative: "text-red-400 bg-red-400/10 border-red-400/20",
  neutral: "text-[#888] bg-[#888]/10 border-[#888]/20",
};

const CAT_COLORS: Record<string, string> = {
  politics: "bg-blue-500/10 text-blue-400",
  finance: "bg-emerald-500/10 text-emerald-400",
  technology: "bg-purple-500/10 text-purple-400",
  war_conflict: "bg-red-500/10 text-red-400",
  health_medical: "bg-pink-500/10 text-pink-400",
  climate_environment: "bg-teal-500/10 text-teal-400",
  sports: "bg-orange-500/10 text-orange-400",
  business: "bg-yellow-500/10 text-yellow-400",
};

interface Props {
  article: Article;
}

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function NewsCard({ article }: Props) {
  const sentStyle =
    SENTIMENT_STYLE[article.sentiment_label] ?? SENTIMENT_STYLE.neutral;

  return (
    <article className="bg-[#111] border border-[#1E1E1E] rounded-xl p-4 hover:border-[#333] transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-white text-sm font-medium leading-snug hover:text-[#ccc] transition-colors line-clamp-2 block"
          >
            {article.title}
          </a>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-[#555] text-xs">{article.source}</span>
            {article.region && (
              <span className="text-[#444] text-xs">· {article.region}</span>
            )}
            <div className="flex items-center gap-1 text-[#444] text-xs">
              <Clock className="w-3 h-3" />
              {relativeTime(article.published_at)}
            </div>
          </div>

          {/* Categories */}
          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            {article.categories.slice(0, 3).map((cat) => (
              <span
                key={cat}
                className={`text-xs px-2 py-0.5 rounded-full ${
                  CAT_COLORS[cat] ?? "bg-[#1E1E1E] text-[#666]"
                }`}
              >
                {cat.replace(/_/g, " ")}
              </span>
            ))}
            <span
              className={`text-xs px-2 py-0.5 rounded-full border ${sentStyle}`}
            >
              {article.sentiment_label}
            </span>
          </div>
        </div>

        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#444] hover:text-white transition-colors flex-shrink-0 mt-0.5"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </article>
  );
}
