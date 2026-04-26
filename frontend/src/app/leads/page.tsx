import { Header } from "@/components/layout/Header";
import { getInsights, queryRAG } from "@/lib/api";
import type { InsightsData } from "@/types";
import { TrendingUp, AlertTriangle, Flame, Brain } from "lucide-react";

export const revalidate = 120;

const CONFIDENCE_STYLE = {
  high: "text-emerald-400 bg-emerald-400/5 border-emerald-400/15",
  medium: "text-yellow-400 bg-yellow-400/5 border-yellow-400/15",
  low: "text-[#666] bg-[#1A1A1A] border-[#2A2A2A]",
};

interface InsightCardProps {
  title: string;
  description: string;
  confidence: "high" | "medium" | "low";
  category: string;
}

function InsightCard({ title, description, confidence, category }: InsightCardProps) {
  const style = CONFIDENCE_STYLE[confidence] ?? CONFIDENCE_STYLE.low;
  return (
    <div className={`rounded-xl border p-4 ${style}`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-white text-sm font-medium leading-snug">{title}</p>
        <span className="text-xs px-2 py-0.5 rounded-full border flex-shrink-0 capitalize" style={{ borderColor: "inherit", color: "inherit" }}>
          {confidence}
        </span>
      </div>
      <p className="text-[#888] text-xs leading-relaxed">{description}</p>
      <p className="text-[#444] text-xs mt-2 uppercase tracking-wide">{category.replace(/_/g, " ")}</p>
    </div>
  );
}

export default async function LeadsPage() {
  let insights: InsightsData | null = null;
  try {
    insights = await getInsights();
  } catch {
    // API offline in dev
  }

  return (
    <div className="flex flex-col h-screen">
      <Header
        title="Lead Generation"
        subtitle="AI-generated market intelligence from live news data"
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {insights ? (
          <>
            {/* Market Opportunities */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <h2 className="text-white font-medium">Market Opportunities</h2>
                <span className="text-[#444] text-sm">({insights.market_opportunities.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {insights.market_opportunities.map((item, i) => (
                  <InsightCard key={i} {...item} />
                ))}
              </div>
            </section>

            {/* Emerging Risks */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <h2 className="text-white font-medium">Emerging Risks</h2>
                <span className="text-[#444] text-sm">({insights.emerging_risks.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {insights.emerging_risks.map((item, i) => (
                  <InsightCard key={i} {...item} />
                ))}
              </div>
            </section>

            {/* Viral Topics */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Flame className="w-4 h-4 text-orange-400" />
                <h2 className="text-white font-medium">Viral Topics</h2>
                <span className="text-[#444] text-sm">({insights.viral_topics.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {insights.viral_topics.map((item, i) => (
                  <InsightCard key={i} {...item} />
                ))}
              </div>
            </section>

            <p className="text-[#333] text-xs text-center pb-4">
              Generated at {new Date(insights.generated_at).toUTCString()}
            </p>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <Brain className="w-8 h-8 text-[#333]" />
            <p className="text-[#444] text-sm">API offline — start backend to see insights</p>
          </div>
        )}
      </div>
    </div>
  );
}
