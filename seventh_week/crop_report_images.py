from pathlib import Path

from PIL import Image, ImageChops


WORK = Path(
    r"C:\Users\31523\.codex\visualizations\2026\10\18"
    r"\01a14e9d-59e3-7da0-8477-06de4166ae0d\week7_build"
)


def trim(image_name: str) -> None:
    source = Image.open(WORK / image_name).convert("RGB")
    background = Image.new("RGB", source.size, source.getpixel((0, 0)))
    box = ImageChops.difference(source, background).getbbox()
    if box is None:
        raise RuntimeError(f"No content found in {image_name}")
    left, top, right, bottom = box
    padding = 24
    cropped = source.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(source.width, right + padding),
            min(source.height, bottom + padding),
        )
    )
    cropped.save(WORK / image_name.replace(".png", "_crop.png"))


for name in ("technical_route.png", "jd_results.png", "terminal_verification.png"):
    trim(name)
