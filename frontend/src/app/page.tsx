"use client";

import { usePolling } from "@/hooks/useNewsData";
import { Header } from "@/components/layout/Header";
import { StatsCards } from "@/components/overview/StatsCards";
import { SystemHealth } from "@/components/overview/SystemHealth";
import { getArticleStats, getCrawlerStatus, getVolumeData } from "@/lib/api";

const INTERVAL = 30_000;

export default function OverviewPage() {
  const { data: stats } = usePolling(getArticleStats, INTERVAL);
  const { data: crawler } = usePolling(getCrawlerStatus, INTERVAL);
  const { data: volume } = usePolling(() => getVolumeData(60), INTERVAL);

  return (
    <div className="flex flex-col h-screen">
      <Header title="Overview" subtitle="System status and key metrics" />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <StatsCards stats={stats} crawler={crawler} />
        <SystemHealth volumeData={volume ?? []} />
      </div>
    </div>
  );
}
