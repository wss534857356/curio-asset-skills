#!/usr/bin/env python3
"""Read-only character texture checks. Requires Pillow; never rewrites images."""

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageChops


def check_maps(albedo, normal, mask=None, material=None, stride=8, cutoff=0.52):
    paths = {"albedo": Path(albedo), "normal": Path(normal)}
    if mask is not None:
        paths["mask"] = Path(mask)
    if material is not None:
        paths["material"] = Path(material)
    result = {
        "method": "Read-only sampled RGB direction checks within albedo alpha * mask green",
        "stride": stride,
        "coverage_cutoff": cutoff,
        "files": {},
        "errors": [],
        "warnings": [],
        "technical_checks_passed": False,
        "visual_review_required": True,
    }
    images = {}
    for role, path in paths.items():
        try:
            with Image.open(path) as source:
                result["files"][role] = {
                    "path": str(path.resolve()), "size": list(source.size), "mode": source.mode,
                }
                images[role] = source.convert("RGBA" if role == "albedo" else "RGB")
        except (OSError, ValueError) as error:
            result["errors"].append(f"Cannot read {role}: {path}: {error}")
    if result["errors"]:
        return result

    size = images["albedo"].size
    for role, image in images.items():
        if image.size != size:
            result["errors"].append(f"{role} dimensions {image.size} differ from albedo {size}")
    if result["errors"]:
        return result

    alpha = images["albedo"].getchannel("A")
    matte = images["mask"].getchannel("G") if "mask" in images else Image.new("L", size, 255)
    coverage = ImageChops.multiply(alpha, matte)
    # This bbox is a packaging diagnostic; runtime UV/landmark registration
    # still requires a visual check. The direction samples below use the exact product.
    visible = coverage.point(lambda value: 255 if value / 255 >= cutoff else 0)
    bounds = visible.getbbox()
    result["coverage"] = {
        "albedo_alpha_range": list(alpha.getextrema()),
        "mask_green_range": list(matte.getextrema()),
        "visible_bounds": list(bounds) if bounds else None,
        "visible_fraction": round(visible.histogram()[255] / (size[0] * size[1]), 6),
    }
    if bounds is None:
        result["errors"].append("No visible character at the selected coverage cutoff")
        return result
    if coverage.getextrema()[0] == 255:
        result["warnings"].append("No transparent background or mask gaps; inspect whether this is an intended full-canvas asset")

    a, m, n = alpha.load(), matte.load(), images["normal"].load()
    directions = []
    background_count = background_neutral = 0
    for y in range(0, size[1], stride):
        for x in range(0, size[0], stride):
            amount = a[x, y] * m[x, y] / (255 * 255)
            rgb = n[x, y]
            if amount >= cutoff:
                directions.append(rgb)
            elif amount <= 0.01:
                background_count += 1
                background_neutral += all(abs(v - target) <= 3 for v, target in zip(rgb, (128, 128, 255)))
    if not directions:
        result["errors"].append("Visible shape missed by sample grid; rerun with --stride 1")
        return result

    count = len(directions)
    means = [sum(rgb[c] for rgb in directions) / count for c in range(3)]
    deviations = [math.sqrt(sum((rgb[c] - means[c]) ** 2 for rgb in directions) / count) for c in range(3)]
    vectors = [tuple(v / 255 * 2 - 1 for v in rgb) for rgb in directions]
    lengths = [math.sqrt(sum(v * v for v in vector)) for vector in vectors]
    backwards = sum(vector[2] < 0 for vector in vectors) / count
    near_zero = sum(length < 0.05 for length in lengths) / count
    neutral_fraction = background_neutral / background_count if background_count else None
    result["normal"] = {
        "sampled_visible_pixels": count,
        "rgb_range": [[min(rgb[c] for rgb in directions), max(rgb[c] for rgb in directions)] for c in range(3)],
        "rgb_standard_deviation": [round(v, 4) for v in deviations],
        "backward_normal_fraction": round(backwards, 6),
        "near_zero_vector_fraction": round(near_zero, 6),
        "decoded_length_mean": round(sum(lengths) / count, 6),
        "sampled_background_pixels": background_count,
        "background_neutral_fraction": round(neutral_fraction, 6) if neutral_fraction is not None else None,
    }
    if max(deviations[:2]) < 1:
        result["warnings"].append("Very little X/Y direction variation; check for a placeholder or overly flat normal map")
    if backwards > 0:
        result["warnings"].append("Raw normal samples include negative Z; inspect their locations and the renderer's mip-filtered result")
    if near_zero > 0:
        result["warnings"].append("Near-zero encoded vectors found; inspect before relying on runtime normalization")
    if neutral_fraction is not None and neutral_fraction < 0.95:
        result["warnings"].append("Background RGB deviates from neutral normal; inspect silhouette-edge filtering and registration")
    result["technical_checks_passed"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--albedo", required=True, type=Path)
    parser.add_argument("--normal", required=True, type=Path)
    parser.add_argument("--mask", type=Path, help="Optional RGB matte; the green channel supplies coverage")
    parser.add_argument("--material", type=Path, help="Optional material texture; only dimensions are checked")
    parser.add_argument("--stride", type=int, default=8, help="Sampling interval in pixels; use 1 for small/thin assets")
    parser.add_argument("--cutoff", type=float, default=0.52, help="Visible alpha * mask cutoff")
    parser.add_argument("--report", type=Path, help="Optional JSON report; no image outputs are produced")
    args = parser.parse_args()
    if args.stride < 1 or not 0 < args.cutoff <= 1:
        parser.error("stride must be positive and cutoff must be in (0, 1]")
    if args.report is not None:
        if args.report.suffix.lower() != ".json":
            parser.error("--report must be a .json file")
        inputs = (args.albedo, args.mask, args.normal, args.material)
        if any(path is not None and args.report.resolve() == path.resolve() for path in inputs):
            parser.error("--report must not overwrite an input")
    result = check_maps(args.albedo, args.normal, args.mask, args.material, args.stride, args.cutoff)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["technical_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
