"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface DateRangeContextType {
  days: number;
  setDays: (d: number) => void;
  refreshTrigger: number;
  triggerRefresh: () => void;
}

const DateRangeContext = createContext<DateRangeContextType>({
  days: 30,
  setDays: () => {},
  refreshTrigger: 0,
  triggerRefresh: () => {},
});

export function DateRangeProvider({ children }: { children: ReactNode }) {
  const [days, setDays] = useState(30);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const triggerRefresh = useCallback(() => setRefreshTrigger((t) => t + 1), []);

  return (
    <DateRangeContext.Provider value={{ days, setDays, refreshTrigger, triggerRefresh }}>
      {children}
    </DateRangeContext.Provider>
  );
}

export function useDateRange() {
  return useContext(DateRangeContext);
}
