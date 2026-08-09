import { expect, test } from "@playwright/test";

test("research flow reaches a sourced report", async ({ page }) => {
  await page.route("**/*", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith("/api/")) return route.continue();
    if (path === "/api/task") return route.fulfill({ json: { status: "waiting_confirmation", thread_id: "test-e2e" } });
    if (path.endsWith("/confirm")) return route.fulfill({ json: { status: "running", thread_id: "test-e2e" } });
    return route.fulfill({ json: { thread_id: "test-e2e", state: "running", sequence: 1, result: null, error: null, events: [] } });
  });
  await page.goto("/");
  await page.getByLabel("研究问题").fill("比较 Agent 平台并标注来源");
  await page.getByLabel("提交研究").click();
  await expect(page.getByText("建议执行计划")).toBeVisible();
  await page.getByText("确认并开始").click();
  await expect(page.getByText("研究正在进行")).toBeVisible();
  await expect(page.getByText("演示来源").first()).toBeVisible();
  await page.getByText("查看模拟报告").click();
  await expect(page.getByText("优先选择可观察、可接管的工作流")).toBeVisible();
  for (const [width, height] of [[1024, 768], [1440, 900], [1920, 1080]] as const) {
    await page.setViewportSize({ width, height });
    await page.screenshot({ path: `../docs/interview/assets/report-${width}x${height}.png`, fullPage: true });
  }
});
