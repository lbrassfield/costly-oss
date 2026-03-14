"use client";

import { Badge } from "@/components/ui/badge";
import { Clock } from "lucide-react";

interface DataFreshnessProps {
  fetchedAt?: string;
  cached?: boolean;
  demo?: boolean;
}

export default function DataFreshness({ fetchedAt, cached, demo }: DataFreshnessProps) {
  if (demo) {
    return (
      <Badge variant="secondary" className="text-xs font-normal gap-1">
        <Clock className="h-3 w-3" />
        Demo data
      </Badge>
    );
  }

  if (!fetchedAt) return null;

  const raw = fetchedAt.endsWith("Z") ? fetchedAt : fetchedAt + "Z";
  const time = new Date(raw).toLocaleTimeString();

  return (
    <Badge variant="outline" className="text-xs font-normal gap-1 text-muted-foreground">
      <Clock className="h-3 w-3" />
      {cached ? "Cached" : "Fresh"} &middot; {time}
    </Badge>
  );
}
