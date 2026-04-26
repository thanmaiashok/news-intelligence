"use client";

import { Header } from "@/components/layout/Header";
import { CrawlerControl } from "@/components/control/CrawlerControl";
import { usePolling } from "@/hooks/useNewsData";
import { getCrawlerStatus } from "@/lib/api";
import { RefreshCw } from "lucide-react";

export default function ControlPage() {
  const { data, loading, refetch } = usePolling(getCrawlerStatus, 5000);

  return (
    <div className="flex flex-col h-screen">
      <Header title="System Control" subtitle="Manage crawlers, sources, and intervals" />
      <div className="flex-1 overflow-y-auto p-6">
        {loading && !data ? (
          <div className="flex items-center justify-center h-40">
            <RefreshCw className="w-5 h-5 text-[#444] animate-spin" />
          </div>
        ) : (
          <CrawlerControl
            running={data?.running ?? false}
            stats={data?.stats ?? null}
            onRefresh={refetch}
          />
        )}
      </div>
    </div>
  );
}
