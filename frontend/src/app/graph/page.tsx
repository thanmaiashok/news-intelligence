"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { GraphView } from "@/components/graph/GraphView";
import { usePolling } from "@/hooks/useNewsData";
import { getGraphData } from "@/lib/api";
import type { GraphData } from "@/types";
import { Search, RefreshCw } from "lucide-react";

export default function GraphPage() {
  const [center, setCenter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState<{ label: string; name?: string } | null>(null);

  const { data, loading, refetch } = usePolling<GraphData>(
    () => getGraphData(center, 150),
    60000,
    [center]
  );

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setCenter(search.trim() || undefined);
  }

  return (
    <div className="flex flex-col h-screen">
      <Header title="Graph View" subtitle="Neo4j knowledge graph — entities, topics, sources" />

      <div className="flex items-center gap-3 px-6 py-3 border-b border-[#1E1E1E]">
        <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#555]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Center on entity or topic..."
              className="w-full bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg pl-8 pr-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-[#444]"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-white text-black text-sm rounded-lg hover:bg-[#ddd] transition-colors font-medium"
          >
            Go
          </button>
          {center && (
            <button
              type="button"
              onClick={() => { setCenter(undefined); setSearch(""); }}
              className="text-[#555] text-sm hover:text-white transition-colors"
            >
              Reset
            </button>
          )}
        </form>

        <button
          onClick={refetch}
          className="ml-auto text-[#555] hover:text-white p-2 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>

        {selectedNode && (
          <div className="text-sm text-[#888]">
            Selected: <span className="text-white">{selectedNode.name ?? selectedNode.label}</span>
            <span className="text-[#444] ml-1">({selectedNode.label})</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-hidden p-6">
        {loading || !data ? (
          <div className="w-full h-full bg-[#111] border border-[#1E1E1E] rounded-xl flex items-center justify-center">
            <RefreshCw className="w-5 h-5 text-[#444] animate-spin" />
          </div>
        ) : (
          <GraphView
            data={data}
            onNodeClick={setSelectedNode}
          />
        )}
      </div>
    </div>
  );
}
