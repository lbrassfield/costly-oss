"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import {
  BarChart3,
  DollarSign,
  Layers,
  Zap,
  History,
  HardDrive,
  Warehouse,
  Lightbulb,
  Bell,
  Settings,
  LogOut,
  Shield,
  ArrowRight,
  MessageSquare,
  Globe,
  Link2,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Cloud,
  Database,
  Cpu,
  GitBranch,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useApi } from "@/hooks/use-api";

/* ── Platform sections (collapsible) ── */

interface PlatformSection {
  key: string;
  label: string;
  icon: React.ElementType;
  items: { path: string; label: string; icon: React.ElementType }[];
}

const SNOWFLAKE_SECTION: PlatformSection = {
  key: "snowflake",
  label: "Snowflake",
  icon: Database,
  items: [
    { path: "/dashboard", label: "Dashboard", icon: BarChart3 },
    { path: "/costs", label: "Cost Analysis", icon: DollarSign },
    { path: "/workloads", label: "Workloads", icon: Layers },
    { path: "/queries", label: "Query Performance", icon: Zap },
    { path: "/history", label: "Query History", icon: History },
    { path: "/storage", label: "Storage", icon: HardDrive },
    { path: "/warehouses", label: "Warehouses", icon: Warehouse },
  ],
};

// Future platform sections — show when connected
const AWS_SECTION: PlatformSection = {
  key: "aws",
  label: "AWS",
  icon: Cloud,
  items: [],
};

const DBT_SECTION: PlatformSection = {
  key: "dbt_cloud",
  label: "dbt Cloud",
  icon: GitBranch,
  items: [],
};

const AI_SECTION: PlatformSection = {
  key: "ai",
  label: "AI APIs",
  icon: Cpu,
  items: [],
};

