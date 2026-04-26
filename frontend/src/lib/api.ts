import type {
  Article,
  SentimentData,
  TrendItem,
  GraphData,
  InsightsData,
  CrawlerStats,
  SystemStats,
  VolumePoint,
  CategoryCount,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }
  const res = await fetch(url.toString(), { next: { revalidate: 30 } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API POST ${path} → ${res.status}`);
  return res.json();
}

// Articles
export const getArticles = (params?: {
  category?: string;
  sentiment?: string;
  region?: string;
  limit?: number;
  offset?: number;
}) => get<Article[]>("/articles/", params as Record<string, string | number>);

export const getArticleStats = () => get<SystemStats>("/articles/stats");

// Trends
export const getTrends = () => get<TrendItem[]>("/trends/");
export const getTrendingTopics = () => get<{ name: string; count: number }[]>("/trends/topics");
export const getCategoryDistribution = (hours = 24) =>
  get<CategoryCount[]>("/trends/categories", { hours });
export const getVolumeData = (minutes = 60) =>
  get<VolumePoint[]>("/trends/volume", { minutes });

// Sentiment
export const getSentimentBreakdown = (hours = 24) =>
  get<SentimentData[]>("/sentiment/breakdown", { hours });
export const getSentimentBySource = (hours = 24) =>
  get<{ source: string; count: number; last_seen: string }[]>("/sentiment/by-source", { hours });

// Graph
export const getGraphData = (center?: string, limit = 100) =>
  get<GraphData>("/graph/subgraph", {
    ...(center ? { center } : {}),
    limit,
  });

// Insights
export const getInsights = () => get<InsightsData>("/insights/");
export const queryRAG = (question: string, top_k = 10) =>
  post<{ answer: string; sources: { title: string; url: string; score: number }[] }>(
    "/insights/query",
    { question, top_k }
  );

// Crawler control
export const getCrawlerStatus = () =>
  get<{ running: boolean; stats: CrawlerStats }>("/crawler/status");
export const startCrawlers = () => post<{ status: string }>("/crawler/start");
export const stopCrawlers = () => post<{ status: string }>("/crawler/stop");
export const setInterval = (seconds: number) =>
  fetch(`${BASE}/crawler/interval?seconds=${seconds}`, { method: "PUT" }).then((r) => r.json());

// Mystery Intelligence
export const getMysteryFeed = (limit = 50, subcategory?: string, minAnomaly = 0) =>
  get<unknown[]>("/mystery/feed", {
    limit,
    ...(subcategory ? { subcategory } : {}),
    min_anomaly: minAnomaly,
  }) as Promise<import("@/components/mystery/MysteryCard").MysteryEventData[]>;

export const getMysteryVerdicts = (limit = 20) =>
  get<unknown[]>("/mystery/verdicts", { limit }) as Promise<
    import("@/components/mystery/DeepAnalysisPanel").VerdictData[]
  >;

export const getMysterySignals = () => get<unknown[]>("/mystery/signals");

export const getMysteryScoreboard = (limit = 20) =>
  get<unknown[]>("/mystery/scoreboard", { limit }) as Promise<
    import("@/components/mystery/MysteryCard").MysteryEventData[]
  >;

export const getMysteryGraphData = (limit = 150) =>
  get<GraphData>("/graph/subgraph", { limit, node_types: "MysteryArticle,MysteryCluster" });
