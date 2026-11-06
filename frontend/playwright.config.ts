import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 180000,
  workers: 1,
  use: {
    actionTimeout: 15000,
    baseURL: "http://127.0.0.1:8010",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      ".venv\\Scripts\\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8010",
    cwd: "..",
    env: { HF_HUB_OFFLINE: "1" },
    url: "http://127.0.0.1:8010/api/sessions",
    timeout: 60000,
    reuseExistingServer: false,
  },
  reporter: [["list"]],
  outputDir: "../tmp/browser/test-results",
});
