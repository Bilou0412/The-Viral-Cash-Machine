"""Pure, host-runnable tests for `editor.resolve` (E5).

No I/O, no network, no heavy deps (pydantic + the editor package only). Builds an
`EditorDocument` with image/video/voice/text bricks plus a narration layer and
asserts the resulting `RenderModel`: clip count/order, media types, src URLs,
layer clips and total_duration.
"""

from src.editor.document import (
    EditorDocument,
    GenerativeBrick,
    Layer,
    MediaBrick,
    NarrativeContext,
    TextBrick,
    TimelinePlacement,
)
from src.editor.resolve import resolve
from src.videospec.models import Canvas


def _doc() -> EditorDocument:
    return EditorDocument(
        title="t",
        canvas=Canvas(width=1080, height=1920, fps=30),
        global_context=NarrativeContext(text="histoire"),
        bricks=[
            GenerativeBrick(
                id="img",
                type="image",
                model_ref="bytedance/seedream-4.5",
                placement=TimelinePlacement(track=0, start=0.0, duration=3.0),
            ),
            GenerativeBrick(
                id="vid",
                type="video",
                model_ref="prunaai/p-video",
                placement=TimelinePlacement(track=0, start=3.0, duration=5.0),
                layers=[
                    Layer(
                        type="narration",
                        z=2,
                        payload={"brick_ref": "vo"},
                    ),
                    Layer(
                        type="text",
                        z=3,
                        payload={"content": "Bonjour"},
                    ),
                ],
            ),
            GenerativeBrick(
                id="vo",
                type="voice",
                model_ref="minimax/speech-2.8-turbo",
                placement=TimelinePlacement(track=1, start=3.0, duration=5.0),
            ),
            MediaBrick(
                id="clip",
                source_path="/x/intro.mp4",
                placement=TimelinePlacement(track=0, start=8.0, duration=2.0),
            ),
            TextBrick(
                id="title",
                payload={"content": "FIN"},
                placement=TimelinePlacement(track=2, start=10.0, duration=1.5),
            ),
        ],
    )


def test_resolve_maps_bricks_and_layers() -> None:
    doc = _doc()
    asset_src = {
        "img": "/api/assets/1/file",
        "vid": "/api/assets/2/file",
        "vo": "/api/assets/3/file",
    }
    model = resolve(doc, asset_src)

    by_id = {c.id: c for c in model.clips}

    # Canvas is carried over from the document.
    assert model.canvas.width == 1080 and model.canvas.height == 1920

    # Image brick -> image clip with the resolved src.
    assert by_id["img"].media == "image"
    assert by_id["img"].src == "/api/assets/1/file"
    assert by_id["img"].start == 0.0 and by_id["img"].duration == 3.0

    # Video brick -> video clip; voice -> audio clip.
    assert by_id["vid"].media == "video"
    assert by_id["vid"].src == "/api/assets/2/file"
    assert by_id["vo"].media == "audio"
    assert by_id["vo"].src == "/api/assets/3/file"

    # Media brick -> video clip (by .mp4 extension), text brick -> text clip.
    assert by_id["clip"].media == "video"
    assert by_id["clip"].src == "/x/intro.mp4"
    assert by_id["title"].media == "text"
    assert by_id["title"].text == "FIN"

    # Narration layer references the voice brick's asset; text layer is a clip.
    narration = by_id["vid:layer0"]
    assert narration.media == "audio"
    assert narration.src == "/api/assets/3/file"
    assert narration.z >= 2
    text_layer = by_id["vid:layer1"]
    assert text_layer.media == "text"
    assert text_layer.text == "Bonjour"
    assert text_layer.z >= 3

    # 5 bricks + 2 layers = 7 clips. Main clip of a brick precedes its layers.
    assert len(model.clips) == 7
    ids = [c.id for c in model.clips]
    assert ids.index("vid") < ids.index("vid:layer0") < ids.index("vid:layer1")

    # total_duration is the max(start + duration) across bricks.
    assert model.total_duration == 11.5

    # No subtitles are transcribed in the pure resolver (TODO at render time).
    assert all(c.subtitles == () for c in model.clips)


def test_resolve_missing_asset_leaves_src_none() -> None:
    doc = EditorDocument(
        bricks=[
            GenerativeBrick(
                id="img",
                type="image",
                placement=TimelinePlacement(start=0.0, duration=2.0),
            )
        ]
    )
    model = resolve(doc, {})  # asset not ready yet
    assert len(model.clips) == 1
    assert model.clips[0].media == "image"
    assert model.clips[0].src is None
    assert model.total_duration == 2.0
