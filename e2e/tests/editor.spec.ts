import { test, expect, type Page } from "@playwright/test"
import { watchPage, shot } from "./helpers"

// The key journey: open the editor, place bricks on the timeline (the blocks MUST
// be visible — this is the invisible-lane regression), inspect a brick (model
// selector + dynamic form), and wire one brick's media input to another. Composing
// must never trigger generation. No console errors / no failed requests allowed.

async function ensureProjectThenCreateDoc(page: Page): Promise<void> {
  await page.goto("/editor")

  // EditorIndex shows either the create card (projects exist) or an "Aucun projet"
  // empty state. If no project select is present, create one via /projects first.
  const projectSelect = page.locator("select").first()
  const hasProject = await projectSelect.count()

  if (!hasProject) {
    await page.goto("/projects")
    await page.getByRole("button", { name: "Créer un projet" }).first().click()
    await page.getByLabel("Nom du projet").fill("E2E Project")
    await page.getByRole("button", { name: "Créer" }).click()
    await page.goto("/editor")
    await expect(page.locator("select").first()).toBeVisible()
  }

  // Fill the title and create the document → navigates to /editor/<id>.
  const titleInput = page.getByLabel("Titre")
  await expect(titleInput).toBeVisible()
  await titleInput.fill("E2E Montage")
  await page.getByRole("button", { name: "Nouveau document" }).click()

  await expect(page).toHaveURL(/\/editor\/[^/]+$/)
}

test("editor journey: place bricks, inspect, connect — no errors", async ({ page }, info) => {
  const w = watchPage(page)

  // 1. Reach a fresh editor document.
  await ensureProjectThenCreateDoc(page)

  // Editor chrome loaded.
  await expect(page.getByTestId("brick-palette")).toBeVisible()
  await shot(page, info, "01-editor-loaded")

  // 2. Palette lists at least Image and Texte.
  const palette = page.getByTestId("brick-palette")
  await expect(palette.getByTestId("palette-item-image")).toBeVisible()
  await expect(palette.getByTestId("palette-item-text")).toBeVisible()

  // Count timeline blocks before we add anything (the seeded doc has a couple).
  const blocksBefore = await page.locator('[data-testid^="timeline-block-"]').count()

  // 3. Click the Image palette item → a brick block appears on the timeline and
  //    is VISIBLE with non-zero width (the invisible-lane regression).
  await palette.getByTestId("palette-item-image").click()

  const imageBlocks = page.locator('[data-testid^="timeline-block-"][data-brick-type="image"]')
  await expect(imageBlocks.first()).toBeVisible()
  await expect
    .poll(async () => page.locator('[data-testid^="timeline-block-"]').count())
    .toBeGreaterThan(blocksBefore)

  // The newly added image block is the selected one — verify it has real width.
  const newImageBlock = imageBlocks.last()
  await expect(newImageBlock).toBeVisible()
  const box = await newImageBlock.boundingBox()
  expect(box, "timeline block must have a bounding box").not.toBeNull()
  expect(box!.width, "timeline block width must be > 0 (visible lane)").toBeGreaterThan(0)
  await shot(page, info, "02-image-block-on-timeline")

  // 4. Click the timeline block → inspector shows a model selector + a form field.
  await newImageBlock.click()
  const inspector = page.getByTestId("inspector")
  await expect(inspector).toBeVisible()
  await expect(inspector.getByText("Modèle", { exact: true })).toBeVisible()
  // At least one dynamic form field from the mock model form (image → "prompt").
  await expect(inspector.getByText("Paramètres", { exact: true })).toBeVisible()
  await expect(inspector.getByText("prompt", { exact: true })).toBeVisible()
  await shot(page, info, "03-inspector-image")

  // 5. Add a Vidéo brick, select it, and connect its media input (the "image"
  //    field) to another brick via the ⛓ connect control → a connection chip.
  await palette.getByTestId("palette-item-video").click()
  const videoBlock = page
    .locator('[data-testid^="timeline-block-"][data-brick-type="video"]')
    .last()
  await expect(videoBlock).toBeVisible()
  await videoBlock.click()

  // The video model form exposes an "image" file field, which is connectable.
  await expect(inspector.getByText("image", { exact: true })).toBeVisible()
  const connectSelect = inspector.getByLabel("Connecter à une brique")
  await expect(connectSelect).toBeVisible()

  // Pick the first available source brick (any non-text brick, e.g. the image).
  const optionValues = await connectSelect.locator("option").evaluateAll((opts) =>
    (opts as HTMLOptionElement[]).map((o) => o.value).filter((v) => v !== "")
  )
  expect(optionValues.length, "expected at least one connectable brick").toBeGreaterThan(0)
  await connectSelect.selectOption(optionValues[0])

  // A connection chip (⛓ / Link2 with a "Déconnecter" affordance) appears.
  await expect(
    inspector.getByRole("button", { name: /Déconnecter/i })
  ).toBeVisible()
  await shot(page, info, "04-connected")

  // 6. Composing must NOT have triggered generation: the brick stays "non généré".
  //    (Generation in mock mode would flip the StatusBadge; we assert it didn't.)
  await expect(inspector.getByText("non généré").first()).toBeVisible()

  w.assertClean()
})
