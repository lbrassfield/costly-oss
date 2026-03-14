"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { DateRangeProvider } from "@/providers/date-range-provider";
import Sidebar from "@/components/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isDemo } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!user && !isDemo) {
      router.push("/login");
    }
  }, [user, isDemo, router]);

  if (!user && !isDemo) return null;

  return (
    <DateRangeProvider>
      <div className="flex min-h-screen bg-slate-50">
        <Sidebar />
        <main className="ml-[220px] flex-1 p-8 max-w-[calc(100vw-220px)] overflow-x-hidden">
          {children}
        </main>
      </div>
    </DateRangeProvider>
  );
}
