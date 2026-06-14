/**
 * EditorComposition — renders a resolved RenderModel.
 *
 * Used both by the editor preview (`@remotion/player`) and by `renderMedia`
 * (CLI export). Each clip becomes a <Sequence>; clips are drawn ordered by
 * (track, z) so later items stack on top.
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { RenderClip, RenderModel, SubtitleWord } from "./renderModel";

const secToFrames = (seconds: number, fps: number): number =>
  Math.round(seconds * fps);

/** Timed subtitle overlay: shows the words active at the current frame. */
const Subtitles: React.FC<{ words: SubtitleWord[] }> = ({ words }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps; // seconds within this Sequence
  const active = words
    .filter((w) => t >= w.start && t < w.end)
    .map((w) => w.text)
    .join(" ");
  if (!active) return null;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: "12%",
      }}
    >
      <span
        style={{
          fontFamily: "sans-serif",
          fontSize: 64,
          fontWeight: 800,
          color: "#ffffff",
          textAlign: "center",
          padding: "0.2em 0.5em",
          background: "rgba(0,0,0,0.55)",
          borderRadius: 12,
          maxWidth: "90%",
          lineHeight: 1.1,
        }}
      >
        {active}
      </span>
    </AbsoluteFill>
  );
};

const ClipBody: React.FC<{ clip: RenderClip }> = ({ clip }) => {
  const style = (clip.style ?? {}) as React.CSSProperties;
  const transform = (clip.transform ?? {}) as React.CSSProperties;

  switch (clip.media) {
    case "video":
      return clip.src ? (
        <OffthreadVideo
          src={clip.src}
          style={{ width: "100%", height: "100%", objectFit: "cover", ...transform }}
        />
      ) : null;
    case "image":
      return (
        <AbsoluteFill>
          {clip.src ? (
            <Img
              src={clip.src}
              style={{ width: "100%", height: "100%", objectFit: "cover", ...transform }}
            />
          ) : null}
        </AbsoluteFill>
      );
    case "audio":
      return clip.src ? <Audio src={clip.src} /> : null;
    case "text":
    case "overlay":
      return (
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            ...transform,
          }}
        >
          {clip.text ? (
            <span
              style={{
                fontFamily: "sans-serif",
                fontSize: 72,
                fontWeight: 700,
                color: "#ffffff",
                textAlign: "center",
                ...style,
              }}
            >
              {clip.text}
            </span>
          ) : null}
        </AbsoluteFill>
      );
    default:
      return null;
  }
};

export const EditorComposition: React.FC<RenderModel> = ({ canvas, clips }) => {
  // canvas.fps is the source of truth for clip placement; useVideoConfig() is
  // used inside <Subtitles> for second-accurate timing within each Sequence.
  const ordered = [...clips].sort((a, b) => {
    if (a.track !== b.track) return a.track - b.track;
    return a.z - b.z;
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {ordered.map((clip) => {
        const from = secToFrames(clip.start, canvas.fps);
        const durationInFrames = Math.max(
          1,
          secToFrames(clip.duration, canvas.fps),
        );
        return (
          <Sequence
            key={clip.id}
            from={from}
            durationInFrames={durationInFrames}
            name={`${clip.media}:${clip.id}`}
          >
            <ClipBody clip={clip} />
            {clip.subtitles.length > 0 ? (
              <Subtitles words={clip.subtitles} />
            ) : null}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
