"use client";

import { useDateRange } from "@/providers/date-range-provider";
import { useApi } from "@/hooks/use-api";
import DateRangePicker from "@/components/date-range-picker";
import DemoBanner from "@/components/demo-banner";
import DataFreshness from "@/components/data-freshness";
import StatCard from "@/components/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DollarSign, CreditCard, Warehouse, Zap, AlertTriangle, HardDrive } from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/format";
import { COLORS } from "@/lib/constants";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

interface DashboardData {
  total_cost: number;
  total_credits: number;
  active_warehouses: number;
  query_count: number;
  failed_queries: number;
  storage_gb: number;
  cost_trend: Array<{
    date: string;
    cost: number;
    compute_cost: number;
    cloud_services_cost: number;
    rolling_avg?: number;
  }>;
  top_warehouses: Array<{ name: string; credits: number; cost: number }>;
  top_users: Array<{ user: string; cost: number; queries: number }>;
  anomalies: Array<{ date: string; cost: number; label: string }>;
  fetched_at?: string;
  cached?: boolean;
  demo?: boolean;
}

export default function DashboardPage() {
  const { days, refreshTrigger } = useDateRange();
  const { data, loading } = useApi<DashboardData>(
    `/dashboard?days=${days}&refresh=${refreshTrigger > 0}`,
    [days, refreshTrigger]
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          {data && <DataFreshness fetchedAt={data.fetched_at} cached={data.cached} demo={data.demo} />}
        </div>
        <DateRangePicker />
      </div>

      <DemoBanner />

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : data ? (
        <>
          {/* Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatCard title="Total Cost" value={formatCurrency(data.total_cost)} icon={DollarSign} description={`${days}d period`} />
            <StatCard title="Credits" value={formatNumber(data.total_credits)} icon={CreditCard} />
            <StatCard title="Warehouses" value={data.active_warehouses} icon={Warehouse} />
            <StatCard title="Queries" value={formatNumber(data.query_count)} icon={Zap} />
            <StatCard title="Failed" value={formatNumber(data.failed_queries)} icon={AlertTriangle} />
            <StatCard title="Storage" value={`${data.storage_gb >= 1000 ? (data.storage_gb / 1000).toFixed(1) + " TB" : data.storage_gb.toFixed(1) + " GB"}`} icon={HardDrive} />
          </div>

          {/* Charts */}
          <div className="grid lg:grid-cols-3 gap-6 mb-8">
            {/* Cost Trend */}
            <Card className="lg:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Cost Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.cost_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                      <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                      <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                      <Area type="monotone" dataKey="compute_cost" stackId="1" fill={COLORS.primary} stroke={COLORS.primary} fillOpacity={0.6} name="Compute" />
                      <Area type="monotone" dataKey="cloud_services_cost" stackId="1" fill={COLORS.chart[4]} stroke={COLORS.chart[4]} fillOpacity={0.4} name="Cloud Services" />
                      {data.anomalies.map((a) => (
                        <ReferenceLine key={a.date} x={a.date} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "!", fill: "#ef4444", fontSize: 12 }} />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Top Warehouses */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Top Warehouses</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.top_warehouses} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
                      <Tooltip formatter={(v) => `${Number(v).toFixed(1)} credits`} />
                      <Bar dataKey="credits" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Anomalies + Top Users */}
          <div className="grid lg:grid-cols-2 gap-6">
            {data.anomalies.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                    Cost Anomalies
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {data.anomalies.map((a) => (
                      <div key={a.date} className="p-3 bg-red-50 rounded-lg border border-red-100">
                        <div className="font-medium text-sm text-red-800">{a.label}</div>
                        <div className="text-xs text-red-600 mt-1">
                          {a.date} &middot; {formatCurrency(a.cost)}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Top Users by Cost</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.top_users.map((u, i) => (
                    <div key={u.user} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-medium text-muted-foreground w-5">{i + 1}</span>
                        <span className="text-sm font-medium">{u.user}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold">{formatCurrency(u.cost)}</div>
                        <div className="text-xs text-muted-foreground">{formatNumber(u.queries)} queries</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
