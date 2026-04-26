export interface Article {
  content_hash: string;
  url: string;
  title: string;
  source: string;
  source_type: string;
  author?: string;
  language: string;
  region?: string;
  published_at: string;
  crawled_at?: string;
  categories: string[];
  sentiment_label: "positive" | "negative" | "neutral";
  sentiment_score: number;
  entities?: Entity[];
}

export interface Entity {
  name: string;
  type: string;
  label?: string;
}

export interface SentimentData {
  label: string;
  count: number;
  avg_score: number;
}

export interface TrendItem {
  key: string;
  name: string;
  kind: string;
  current_count: number;
  prev_count: number;
  velocity: number;
  is_spike: boolean;
  computed_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface Insight {
  title: string;
  description: string;
  confidence: "high" | "medium" | "low";
  category: string;
}

export interface InsightsData {
  market_opportunities: Insight[];
  emerging_risks: Insight[];
  viral_topics: Insight[];
  generated_at: string;
}

export interface CrawlerStats {
  total_crawled: number;
  total_errors: number;
  last_run: string | null;
  active_crawlers: number;
  crawlers_per_minute: number;
}

export interface SystemStats {
  total: number;
  last_hour: number;
  last_day: number;
  sources: number;
}

export interface VolumePoint {
  minute: string;
  count: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface WSMessage {
  type: "article" | "ping";
  data?: Article;
}
