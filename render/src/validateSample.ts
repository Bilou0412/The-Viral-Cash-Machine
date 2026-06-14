/**
 * validateSample.ts — smoke test: validates the sample RenderModel against the
 * zod schema. Run via `npm run validate:sample` (tsx).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { RenderModelSchema } from "./renderModel";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const samplePath = path.resolve(
  __dirname,
  "..",
  "sample",
  "render_model.sample.json",
);

const raw = JSON.parse(readFileSync(samplePath, "utf-8"));
const result = RenderModelSchema.safeParse(raw);

if (!result.success) {
  console.error("[validateSample] INVALID:");
  console.error(JSON.stringify(result.error.issues, null, 2));
  process.exit(1);
}

const model = result.data;
console.log(
  `[validateSample] OK — ${model.clips.length} clips, ` +
    `${model.canvas.width}x${model.canvas.height}@${model.canvas.fps}, ` +
    `total_duration=${model.total_duration}s`,
);
console.log(
  "[validateSample] media types:",
  model.clips.map((c) => c.media).join(", "),
);
