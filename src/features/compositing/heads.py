"""Head detection for character positioning."""

import io
import os
from dataclasses import dataclass
from typing import Protocol
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw
import replicate


@dataclass(frozen=True)
class HeadLayout:
    """Detected head positions (normalized 0-1)."""

    left: tuple[float, float]  # (x, y) for left character
    right: tuple[float, float]  # (x, y) for right character


class HeadDetector(Protocol):
    """Port for detecting character head positions in an image."""

    def detect(self, image_path: str, instance_dir: str) -> HeadLayout:
        """Detect head positions and return normalized coordinates."""
        ...


class GroundingDINOHeadDetector(HeadDetector):
    """Grounding DINO-based head detection via Replicate."""

    def detect(self, image_path: str, instance_dir: str) -> HeadLayout:
        """Detect character heads using split-detection for parallel processing."""
        try:
            print(f"🔍 Starting Parallel Split-Detection for: {image_path}")
            with Image.open(image_path) as full_img:
                w, h = full_img.size

                # Create masks for left and right halves
                left_mask = full_img.copy()
                draw_l = ImageDraw.Draw(left_mask)
                draw_l.rectangle([w // 2, 0, w, h], fill="black")
                left_path = os.path.join(instance_dir, "debug_split_left.png")
                left_mask.save(left_path)

                right_mask = full_img.copy()
                draw_r = ImageDraw.Draw(right_mask)
                draw_r.rectangle([0, 0, w // 2, h], fill="black")
                right_path = os.path.join(instance_dir, "debug_split_right.png")
                right_mask.save(right_path)

                # Detect in parallel
                with ThreadPoolExecutor(max_workers=2) as executor:
                    with open(left_path, "rb") as fl, open(right_path, "rb") as fr:
                        f_left = executor.submit(self._detect_side, fl.read(), "LEFT", w, h)
                        f_right = executor.submit(self._detect_side, fr.read(), "RIGHT", w, h)
                        res_l = f_left.result()
                        res_r = f_right.result()

                final_l = res_l if res_l else (0.25, 0.40)
                final_r = res_r if res_r else (0.75, 0.40)
                return HeadLayout(left=final_l, right=final_r)

        except Exception as e:
            print(f"💥 Split-Detection Critical Failure: {e}")

        return HeadLayout(left=(0.25, 0.40), right=(0.75, 0.40))

    @staticmethod
    def _detect_side(img_bytes: bytes, side_label: str, full_w: int, full_h: int) -> tuple[float, float] | None:
        """Detect head in one half of the image."""
        try:
            img_file = io.BytesIO(img_bytes)
            output = replicate.run(
                "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e20cc1d734c589f7dd01d2036921ed78aa",
                input={
                    "image": img_file,
                    "query": "the head or highest point of the entity",
                    "box_threshold": 0.12,
                    "text_threshold": 0.12,
                },
            )
            detections = output.get("detections", [])
            if detections:
                best = sorted(detections, key=lambda d: d["bbox"][1])[0]
                bbox = best["bbox"]
                if any(v > 2.0 for v in bbox):
                    cx = (bbox[0] + bbox[2]) / (2.0 * full_w)
                    ty = bbox[1] / full_h
                    return cx, ty
                return (bbox[0] + bbox[2]) / 2.0, bbox[1]
        except Exception as e:
            print(f"❌ AI Error ({side_label}): {e}")

        return None