export default function Sidebar() {
  const { user, isDemo, logout, exitDemo } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const { data: connections } = useApi<{ id: string; platform?: string }[]>(
    !isDemo && user ? "/platforms" : null
  );
  const showOnboarding = !isDemo && user && (!connections || connections.length === 0);

  // Track which platform sections are expanded
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["snowflake"]));

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Auto-expand section if current path is inside it
  const isPathInSection = (section: PlatformSection) =>
    section.items.some((item) => pathname === item.path);

  const handleLogout = () => {
    if (isDemo) {
      exitDemo();
      router.push("/");
    } else {
      logout();
      router.push("/");
    }
  };

  // In demo mode, show Snowflake section. For real users, always show Snowflake
  // (since it's the most built-out), and show others based on connections.
  const platformSections: PlatformSection[] = [SNOWFLAKE_SECTION];

  const navLink = (path: string, label: string, Icon: React.ElementType, indent = false) => (
    <Link
      key={path}
      href={path}
      className={cn(
        "flex items-center gap-2.5 py-1.5 rounded-md text-sm transition-colors",
        indent ? "px-3 pl-9" : "px-3",
        pathname === path
          ? "bg-sky-600/80 text-white font-semibold"
          : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </Link>
  );

  return (
    <aside className="fixed left-0 top-0 w-[220px] h-screen bg-gradient-to-b from-[#0B1929] to-[#0A1525] flex flex-col py-5 px-3 z-50 border-r border-white/5 overflow-y-auto">
      {/* Logo */}
      <div className="mb-5 px-1">
        <div className="flex items-center gap-2 text-white font-extrabold text-lg tracking-tight">
          <DollarSign className="h-5 w-5 text-sky-400" />
          costly
        </div>
        {isDemo ? (
          <div className="mt-3 p-2.5 bg-sky-500/10 border border-sky-500/20 rounded-lg">
            <div className="text-xs font-semibold text-sky-400 uppercase tracking-wider mb-1">
              Live Demo
            </div>
            <div className="text-[0.65rem] text-slate-400 leading-tight">
              Viewing sample data
            </div>
          </div>
        ) : user ? (
          <div className="mt-3 p-2.5 bg-white/5 rounded-lg">
            <div className="text-sm font-semibold text-slate-200 truncate">
              {user.name}
            </div>
            <div className="text-xs text-slate-500 truncate mt-0.5">
              {user.email}
            </div>
          </div>
        ) : null}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5">
        {showOnboarding && (
          <>
            <Link
              href="/onboarding"
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors mb-1",
                pathname === "/onboarding"
                  ? "bg-sky-600/80 text-white font-semibold"
                  : "text-sky-400 hover:text-sky-300 hover:bg-sky-500/10 bg-sky-500/5 border border-sky-500/20"
              )}
            >
              <Sparkles className="h-4 w-4 shrink-0" />
              Get Started
            </Link>
            <Separator className="bg-white/5 my-2" />
          </>
        )}

        {/* ── Overview Section ── */}
        <div className="text-[0.65rem] font-bold text-slate-600 uppercase tracking-wider px-3 mb-2">
          Overview
        </div>
        {navLink("/overview", "All Platforms", Globe)}
        {navLink("/recommendations", "Recommendations", Lightbulb)}
        {navLink("/alerts", "Alerts", Bell)}

        <Separator className="bg-white/5 my-3" />

        {/* ── Platform Sections (collapsible) ── */}
        <div className="text-[0.65rem] font-bold text-slate-600 uppercase tracking-wider px-3 mb-2">
          Platforms
        </div>

        {platformSections.map((section) => {
          const isExpanded = expandedSections.has(section.key) || isPathInSection(section);
          const hasItems = section.items.length > 0;

          return (
            <div key={section.key} className="mb-1">
              {/* Section header */}
              <button
                onClick={() => hasItems && toggleSection(section.key)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors",
                  isPathInSection(section)
                    ? "text-sky-300"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                )}
              >
                <section.icon className="h-4 w-4 shrink-0" />
                <span className="flex-1 text-left font-semibold">{section.label}</span>
                {hasItems && (
                  isExpanded
                    ? <ChevronDown className="h-3.5 w-3.5 text-slate-600" />
                    : <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
                )}
                {!hasItems && (
                  <span className="text-[0.6rem] text-slate-600 font-normal">Soon</span>
                )}
              </button>

              {/* Section items */}
              {isExpanded && hasItems && (
                <div className="mt-0.5 space-y-0.5">
                  {section.items.map(({ path, label, icon: Icon }) =>
                    navLink(path, label, Icon, true)
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Show placeholder sections for other platforms */}
        {[AWS_SECTION, DBT_SECTION, AI_SECTION].map((section) => (
          <div key={section.key} className="mb-1">
            <div className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm text-slate-500">
              <section.icon className="h-4 w-4 shrink-0" />
              <span className="flex-1 text-left font-semibold">{section.label}</span>
              <span className="text-[0.6rem] text-slate-600 font-normal">Soon</span>
            </div>
          </div>
        ))}

        <Separator className="bg-white/5 my-3" />

        {/* ── Tools Section ── */}
        <div className="text-[0.65rem] font-bold text-slate-600 uppercase tracking-wider px-3 mb-2">
          Tools
        </div>
        {navLink("/chat", "Costly AI", MessageSquare)}
        {navLink("/platforms", "Connections", Link2)}
      </nav>

      {/* Bottom */}
      <Separator className="bg-white/5 my-3" />

      {isDemo ? (
        <>
          <Link
            href="/login"
            onClick={() => exitDemo()}
            className="flex items-center gap-2 px-3 py-2.5 bg-sky-600 rounded-lg text-white text-sm font-semibold hover:bg-sky-700 transition mb-2"
          >
            <ArrowRight className="h-4 w-4" />
            Sign Up Free
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="justify-start gap-2.5 px-3 text-slate-500 hover:text-slate-300 hover:bg-transparent"
          >
            <LogOut className="h-4 w-4" />
            Exit Demo
          </Button>
        </>
      ) : (
        <>
          {user?.role === "admin" && (
            <Link
              href="/admin"
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
                pathname === "/admin"
                  ? "bg-sky-600/80 text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              )}
            >
              <Shield className="h-4 w-4" />
              Admin
            </Link>
          )}
          <Link
            href="/settings"
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors",
              pathname === "/settings"
                ? "bg-sky-600/80 text-white font-semibold"
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
            )}
          >
            <Settings className="h-4 w-4" />
            Settings
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="justify-start gap-2.5 px-3 text-slate-500 hover:text-red-400 hover:bg-transparent"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </>
      )}
    </aside>
  );
}
