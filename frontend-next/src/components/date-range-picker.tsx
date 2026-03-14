"use client";

import { useDateRange } from "@/providers/date-range-provider";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { DATE_OPTIONS } from "@/lib/constants";

export default function DateRangePicker() {
  const { days, setDays, triggerRefresh } = useDateRange();

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
        {DATE_OPTIONS.map(({ label, value }) => (
          <button
            key={value}
            onClick={() => setDays(value)}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-semibold transition-all",
              days === value
                ? "bg-white text-indigo-500 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            )}
          >
            {label}
          </button>
        ))}
      </div>
      <Button
        variant="outline"
        size="icon"
        className="h-8 w-8"
        onClick={triggerRefresh}
        title="Refresh data"
      >
        <RefreshCw className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
