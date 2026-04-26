"use client";

import { useState } from "react";
import { startCrawlers, stopCrawlers, setInterval as setCrawlInterval } from "@/lib/api";
import type { CrawlerStats } from "@/types";
import { Play, Square, RefreshCw, Clock, Bug, Activity } from "lucide-react";

interface Props {
  running: boolean;
  stats: CrawlerStats | null;
  onRefresh: () => void;
}

export function CrawlerControl({ running, stats, onRefresh }: Props) {
  const [loading, setLoading] = useState(false);
  const [interval, setIntervalVal] = useState(300);
  const [msg, setMsg] = useState("");

  async function toggle() {
    setLoading(true);
    setMsg("");
    try {
      if (running) {
        await stopCrawlers();
        setMsg("Crawlers stopped.");
      } else {
        await startCrawlers();
        setMsg("Crawlers started.");
      }
      onRefresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  async function applyInterval() {
    try {
      await setCrawlInterval(interval);
      setMsg(`Interval set to ${interval}s`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <div className="space-y-4">
      {/* Status + toggle */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-white font-medium">Crawler Engine</p>
            <p className="text-[#555] text-sm">
              Status:{" "}
              <span className={running ? "text-emerald-400" : "text-red-400"}>
                {running ? "Running" : "Stopped"}
              </span>
            </p>
          </div>
          <button
            onClick={toggle}
            disabled={loading}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              running
                ? "bg-red-500/10 text-red-400 border border-red-400/20 hover:bg-red-500/20"
                : "bg-emerald-500/10 text-emerald-400 border border-emerald-400/20 hover:bg-emerald-500/20"
            } disabled:opacity-50`}
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : running ? (
              <Square className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {loading ? "Processing..." : running ? "Stop Crawlers" : "Start Crawlers"}
          </button>
        </div>

        {msg && (
          <div className="text-sm text-[#888] bg-[#1A1A1A] rounded-lg px-4 py-2">{msg}</div>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Crawled", value: stats.total_crawled?.toLocaleString(), icon: Activity },
            { label: "Active", value: stats.active_crawlers?.toString(), icon: RefreshCw },
            { label: "Per Minute", value: stats.crawlers_per_minute?.toString(), icon: Clock },
            { label: "Errors", value: stats.total_errors?.toString(), icon: Bug },
          ].map(({ label, value, icon: Icon }) => (
            <div
              key={label}
              className="bg-[#111] border border-[#1E1E1E] rounded-xl p-4 flex items-center gap-3"
            >
              <Icon className="w-4 h-4 text-[#555]" />
              <div>
                <p className="text-[#555] text-xs">{label}</p>
                <p className="text-white font-bold">{value ?? "—"}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Interval control */}
      <div className="bg-[#111] border border-[#1E1E1E] rounded-xl p-5">
        <p className="text-white text-sm font-medium mb-3">Crawl Frequency</p>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={60}
            max={1800}
            step={60}
            value={interval}
            onChange={(e) => setIntervalVal(Number(e.target.value))}
            className="flex-1 accent-white"
          />
          <span className="text-white text-sm w-20 text-right font-mono">{interval}s</span>
          <button
            onClick={applyInterval}
            className="px-4 py-2 bg-white text-black text-sm font-medium rounded-lg hover:bg-[#ddd] transition-colors"
          >
            Apply
          </button>
        </div>
        <div className="flex justify-between text-[#444] text-xs mt-1.5 px-0.5">
          <span>1 min</span>
          <span>30 min</span>
        </div>
      </div>
    </div>
  );
}
