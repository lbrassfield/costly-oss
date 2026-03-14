"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertTriangle, X, ArrowRight, Sparkles } from "lucide-react";
import api from "@/lib/api";

export default function DemoBanner() {
  const { isDemo, exitDemo } = useAuth();
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (isDemo) {
      setShow(true);
      return;
    }
    if (sessionStorage.getItem("demoBannerDismissed")) return;
    api
      .get("/connections/status")
      .then((data: unknown) => {
        const d = data as { has_connection: boolean };
        if (!d.has_connection) setShow(true);
      })
      .catch(() => setShow(true));
  }, [isDemo]);

  if (!show || dismissed) return null;

  // Public demo mode — prominent CTA banner
  if (isDemo) {
    return (
      <div className="mb-6 rounded-xl border border-sky-200 bg-gradient-to-r from-sky-50 to-cyan-50 p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-sky-100 flex items-center justify-center shrink-0">
              <Sparkles className="h-5 w-5 text-sky-600" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900">
                You&apos;re viewing a live demo with sample data
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Sign up free to connect your data platforms and see real cost insights in under 5 minutes.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              onClick={() => {
                exitDemo();
                router.push("/login");
              }}
              className="bg-sky-600 hover:bg-sky-700 text-white gap-1"
            >
              Sign Up Free
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-slate-400 hover:text-slate-600"
              onClick={() => setDismissed(true)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Authenticated user without any platform connection
  return (
    <Alert className="mb-6 border-amber-300 bg-amber-50">
      <AlertTriangle className="h-4 w-4 text-amber-600" />
      <AlertDescription className="flex items-center justify-between w-full">
        <span className="text-amber-800 text-sm">
          <strong>Demo Mode</strong> &mdash; You&apos;re viewing sample data.
          Connect your data platforms in Settings to see real data.{" "}
          <Button
            variant="link"
            className="text-amber-800 underline p-0 h-auto font-semibold"
            onClick={() => router.push("/settings")}
          >
            Go to Settings
          </Button>
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-amber-600 hover:text-amber-800 shrink-0"
          onClick={() => {
            sessionStorage.setItem("demoBannerDismissed", "1");
            setShow(false);
          }}
        >
          <X className="h-4 w-4" />
        </Button>
      </AlertDescription>
    </Alert>
  );
}
