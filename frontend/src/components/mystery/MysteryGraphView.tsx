"use client";

import { useEffect, useRef, useState } from "react";
import type { GraphData } from "@/types";
import { ZoomIn, ZoomOut, RefreshCw } from "lucide-react";

const MYSTERY_NODE_COLORS: Record<string, string> = {
  MysteryArticle: "#f87171",
  MysteryCluster: "#f59e0b",
  Entity: "#6366f1",
  Topic: "#34d399",
};

const MYSTERY_LINK_COLORS: Record<string, string> = {
  SAME_ENTITY: "#f59e0b",
  SAME_PATTERN: "#f87171",
  POSSIBLE_LINK: "#6366f144",
  BELONGS_TO_CLUSTER: "#555",
};

interface Props {
  data: GraphData;
}

export function MysteryGraphView({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (!data.nodes.length || !svgRef.current) return;

    let cancelled = false;

    (async () => {
      const d3 = await import("d3");
      if (cancelled || !svgRef.current) return;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();

      const W = svgRef.current.clientWidth || 900;
      const H = svgRef.current.clientHeight || 600;

      const zoomBehavior = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.05, 5])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
          setZoom(Math.round(event.transform.k * 100) / 100);
        });
      svg.call(zoomBehavior);

      const g = svg.append("g");

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

      // Arrow markers
      const defs = svg.append("defs");
      ["SAME_ENTITY", "SAME_PATTERN", "POSSIBLE_LINK"].forEach((rel) => {
        const color = MYSTERY_LINK_COLORS[rel] ?? "#555";
        defs
          .append("marker")
          .attr("id", `arrow-${rel}`)
          .attr("viewBox", "0 -4 8 8")
          .attr("refX", 14)
          .attr("markerWidth", 6)
          .attr("markerHeight", 6)
          .attr("orient", "auto")
          .append("path")
          .attr("d", "M0,-4L8,0L0,4")
          .attr("fill", color);
      });

      const sim = d3
        .forceSimulation(nodes as d3.SimulationNodeDatum[])
        .force(
          "link",
          d3.forceLink(links).id((d: d3.SimulationNodeDatum) => (d as typeof nodes[0]).id).distance(100).strength(0.4)
        )
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(W / 2, H / 2))
        .force("collision", d3.forceCollide(22));

      const linkEls = g
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", (d) => MYSTERY_LINK_COLORS[d.type] ?? "#333")
        .attr("stroke-width", (d) => (d.type === "SAME_PATTERN" ? 2 : 1))
        .attr("stroke-dasharray", (d) => (d.type === "POSSIBLE_LINK" ? "4,3" : "none"))
        .attr("marker-end", (d) => `url(#arrow-${d.type})`);

      const nodeEls = g
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", (d) => (d.label === "MysteryCluster" ? 12 : d.label === "MysteryArticle" ? 7 : 6))
        .attr("fill", (d) => MYSTERY_NODE_COLORS[d.label] ?? "#888")
        .attr("stroke", (d) => (d.id === selected ? "#fff" : "#0B0B0B"))
        .attr("stroke-width", (d) => (d.id === selected ? 2 : 1.5))
        .attr("cursor", "pointer")
        .on("click", (_, d) => setSelected(d.id === selected ? null : d.id))
        .call(
          d3.drag<SVGCircleElement, (typeof nodes)[0]>()
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

      const labelEls = g
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("text-anchor", "middle")
        .attr("dy", 20)
        .attr("font-size", 9)
        .attr("fill", "#666")
        .text((d) => {
          const p = d.properties as Record<string, string>;
          return (p.title ?? p.name ?? "").slice(0, 20);
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

    return () => { cancelled = true; };
  }, [data, selected]);

  return (
    <div className="relative w-full h-full bg-[#0B0B0B] rounded-xl border border-[#1E1E1E] overflow-hidden">
      {/* Legend */}
      <div className="absolute top-4 left-4 z-10 bg-[#111]/90 border border-[#2A2A2A] rounded-lg p-3 space-y-2">
        <p className="text-[#555] text-xs font-medium uppercase tracking-wide mb-1">Nodes</p>
        {Object.entries(MYSTERY_NODE_COLORS).map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span className="text-[#666] text-xs">{label}</span>
          </div>
        ))}
        <p className="text-[#555] text-xs font-medium uppercase tracking-wide mt-3 mb-1">Edges</p>
        {Object.entries(MYSTERY_LINK_COLORS)
          .filter(([k]) => k !== "BELONGS_TO_CLUSTER")
          .map(([rel, color]) => (
            <div key={rel} className="flex items-center gap-2">
              <div className="w-4 h-0.5" style={{ background: color.replace("44", "") }} />
              <span className="text-[#555] text-xs">{rel}</span>
            </div>
          ))}
      </div>

      {/* Zoom */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-1">
        <div className="text-center text-[#444] text-xs py-0.5">{Math.round(zoom * 100)}%</div>
      </div>

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <RefreshCw className="w-5 h-5 text-[#333] animate-spin" />
        </div>
      )}

      <svg ref={svgRef} className="w-full h-full" />

      <div className="absolute bottom-4 left-4 text-[#333] text-xs">
        {data.nodes.length} nodes · {data.links.length} links
      </div>
    </div>
  );
}
