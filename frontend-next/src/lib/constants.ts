export const COLORS = {
  primary: "#0C4A6E",
  primaryLight: "#38BDF8",
  accent: "#0EA5E9",
  success: "#059669",
  warning: "#D97706",
  danger: "#DC2626",
  chart: ["#0EA5E9", "#6366F1", "#14B8A6", "#F59E0B", "#8B5CF6", "#EC4899", "#10B981", "#F97316"],
} as const;

export const DATE_OPTIONS = [
  { label: "7D", value: 7 },
  { label: "14D", value: 14 },
  { label: "30D", value: 30 },
  { label: "90D", value: 90 },
] as const;
