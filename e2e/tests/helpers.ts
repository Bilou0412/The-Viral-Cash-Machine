import { type Page, type TestInfo, expect } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

const SHOTS_DIR = path.resolve(__dirname, "..", "screenshots")

// Attach console-error + failed-response collectors to a page. Returns the two
// arrays plus an assert() to call at the end of a test. We ignore benign noise:
// the Vite dev client, sourcemap probes, and known-irrelevant network failures.
export function watchPage(page: Page) {
  const consoleErrors: string[] = []
  const failedResponses: string[] = []

  page.on("console", (msg) => {
    if (msg.type() !== "error") return
    const text = msg.text()
    if (isIgnorableConsole(text)) return
    consoleErrors.push(text)
  })

  page.on("pageerror", (err) => {
    consoleErrors.push(`pageerror: ${err.message}`)
  })

  page.on("response", (res) => {
    const status = res.status()
    if (status < 400) return
    const url = res.url()
    if (isIgnorableUrl(url)) return
    failedResponses.push(`${status} ${url}`)
  })

  return {
    consoleErrors,
    failedResponses,
    assertClean() {
      expect(
        consoleErrors,
        `console errors:\n${consoleErrors.join("\n")}`
      ).toEqual([])
      expect(
        failedResponses,
        `failed network responses:\n${failedResponses.join("\n")}`
      ).toEqual([])
    },
  }
}

function isIgnorableConsole(text: string): boolean {
  return (
    text.includes("[vite] connecting") ||
    text.includes("Download the React DevTools") ||
    text.includes("favicon.ico")
  )
}

function isIgnorableUrl(url: string): boolean {
  return (
    url.endsWith("/favicon.ico") ||
    url.includes("/@vite/") ||
    url.includes(".map")
  )
}

if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true })

export async function shot(page: Page, info: TestInfo, name: string) {
  const file = path.join(SHOTS_DIR, `${info.title.replace(/[^a-z0-9]+/gi, "-")}__${name}.png`)
  await page.screenshot({ path: file, fullPage: false })
  return file
}
