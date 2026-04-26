"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  TrendingUp,
  BarChart2,
  Share2,
  Lightbulb,
  Settings,
  Globe2,
  Telescope,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
}

const NAV: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/live-feed", label: "Live Feed", icon: Radio },
  { href: "/trends", label: "Trend Analytics", icon: TrendingUp },
  { href: "/sentiment", label: "Sentiment", icon: BarChart2 },
  { href: "/graph", label: "Graph View", icon: Share2 },
  { href: "/mystery", label: "Mystery Intel", icon: Telescope, badge: "NEW" },
  { href: "/leads", label: "Lead Generation", icon: Lightbulb },
  { href: "/control", label: "System Control", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-[#111111] border-r border-[#2A2A2A] flex flex-col z-40">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[#2A2A2A]">
        <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
          <Globe2 className="w-5 h-5 text-black" />
        </div>
        <div>
          <p className="text-white font-semibold text-sm leading-tight">NewsIntel</p>
          <p className="text-[#555] text-xs">Global Intelligence</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                active
                  ? "bg-white text-black font-medium"
                  : "text-[#888] hover:text-white hover:bg-[#1E1E1E]"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {badge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-400/15 text-violet-400 font-medium">
                  {badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[#2A2A2A]">
        <p className="text-[#444] text-xs">v1.0.0 · Production</p>
      </div>
    </aside>
  );
}
