/**
 * cli.ts — render a RenderModel JSON to MP4.
 *
 *   node dist/cli.js --props path/to/render_model.json --out path/to/out.mp4
 *
 * Steps: read+validate props (zod) -> bundle() -> selectComposition() ->
 * renderMedia({ codec: "h264" }). Duration/size/fps come from the model via
 * the composition's calculateMetadata.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { RenderModelSchema, type RenderModel } from "./renderModel";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

interface Args {
  props: string;
  out: string;
}

function parseArgs(argv: string[]): Args {
  const args: Partial<Args> = {};
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (flag === "--props") args.props = argv[++i];
    else if (flag === "--out") args.out = argv[++i];
  }
  if (!args.props || !args.out) {
    throw new Error(
      "Usage: render --props <render_model.json> --out <output.mp4>",
    );
  }
  return { props: args.props, out: args.out };
}

async function main(): Promise<void> {
  const { props, out } = parseArgs(process.argv.slice(2));

  const raw = JSON.parse(readFileSync(path.resolve(props), "utf-8"));
  const model: RenderModel = RenderModelSchema.parse(raw);
  console.log(
    `[render] validated RenderModel: ${model.clips.length} clip(s), ` +
      `${model.canvas.width}x${model.canvas.height}@${model.canvas.fps}, ` +
      `${model.total_duration}s`,
  );

  // Root.tsx registers the "editor" composition.
  const entry = path.resolve(__dirname, "Root.js");
  console.log("[render] bundling...");
  const serveUrl = await bundle({
    entryPoint: entry,
    onProgress: (p) => process.stdout.write(`\r[render] bundle ${p}%   `),
  });
  process.stdout.write("\n");

  console.log("[render] selecting composition...");
  const composition = await selectComposition({
    serveUrl,
    id: "editor",
    inputProps: model,
  });

  const outputLocation = path.resolve(out);
  console.log(`[render] rendering -> ${outputLocation}`);
  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    outputLocation,
    inputProps: model,
    onProgress: ({ progress }) =>
      process.stdout.write(`\r[render] ${Math.round(progress * 100)}%   `),
  });
  process.stdout.write("\n");
  console.log(`[render] done: ${outputLocation}`);
}

main().catch((err) => {
  console.error("[render] failed:", err);
  process.exit(1);
});
