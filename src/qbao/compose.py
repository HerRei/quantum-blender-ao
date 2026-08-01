"""Create a labelled side-by-side comparison from Blender renders."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def compose_comparison(
    exact_path: Path,
    monte_carlo_path: Path,
    qae_path: Path,
    results_path: Path,
    output_path: Path,
) -> None:
    """Combine three equally sized renders with experiment metrics."""

    paths = [exact_path, monte_carlo_path, qae_path]
    images = [Image.open(path).convert("RGB") for path in paths]
    if len({image.size for image in images}) != 1:
        raise ValueError("all rendered images must have the same dimensions")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    summary = results["summary"]
    labels = [
        "Exact reference",
        f"Monte Carlo  |  RMSE {summary['monte_carlo']['rmse_vs_exact']:.4f}",
        f"Simulated QAE  |  RMSE {summary['qae']['rmse_vs_exact']:.4f}",
    ]

    panel_width, panel_height = images[0].size
    header_height = 44
    footer_height = 58
    canvas = Image.new(
        "RGB",
        (panel_width * len(images), panel_height + header_height + footer_height),
        (18, 20, 27),
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    small_font = ImageFont.load_default(size=14)

    for index, (image, label) in enumerate(zip(images, labels, strict=True)):
        left = index * panel_width
        canvas.paste(image, (left, header_height))
        box = draw.textbbox((0, 0), label, font=font)
        text_width = box[2] - box[0]
        draw.text(
            (left + (panel_width - text_width) / 2, 12),
            label,
            fill=(235, 239, 247),
            font=font,
        )

    settings = results["settings"]
    footer = (
        f"{results['direction_count']} Blender ray directions per probe  |  "
        f"matched MC/QAE logical-query budget: "
        f"{summary['qae']['logical_queries_per_probe']}  |  "
        f"QAE max circuit depth: {summary['qae']['max_circuit_depth']}  |  "
        f"seed: {settings['seed']}"
    )
    draw.text(
        (18, panel_height + header_height + 20),
        footer,
        fill=(184, 194, 210),
        font=small_font,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
