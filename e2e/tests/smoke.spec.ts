import { test, expect } from "@playwright/test"
import { watchPage, shot } from "./helpers"

// Smoke: load the app and walk the sidebar. Each page must render a heading and
// produce no console errors / no 4xx-5xx responses.
test("sidebar navigation renders pages cleanly", async ({ page }, info) => {
  const w = watchPage(page)

  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible()
  await shot(page, info, "dashboard")

  // Projets
  await page.getByRole("link", { name: "Projets" }).click()
  await expect(page).toHaveURL(/\/projects$/)
  await expect(page.getByRole("heading", { name: "Projets" })).toBeVisible()
  await shot(page, info, "projects")

  // Éditeur (EditorIndex)
  await page.getByRole("link", { name: "Éditeur" }).click()
  await expect(page).toHaveURL(/\/editor$/)
  await expect(page.getByRole("heading", { name: "Éditeur" })).toBeVisible()
  await shot(page, info, "editor-index")

  // Bibliothèque
  await page.getByRole("link", { name: "Bibliothèque" }).click()
  await expect(page).toHaveURL(/\/library$/)
  await expect(page.getByRole("heading", { name: "Bibliothèque" })).toBeVisible()
  await shot(page, info, "library")

  w.assertClean()
})
