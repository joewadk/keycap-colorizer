import argparse
from pathlib import Path

from pydantic import ValidationError

from app.colors.sampling import Crop, SamplingError, sample_image


def main():
    parser = argparse.ArgumentParser(description="Sample an approximate palette from a local product image (no network or AI).")
    parser.add_argument("image", type=Path)
    parser.add_argument("--crop", type=float, nargs=4, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                        help="Fractional bounds (0–1) in the oriented image")
    parser.add_argument("--max-colors", type=int, default=6)
    args = parser.parse_args()
    try:
        crop = Crop(**dict(zip(("left", "top", "right", "bottom"), args.crop))) if args.crop else None
        print(sample_image(args.image, crop=crop, max_colors=args.max_colors).model_dump_json(indent=2))
    except (SamplingError, ValidationError) as error:
        parser.exit(1, f"Palette sampling failed: {error}\n")


if __name__ == "__main__":
    main()
