from pathlib import Path

from PIL import Image

from streetguard.config import get_settings
from streetguard.detection import Detector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "pothole" / "best.pt"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "detections"
CONFIDENCE_THRESHOLD = 0.25
IMAGE_SIZE = 640


def detect_potholes(image_path: str) -> None:
    """Detect potholes through the reusable service and retain the CLI output."""
    path = Path(image_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    supported_formats = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
    if path.suffix.lower() not in supported_formats:
        raise ValueError(
            f"Unsupported image format: {path.suffix}. "
            f"Supported formats: {', '.join(sorted(supported_formats))}"
        )

    settings = get_settings()
    detector = Detector(
        MODEL_PATH,
        checksum=settings.model_checksum,
        confidence_threshold=CONFIDENCE_THRESHOLD,
        image_size=IMAGE_SIZE,
        device="cpu",
    )
    print("\nLoading YOLO StreetGuard AI model...")
    print("Detecting potholes. Please wait...\n")
    content = path.read_bytes()
    with Image.open(path) as image:
        mime_type = Image.MIME.get(image.format, "") if image.format else ""
    result = detector.detect(content, mime_type)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{path.stem}_detected.jpg"
    output_path.write_bytes(result.annotated_bytes)

    with Image.open(path) as image:
        width, height = image.size

    print("=" * 45)
    print("YOLO STREETGUARD AI — DETECTION RESULTS")
    print("=" * 45)
    print(f"Input image: {path.name}")
    print(f"Potholes detected: {len(result.boxes)}")
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")
    for index, box in enumerate(result.boxes, start=1):
        x1 = (box.x_center - box.box_width / 2) * width
        y1 = (box.y_center - box.box_height / 2) * height
        x2 = (box.x_center + box.box_width / 2) * width
        y2 = (box.y_center + box.box_height / 2) * height
        print(f"\nPothole {index}")
        print(f"  Confidence: {box.confidence:.2%}")
        print(f"  Bounding box: x1={x1:.1f}, y1={y1:.1f}, x2={x2:.1f}, y2={y2:.1f}")
    print("\nAnnotated image saved to:")
    print(output_path.resolve())
    print("=" * 45)


if __name__ == "__main__":
    try:
        image_input = input("Enter the full path to a road image: ").strip().strip('"')
        detect_potholes(image_input)
    except (FileNotFoundError, ValueError) as error:
        print(f"\nError: {error}")
    except Exception as error:
        print(f"\nUnexpected error: {error}")
