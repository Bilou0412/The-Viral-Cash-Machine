/**
 * renderModel.ts — zod mirror of the resolved RENDER contract.
 *
 * Lockstep counterpart of `src/editor/render_model.py` (pydantic). A Python
 * contract test dumps a `RenderModel` and validates it against this schema.
 *
 * Keep these two files in sync. The pydantic side is `frozen + extra="forbid"`,
 * so this schema is strict too (`.strict()` rejects unknown keys), and matches
 * the same defaults (canvas 1080x1920@24, track/z 0, subtitles []).
 */
import { z } from "zod";

/** A subtitled word with its timing (seconds). */
export const SubtitleWordSchema = z
  .object({
    text: z.string(),
    start: z.number(),
    end: z.number(),
  })
  .strict();
export type SubtitleWord = z.infer<typeof SubtitleWordSchema>;

/** Free-form style/transform bags — pydantic side is Dict[str, Any] | None. */
const FreeBag = z.record(z.string(), z.unknown());

/** A resolved element placed on a track, ready for Remotion. */
export const RenderClipSchema = z
  .object({
    id: z.string(),
    media: z.enum(["video", "image", "audio", "text", "overlay"]),
    src: z.string().nullable().optional().default(null),
    start: z.number(), // seconds on the timeline
    duration: z.number(), // seconds
    track: z.number().int().default(0),
    z: z.number().int().default(0), // stacking order
    text: z.string().nullable().optional().default(null),
    style: FreeBag.nullable().optional().default(null),
    subtitles: z.array(SubtitleWordSchema).default([]),
    transform: FreeBag.nullable().optional().default(null),
  })
  .strict();
export type RenderClip = z.infer<typeof RenderClipSchema>;

/** Output frame size + frame rate. Defaults mirror videospec.models.Canvas. */
export const CanvasSchema = z
  .object({
    width: z.number().int().default(1080),
    height: z.number().int().default(1920),
    fps: z.number().int().default(24),
  })
  .strict();
export type Canvas = z.infer<typeof CanvasSchema>;

/** Resolved video: canvas + ordered clips + total duration. Remotion props. */
export const RenderModelSchema = z
  .object({
    version: z.literal("1.0").default("1.0"),
    canvas: CanvasSchema.default({ width: 1080, height: 1920, fps: 24 }),
    clips: z.array(RenderClipSchema).default([]),
    total_duration: z.number().default(0), // seconds
  })
  .strict();
export type RenderModel = z.infer<typeof RenderModelSchema>;
