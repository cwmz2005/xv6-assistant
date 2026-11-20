import { test, expect } from "@playwright/test";
const screenshotRoot = "../tmp/browser/run-" + Date.now();

test("home and lazy-loaded knowledge management", async ({ page }) => {
  const errors: string[] = [];
  const requests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => requests.push(request.url()));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "深挖源码，为你的 xv6 学习旅程保驾护航。" }),
  ).toBeVisible();
  await expect(page.getByPlaceholder("向 xv6 学习助手提问")).toBeVisible();
  await expect(page.getByText("补充搜索", { exact: true })).toBeVisible();
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
    data: {
      query: "walkaddr PTE_U",
      strategy: "bm25",
      top_k: 1,
      rerank: false,
    },
    timeout: 120000,
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
    timeout: 120000,
  });
  expect(fixture.ok()).toBeTruthy();
  await page.goto("/");
  await page.getByPlaceholder("提问 xv6").fill("walkaddr PTE_U");
  await page.getByRole("button", { name: "检索调试", exact: true }).click();
  await expect(page.getByRole("tab", { name: "关键词 BM25" })).toBeVisible({
    timeout: 120000,
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
      .fill(
        "walkaddr 为什么检查 PTE_U？请简短回答，并且必须在回答中使用至少一处检索到的源码片段引用。",
      );
    await page.getByRole("button", { name: /^发送/ }).click();
    const citation = page.locator(".message.assistant .citation-chip").first();
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
    await expect(page.locator(".ant-drawer-title").last()).toContainText(
      "引用原文",
    );
    await expect(page.locator(".source-content")).toBeVisible();
    await page.screenshot({
      path: screenshotRoot + "/citation.png",
      fullPage: true,
      animations: "disabled",
    });
  } finally {
    if (sessionId) await request.delete("/api/sessions/" + sessionId);
  }
});

test("generation process card and live details drawer", async ({
  page,
  request,
}) => {
  let sessionId = "";
  page.on("response", async (response) => {
    if (
      response.url().endsWith("/api/sessions") &&
      response.request().method() === "POST"
    )
      sessionId = (await response.json()).id;
  });
  const question = "walkaddr 为什么检查 PTE_U？请简短回答。E2E详情验证";
  try {
    await page.goto("/");
    await page.getByPlaceholder("提问 xv6").fill(question);
    const streamRequest = page.waitForRequest(
      (request) =>
        request.url().endsWith("/api/chat/stream") &&
        request.method() === "POST",
    );
    await page.getByRole("button", { name: /^发送/ }).click();
    expect((await streamRequest).postDataJSON().show_details).toBeUndefined();

    // Details are always collected and open in a separate drawer per message.
    const detailsLink = page.getByRole("button", { name: /^生成详情/ }).first();
    await expect(detailsLink).toBeVisible({ timeout: 160000 });
    await detailsLink.click();
    await expect(page.getByText("系统 Prompt", { exact: true })).toBeVisible({
      timeout: 160000,
    });
    await expect(page.getByText("RAG 注入内容", { exact: true })).toBeVisible();
    await expect(
      page.locator(".generation-details").getByText("命中片段"),
    ).toBeVisible();
    await expect(
      page.locator(".detail-name", { hasText: "完整 Prompt" }).first(),
    ).toBeVisible();
    await expect(page.getByText("最终上下文", { exact: true })).toBeVisible({
      timeout: 160000,
    });
    await page.screenshot({
      path: screenshotRoot + "/details.png",
      fullPage: true,
      animations: "disabled",
    });
    await page.locator(".ant-drawer-close").last().click();
    await expect(page.locator(".generation-details")).toBeHidden();

    // The process summary stays with the answer.
    await expect(
      page.getByText("思考与检索过程", { exact: true }),
    ).toBeVisible();

    // Reloading history keeps both the process card and the persisted details.
    await page.reload();
    await page
      .locator(".history-item", { hasText: "E2E详情验证" })
      .first()
      .click();
    await expect(
      page.getByText("思考与检索过程", { exact: true }),
    ).toBeVisible();
    const historyLink = page.getByRole("button", { name: /^生成详情/ }).first();
    await expect(historyLink).toBeEnabled();
    await historyLink.click();
    await expect(page.getByText("系统 Prompt", { exact: true })).toBeVisible();
    await expect(
      page.locator(".detail-name", { hasText: "完整 Prompt" }).first(),
    ).toBeVisible();
  } finally {
    if (sessionId) await request.delete("/api/sessions/" + sessionId);
  }
});
