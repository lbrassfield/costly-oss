import { test, expect } from "@playwright/test";

test.describe("Demo Dashboard", () => {
  // Demo endpoints don't require auth, so we can test the API directly

  test("demo dashboard API returns data", async ({ request }) => {
    const resp = await request.get("/api/demo/dashboard?days=7");
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.demo).toBe(true);
    expect(data.daily_costs).toBeDefined();
  });

  test("demo platform costs API returns unified data", async ({ request }) => {
    const resp = await request.get("/api/demo/platforms/costs?days=7");
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.total_cost).toBeGreaterThan(0);
    expect(data.by_platform.length).toBeGreaterThan(0);
    expect(data.by_category.length).toBeGreaterThan(0);
    expect(data.daily_trend.length).toBe(7);
  });

  test("demo platform costs has no Claude references", async ({ request }) => {
    const resp = await request.get("/api/demo/platforms/costs?days=30");
    const text = JSON.stringify(await resp.json()).toLowerCase();
    expect(text).not.toContain("claude");
  });

  test("demo supported platforms lists all connectors", async ({ request }) => {
    const resp = await request.get("/api/demo/platforms/supported");
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.platforms.length).toBeGreaterThanOrEqual(15);
    expect(data.platforms).toContain("aws");
    expect(data.platforms).toContain("openai");
    expect(data.platforms).toContain("fivetran");
    expect(data.platforms).toContain("databricks");
    expect(data.platforms).toContain("github");
  });

  test("demo connections returns platform list", async ({ request }) => {
    const resp = await request.get("/api/demo/platforms");
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.length).toBeGreaterThanOrEqual(3);
    const platforms = data.map((c: { platform: string }) => c.platform);
    expect(platforms).toContain("snowflake");
    expect(platforms).toContain("aws");
  });

  test("demo recommendations returns data", async ({ request }) => {
    const resp = await request.get("/api/demo/recommendations");
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(Array.isArray(data) || data.recommendations).toBeTruthy();
  });
});
