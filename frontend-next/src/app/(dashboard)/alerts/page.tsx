"use client";

import { useState, useCallback } from "react";
import { useApi } from "@/hooks/use-api";
import DemoBanner from "@/components/demo-banner";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Trash2, Loader2 } from "lucide-react";

interface AlertItem {
  id: string; name: string; metric: string; threshold: number;
  channel: string; webhook_url?: string; enabled: boolean;
  created_at: string; last_fired_at?: string; last_value?: number;
}

const METRICS = [
  { value: "daily_cost", label: "Daily Cost ($)" },
  { value: "hourly_credits", label: "Hourly Credits" },
  { value: "expensive_query_count", label: "Expensive Queries (>5min)" },
  { value: "failed_query_count", label: "Failed Queries" },
  { value: "storage_gb", label: "Storage (GB)" },
];

export default function AlertsPage() {
  const { data, loading, refetch } = useApi<AlertItem[]>("/alerts");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [metric, setMetric] = useState("daily_cost");
  const [threshold, setThreshold] = useState("");
  const [channel, setChannel] = useState("slack");
  const [webhookUrl, setWebhookUrl] = useState("");

  const handleCreate = useCallback(async () => {
    setSaving(true);
    try {
      await api.post("/alerts", {
        name,
        metric,
        threshold: parseFloat(threshold),
        channel,
        webhook_url: channel === "slack" ? webhookUrl : undefined,
      });
      setDialogOpen(false);
      setName(""); setThreshold(""); setWebhookUrl("");
      refetch();
    } catch {
      // error handling
    } finally {
      setSaving(false);
    }
  }, [name, metric, threshold, channel, webhookUrl, refetch]);

  const toggleAlert = useCallback(async (id: string, enabled: boolean) => {
    await api.patch(`/alerts/${id}`, { enabled });
    refetch();
  }, [refetch]);

  const deleteAlert = useCallback(async (id: string) => {
    await api.delete(`/alerts/${id}`);
    refetch();
  }, [refetch]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Alerts</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Create Alert
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Alert</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <Label>Name</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. High daily cost" />
              </div>
              <div>
                <Label>Metric</Label>
                <Select value={metric} onValueChange={setMetric}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {METRICS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Threshold</Label>
                <Input type="number" value={threshold} onChange={(e) => setThreshold(e.target.value)} placeholder="e.g. 500" />
              </div>
              <div>
                <Label>Channel</Label>
                <Select value={channel} onValueChange={setChannel}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="slack">Slack</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {channel === "slack" && (
                <div>
                  <Label>Slack Webhook URL</Label>
                  <Input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} placeholder="https://hooks.slack.com/..." />
                </div>
              )}
              <Button className="w-full" onClick={handleCreate} disabled={saving || !name || !threshold}>
                {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Create Alert
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      <DemoBanner />

      {loading ? (
        <Skeleton className="h-80 rounded-lg" />
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Your Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            {data && data.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Metric</TableHead>
                    <TableHead>Threshold</TableHead>
                    <TableHead>Channel</TableHead>
                    <TableHead>Last Fired</TableHead>
                    <TableHead>Enabled</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="font-medium">{a.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">{a.metric}</Badge>
                      </TableCell>
                      <TableCell>{a.threshold}</TableCell>
                      <TableCell className="capitalize">{a.channel}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {a.last_fired_at ? new Date(a.last_fired_at).toLocaleDateString() : "Never"}
                      </TableCell>
                      <TableCell>
                        <Switch checked={a.enabled} onCheckedChange={(val) => toggleAlert(a.id, val)} />
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-400 hover:text-red-600" onClick={() => deleteAlert(a.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <p>No alerts configured yet.</p>
                <p className="text-sm mt-1">Create your first alert to get notified when metrics exceed thresholds.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
