import { Header } from "@/components/layout/Header";
import { StatsCards } from "@/components/overview/StatsCards";
import { SystemHealth } from "@/components/overview/SystemHealth";
import { getArticleStats, getCrawlerStatus, getVolumeData } from "@/lib/api";

export const revalidate = 30;

export default async function OverviewPage() {
  const [stats, crawler, volume] = await Promise.allSettled([
    getArticleStats(),
    getCrawlerStatus(),
    getVolumeData(60),
  ]);

  return (
    <div className="flex flex-col h-screen">
      <Header title="Overview" subtitle="System status and key metrics" />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <StatsCards
          stats={stats.status === "fulfilled" ? stats.value : null}
          crawler={crawler.status === "fulfilled" ? crawler.value : null}
        />
        <SystemHealth
          volumeData={volume.status === "fulfilled" ? volume.value : []}
        />
      </div>
    </div>
  );
}
