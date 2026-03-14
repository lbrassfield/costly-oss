"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

function StrengthBar({ password }: { password: string }) {
  const checks = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];
  const score = checks.filter(Boolean).length;
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = ["bg-slate-200", "bg-red-500", "bg-amber-500", "bg-emerald-500", "bg-emerald-500"];
  const textColors = ["", "text-red-500", "text-amber-500", "text-emerald-500", "text-emerald-500"];

  return (
    <div className="mb-4 -mt-1">
      <div className="flex gap-1 mb-1">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`flex-1 h-[3px] rounded-sm transition-colors ${
              i <= score ? colors[score] : "bg-slate-200"
            }`}
          />
        ))}
      </div>
      {score > 0 && (
        <div className={`text-[0.72rem] font-semibold ${textColors[score]}`}>{labels[score]}</div>
      )}
    </div>
  );
}

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
      <Card className="w-full max-w-[400px] shadow-lg">
        <CardContent className="p-8">
          <div className="text-center mb-7">
            <div className="text-3xl mb-1">&#10052;&#65039;</div>
            <span className="text-lg font-extrabold text-slate-900 tracking-tight">costly</span>
          </div>
          {children}
        </CardContent>
      </Card>
    </div>
  );
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!token) {
    return (
      <PageWrapper>
        <div className="text-center">
          <div className="text-4xl mb-4">&#128279;</div>
          <h2 className="text-lg font-bold text-slate-900 mb-2">Invalid reset link</h2>
          <p className="text-sm text-slate-500 mb-6 leading-relaxed">
            This link is missing a reset token. Please request a new one.
          </p>
          <Button asChild>
            <Link href="/login">Back to Sign In</Link>
          </Button>
        </div>
      </PageWrapper>
    );
  }

  if (done) {
    return (
      <PageWrapper>
        <div className="text-center">
          <div className="text-4xl mb-4">&#9989;</div>
          <h2 className="text-lg font-bold text-slate-900 mb-2">Password updated</h2>
          <p className="text-sm text-slate-500 mb-6 leading-relaxed">
            Your password has been reset successfully. You can now sign in with your new password.
          </p>
          <Button asChild>
            <Link href="/login">Sign In</Link>
          </Button>
        </div>
      </PageWrapper>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
    } catch {
      setError("This reset link is invalid or has expired. Please request a new one.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <h2 className="text-lg font-bold text-slate-900 mb-1">Set a new password</h2>
      <p className="text-sm text-slate-500 mb-6 leading-relaxed">
        Choose a strong password of at least 8 characters.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label>New password</Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
            required
            minLength={8}
            autoFocus
            autoComplete="new-password"
          />
        </div>
        <div>
          <Label>Confirm new password</Label>
          <Input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Re-enter password"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>

        {password.length > 0 && <StrengthBar password={password} />}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2 text-red-600 text-sm">
            {error}
          </div>
        )}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          {loading ? "Updating..." : "Set New Password"}
        </Button>
      </form>
      <div className="mt-5 text-center">
        <Link href="/login" className="text-sm text-slate-500 hover:text-slate-700">
          Back to sign in
        </Link>
      </div>
    </PageWrapper>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <PageWrapper>
          <Skeleton className="h-64 rounded-lg" />
        </PageWrapper>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
