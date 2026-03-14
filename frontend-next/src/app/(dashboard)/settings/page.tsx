"use client";

import { useState, useCallback } from "react";
import { useApi } from "@/hooks/use-api";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Trash2, TestTube, CheckCircle, XCircle, Loader2 } from "lucide-react";

interface Connection {
  connection_id: string; connection_name: string; account: string; username: string;
  warehouse: string; role: string; is_active: boolean; test_status?: string;
  last_tested_at?: string;
}

interface PermCheck {
  checks: Record<string, { status: string; rows?: number | string; error?: string }>;
  connection: string;
  role: string;
}

export default function SettingsPage() {
  const { data: connections, loading, refetch } = useApi<Connection[]>("/connections");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [permsData, setPermsData] = useState<PermCheck | null>(null);
  const [checkingPerms, setCheckingPerms] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [account, setAccount] = useState("");
  const [username, setUsername] = useState("");
  const [warehouse, setWarehouse] = useState("COMPUTE_WH");
  const [role, setRole] = useState("ACCOUNTADMIN");
  const [privateKey, setPrivateKey] = useState("");
  const [passphrase, setPassphrase] = useState("");

  const handleCreate = useCallback(async () => {
    setSaving(true);
    try {
      await api.post("/connections", {
        connection_name: name,
        account,
        username,
        auth_type: "keypair",
        private_key: privateKey,
        private_key_passphrase: passphrase || undefined,
        warehouse,
        role,
        database: "SNOWFLAKE",
        schema_name: "ACCOUNT_USAGE",
      });
      setShowForm(false);
      setName(""); setAccount(""); setUsername(""); setPrivateKey(""); setPassphrase("");
      refetch();
    } catch {
      // error
    } finally {
      setSaving(false);
    }
  }, [name, account, username, warehouse, role, privateKey, passphrase, refetch]);

  const handleTest = useCallback(async (connId: string) => {
    setTesting(connId);
    try {
      await api.post(`/connections/${connId}/test`);
      refetch();
    } catch {
      // error
    } finally {
      setTesting(null);
    }
  }, [refetch]);

  const handleDelete = useCallback(async (connId: string) => {
    await api.delete(`/connections/${connId}`);
    refetch();
  }, [refetch]);

  const handleActivate = useCallback(async (connId: string) => {
    await api.post(`/connections/${connId}/activate`);
    refetch();
  }, [refetch]);

  const checkPermissions = useCallback(async () => {
    setCheckingPerms(true);
    try {
      const res = (await api.get("/debug/permissions")) as PermCheck;
      setPermsData(res);
    } catch {
      // error
    } finally {
      setCheckingPerms(false);
    }
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <Button onClick={() => setShowForm(!showForm)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Connection
        </Button>
      </div>

      {showForm && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">New Connection</CardTitle>
            <CardDescription>Key-pair authentication only. See the Setup Guide for instructions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div><Label>Connection Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Production" /></div>
              <div><Label>Account Identifier</Label><Input value={account} onChange={(e) => setAccount(e.target.value)} placeholder="org-account" /></div>
              <div><Label>Username</Label><Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="COSTLY_USER" /></div>
              <div><Label>Warehouse</Label><Input value={warehouse} onChange={(e) => setWarehouse(e.target.value)} /></div>
              <div><Label>Role</Label><Input value={role} onChange={(e) => setRole(e.target.value)} /></div>
            </div>
            <div><Label>Private Key (PEM)</Label><Textarea rows={6} value={privateKey} onChange={(e) => setPrivateKey(e.target.value)} placeholder="-----BEGIN ENCRYPTED PRIVATE KEY-----" className="font-mono text-xs" /></div>
            <div><Label>Passphrase (optional)</Label><Input type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} /></div>
            <div className="flex gap-2">
              <Button onClick={handleCreate} disabled={saving || !name || !account || !username || !privateKey}>
                {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Save Connection
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Skeleton className="h-40 rounded-lg" />
      ) : (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Connections</CardTitle>
          </CardHeader>
          <CardContent>
            {connections && connections.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead>Warehouse</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {connections.map((c) => (
                    <TableRow key={c.connection_id}>
                      <TableCell className="font-medium">
                        {c.connection_name}
                        {c.is_active && <Badge className="ml-2 text-xs">Active</Badge>}
                      </TableCell>
                      <TableCell>{c.account}</TableCell>
                      <TableCell>{c.warehouse}</TableCell>
                      <TableCell>{c.role}</TableCell>
                      <TableCell>
                        {c.test_status === "success" ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : c.test_status === "failed" ? (
                          <XCircle className="h-4 w-4 text-red-500" />
                        ) : (
                          <span className="text-xs text-muted-foreground">Untested</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleTest(c.connection_id)} disabled={testing === c.connection_id}>
                            {testing === c.connection_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube className="h-4 w-4" />}
                          </Button>
                          {!c.is_active && (
                            <Button variant="ghost" size="sm" onClick={() => handleActivate(c.connection_id)}>Activate</Button>
                          )}
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-400" onClick={() => handleDelete(c.connection_id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No connections configured.</p>
                <p className="text-sm mt-1">Add a platform connection to start analyzing your costs.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Permissions Checker */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Permissions Checker</CardTitle>
          <CardDescription>Test which ACCOUNT_USAGE views your connection can access.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={checkPermissions} disabled={checkingPerms}>
            {checkingPerms ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <TestTube className="h-4 w-4 mr-2" />}
            Check Permissions
          </Button>
          {permsData && (
            <div className="mt-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>View</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(permsData.checks).map(([name, check]) => (
                    <TableRow key={name}>
                      <TableCell className="font-mono text-sm">{name}</TableCell>
                      <TableCell>
                        <Badge variant={check.status === "ok" ? "default" : "destructive"} className="text-xs">
                          {check.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {check.status === "ok" ? `${check.rows} rows` : check.error}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
