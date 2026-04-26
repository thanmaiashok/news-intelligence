"use client";

import { useEffect, useRef, useState } from "react";
import type { GraphData } from "@/types";
import { ZoomIn, ZoomOut, RefreshCw } from "lucide-react";

// D3 force graph rendered on canvas for performance
interface Props {
  data: GraphData;
  onNodeClick?: (node: { label: string; name?: string }) => void;
}

const NODE_COLORS: Record<string, string> = {
  Article: "#6366f1",
  Source: "#f59e0b",
  Topic: "#34d399",
  Entity: "#f87171",
  Node: "#888",
};

const LINK_COLORS: Record<string, string> = {
  FROM_SOURCE: "#555",
  TAGGED_AS: "#34d39944",
  MENTIONS: "#f8717144",
  RELATES_TO: "#f59e0b44",
  TRENDING_WITH: "#6366f144",
};

export function GraphView({ data, onNodeClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<unknown>(null);
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!data.nodes.length || !svgRef.current) return;

    let cancelled = false;

    (async () => {
      const d3 = await import("d3");
      if (cancelled || !svgRef.current) return;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();

      const W = svgRef.current.clientWidth || 800;
      const H = svgRef.current.clientHeight || 600;

      // Zoom behavior
      const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
          setZoom(Math.round(event.transform.k * 100) / 100);
        });
      svg.call(zoomBehavior);

      const g = svg.append("g");

      // Build node/link copies for simulation
      const nodes = data.nodes.map((n) => ({ ...n, x: W / 2, y: H / 2 }));
      const nodeById: Record<string, (typeof nodes)[0]> = {};
      nodes.forEach((n) => (nodeById[n.id] = n));

      const links = data.links
        .map((l) => ({
          ...l,
          source: nodeById[l.source],
          target: nodeById[l.target],
        }))
        .filter((l) => l.source && l.target);

      // Simulation
      const sim = d3
        .forceSimulation(nodes as d3.SimulationNodeDatum[])
        .force("link", d3.forceLink(links).id((d: d3.SimulationNodeDatum) => (d as typeof nodes[0]).id).distance(80).strength(0.5))
        .force("charge", d3.forceManyBody().strength(-150))
        .force("center", d3.forceCenter(W / 2, H / 2))
        .force("collision", d3.forceCollide(20));

      simRef.current = sim;

      // Links
      const linkEls = g
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", (d) => LINK_COLORS[d.type] ?? "#333")
        .attr("stroke-width", 1);

      // Link labels (only for short graphs)
      if (links.length < 80) {
        g.selectAll(".link-label")
          .data(links)
          .join("text")
          .attr("class", "link-label")
          .attr("text-anchor", "middle")
          .attr("font-size", 8)
          .attr("fill", "#444")
          .text((d) => d.type);
      }

      // Nodes
      const nodeEls = g
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", (d) => (d.label === "Article" ? 6 : d.label === "Source" ? 9 : 7))
        .attr("fill", (d) => NODE_COLORS[d.label] ?? "#888")
        .attr("stroke", "#0B0B0B")
        .attr("stroke-width", 1.5)
        .attr("cursor", "pointer")
        .on("click", (_, d) => onNodeClick?.({ label: d.label, name: (d.properties as Record<string, string>).name }))
        .call(
          d3
            .drag<SVGCircleElement, (typeof nodes)[0]>()
            .on("start", (event, d_) => {
              if (!event.active) sim.alphaTarget(0.3).restart();
              (d_ as d3.SimulationNodeDatum).fx = (d_ as d3.SimulationNodeDatum).x;
              (d_ as d3.SimulationNodeDatum).fy = (d_ as d3.SimulationNodeDatum).y;
            })
            .on("drag", (event, d_) => {
              (d_ as d3.SimulationNodeDatum).fx = event.x;
              (d_ as d3.SimulationNodeDatum).fy = event.y;
            })
            .on("end", (event, d_) => {
              if (!event.active) sim.alphaTarget(0);
              (d_ as d3.SimulationNodeDatum).fx = null;
              (d_ as d3.SimulationNodeDatum).fy = null;
            }) as d3.DragBehavior<SVGCircleElement, unknown, unknown>
        );

      // Labels
      const labelEls = g
        .selectAll("text.label")
        .data(nodes)
        .join("text")
        .attr("class", "label")
        .attr("text-anchor", "middle")
        .attr("dy", 18)
        .attr("font-size", 9)
        .attr("fill", "#888")
        .text((d) => {
          const name = (d.properties as Record<string, string>).name ?? (d.properties as Record<string, string>).title ?? "";
          return name.slice(0, 20);
        });

      sim.on("tick", () => {
        linkEls
          .attr("x1", (d) => (d.source as d3.SimulationNodeDatum).x ?? 0)
          .attr("y1", (d) => (d.source as d3.SimulationNodeDatum).y ?? 0)
          .attr("x2", (d) => (d.target as d3.SimulationNodeDatum).x ?? 0)
          .attr("y2", (d) => (d.target as d3.SimulationNodeDatum).y ?? 0);
        nodeEls
          .attr("cx", (d) => (d as d3.SimulationNodeDatum).x ?? 0)
          .attr("cy", (d) => (d as d3.SimulationNodeDatum).y ?? 0);
        labelEls
          .attr("x", (d) => (d as d3.SimulationNodeDatum).x ?? 0)
          .attr("y", (d) => (d as d3.SimulationNodeDatum).y ?? 0);
      });

      setLoading(false);

      return () => {
        cancelled = true;
        sim.stop();
      };
    })();

    return () => {
      cancelled = true;
    };
  }, [data, onNodeClick]);

  return (
    <div className="relative w-full h-full bg-[#0B0B0B] rounded-xl border border-[#1E1E1E] overflow-hidden">
      {/* Legend */}
      <div className="absolute top-4 left-4 z-10 bg-[#111]/90 border border-[#2A2A2A] rounded-lg p-3 space-y-1.5">
        {Object.entries(NODE_COLORS).filter(([k]) => k !== "Node").map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span className="text-[#888] text-xs">{label}</span>
          </div>
        ))}
      </div>

      {/* Zoom controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-1">
        <button
          className="w-8 h-8 bg-[#111] border border-[#2A2A2A] rounded-lg flex items-center justify-center text-[#888] hover:text-white"
          onClick={() => {
            const el = svgRef.current;
            if (el) {
              import("d3").then((d3) =>
                d3.select(el).transition().call(
                  d3.zoom<SVGSVGElement, unknown>().scaleBy as never,
                  1.3
                )
              );
            }
          }}
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          className="w-8 h-8 bg-[#111] border border-[#2A2A2A] rounded-lg flex items-center justify-center text-[#888] hover:text-white"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <div className="text-center text-[#444] text-xs py-0.5">{Math.round(zoom * 100)}%</div>
      </div>

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <RefreshCw className="w-5 h-5 text-[#444] animate-spin" />
        </div>
      )}

      <svg ref={svgRef} className="w-full h-full" />

      {/* Stats bar */}
      <div className="absolute bottom-4 left-4 text-[#444] text-xs">
        {data.nodes.length} nodes · {data.links.length} relationships
      </div>
    </div>
  );
}
