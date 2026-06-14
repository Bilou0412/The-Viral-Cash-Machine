import { defineConfig, devices } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

// Some sandboxed hosts lack root to `playwright install --with-deps`, so the
// chromium shared libs (libnspr4/libnss3/…) are vendored under .pw-libs and
// extracted there by `make e2e` / setup. If that dir exists, make the browser
// child process find them. A no-op on properly-provisioned machines.
const vendoredLibs = path.resolve(__dirname, ".pw-libs")
if (fs.existsSync(vendoredLibs)) {
  process.env.LD_LIBRARY_PATH = [vendoredLibs, process.env.LD_LIBRARY_PATH]
    .filter(Boolean)
    .join(":")
}

// E2E harness (AUTONOMY_PLAN V3): drives the real editor in a headless browser
// against the in-memory mock backend (VITE_USE_MOCKS=true) — no Python needed.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    screenshot: "on",
    trace: "on-first-retry",
    video: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm --prefix ../frontend run dev -- --port 5173 --strictPort",
    env: { VITE_USE_MOCKS: "true" },
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
