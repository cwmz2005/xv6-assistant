import { test, expect } from "@playwright/test";
const screenshotRoot = "../tmp/browser/run-" + Date.now();

test("home and lazy-loaded knowledge management", async ({ page }) => {
  const errors: string[] = [];
  const requests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => requests.push(request.url()));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "从一个问题，读懂内核。" }),
  ).toBeVisible();
  await expect(page.getByPlaceholder("提问 xv6")).toBeVisible();
  expect(requests.some((url) => url.includes("/KnowledgePanel-"))).toBeFalsy();
  await page.screenshot({ path: screenshotRoot + "/home.png", fullPage: true });
  await page.getByRole("button", { name: "知识库文档" }).click();
  await expect(page.getByRole("button", { name: "刷新文档" })).toBeVisible();
  await page.getByRole("button", { name: "刷新文档" }).click();
  await expect(
    page.getByText("系统文档", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("10 条/页", { exact: true })).toBeVisible();
  expect(requests.some((url) => url.includes("/KnowledgePanel-"))).toBeTruthy();
  await page.getByRole("button", { name: "导入并索引" }).click();
  await expect(
    page.getByText("导入完成，新增 0 个片段", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page.screenshot({
    path: screenshotRoot + "/knowledge.png",
    fullPage: true,
  });
  await page.locator(".ant-drawer-close").click();
  await page.getByRole("button", { name: "实验评估", exact: true }).click();
  await expect(page.getByRole("button", { name: "运行实验" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("retrieval comparison and persisted experiment history", async ({
  page,
  request,
}) => {
  const recall = await request.post("/api/search", {
    data: { query: "walkaddr PTE_U", strategy: "bm25", top_k: 1 },
  });
  expect(recall.ok()).toBeTruthy();
  const source = (await recall.json()).results[0];
  expect(source.text).toContain("walkaddr");
  expect(source.text).toContain("PTE_U");
  const fixture = await request.post("/api/evaluation/run", {
    data: {
      cases: [
        {
          id: "e2e-history-" + Date.now(),
          question: "walkaddr PTE_U",
          reference_answer: "walkaddr rejects a mapping without PTE_U.",
          relevance: { [source.id]: 3 },
          type: "source_location",
          annotation_status: "complete",
          annotation_method: "E2E wiring fixture; not a benchmark",
        },
      ],
    },
  });
  expect(fixture.ok()).toBeTruthy();
  await page.goto("/");
  await page.getByPlaceholder("提问 xv6").fill("walkaddr PTE_U");
  await page.getByRole("button", { name: "检索调试", exact: true }).click();
  await expect(page.getByRole("tab", { name: "关键词 BM25" })).toBeVisible({
    timeout: 60000,
  });
  await expect(page.getByRole("tab", { name: "向量 Dense" })).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "混合 Hybrid", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "向量 Dense" }).click();
  await expect(page.getByText(/cosine_similarity:/).first()).toBeVisible();
  await page.screenshot({
    path: screenshotRoot + "/retrieval.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.locator(".ant-drawer-close").click();
  await page.getByRole("button", { name: "实验评估", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("combobox")
    .first()
    .press("ArrowDown");
  await page
    .locator(".ant-select-item-option-content")
    .filter({ hasText: /1 题.*检索对比/ })
    .first()
    .click();
  await expect(page.getByRole("heading", { name: "方案汇总" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "逐题核验" })).toBeVisible();
  await page.screenshot({
    path: screenshotRoot + "/evaluation.png",
    fullPage: true,
    animations: "disabled",
  });
});

test("real streamed chat and citation drawer", async ({ page, request }) => {
  let sessionId = "";
  page.on("response", async (response) => {
    if (
      response.url().endsWith("/api/sessions") &&
      response.request().method() === "POST"
    )
      sessionId = (await response.json()).id;
  });
  try {
    await page.goto("/");
    await page
      .getByPlaceholder("提问 xv6")
      .fill("walkaddr 为什么检查 PTE_U？请简短回答并引用源码。");
    await page.getByRole("button", { name: /^发送/ }).click();
    const citation = page
      .getByRole("button", { name: /kernel\/vm.c:/ })
      .first();
    await expect(citation).toBeVisible({ timeout: 160000 });
    await expect(
      page.locator(".message.assistant .inline-citation").first(),
    ).toBeVisible();
    await expect(page.locator(".message.assistant")).not.toContainText(
      /[0-9a-f]{64}/,
    );
    await page.screenshot({
      path: screenshotRoot + "/chat.png",
      fullPage: true,
      animations: "disabled",
    });
    await citation.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(
      page.locator("pre").filter({ hasText: "PTE_U" }).last(),
    ).toBeVisible();
    await page.screenshot({
      path: screenshotRoot + "/citation.png",
      fullPage: true,
      animations: "disabled",
    });
  } finally {
    if (sessionId) await request.delete("/api/sessions/" + sessionId);
  }
});
