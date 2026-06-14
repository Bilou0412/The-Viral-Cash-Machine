/**
 * Root.tsx — registers the single "editor" composition.
 *
 * Dimensions/fps/duration are derived from the RenderModel input props via
 * calculateMetadata, so the same composition serves any canvas. The static
 * defaults below are only placeholders for the Studio preview before props
 * are supplied.
 */
import React from "react";
import { Composition, registerRoot } from "remotion";
import { EditorComposition } from "./EditorComposition";
import { RenderModelSchema, type RenderModel } from "./renderModel";

const DEFAULT_PROPS: RenderModel = {
  version: "1.0",
  canvas: { width: 1080, height: 1920, fps: 24 },
  clips: [],
  total_duration: 1,
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="editor"
      component={EditorComposition}
      // Placeholders; real values come from calculateMetadata.
      durationInFrames={24}
      fps={24}
      width={1080}
      height={1920}
      defaultProps={DEFAULT_PROPS}
      calculateMetadata={({ props }) => {
        const model = RenderModelSchema.parse(props);
        const fps = model.canvas.fps;
        return {
          props: model,
          durationInFrames: Math.max(1, Math.round(model.total_duration * fps)),
          fps,
          width: model.canvas.width,
          height: model.canvas.height,
        };
      }}
    />
  );
};

registerRoot(RemotionRoot);
