from pathlib import Path
from ultralytics import YOLO


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "pothole" / "best.pt"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "detections"

# Detection settings
CONFIDENCE_THRESHOLD = 0.25
IMAGE_SIZE = 640


def detect_potholes(image_path: str) -> None:
    """Detect potholes in an image and save the annotated result."""

    image_path = Path(image_path).expanduser()

    # Validate input image
    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    # Validate trained model
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}"
        )

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nLoading YOLO StreetGuard AI model...")

    model = YOLO(str(MODEL_PATH))

    print("Detecting potholes. Please wait...\n")

    results = model.predict(
        source=str(image_path),
        conf=CONFIDENCE_THRESHOLD,
        imgsz=IMAGE_SIZE,
        device="cpu",
        save=False,
        verbose=False,
    )

    result = results[0]
    boxes = result.boxes

    # Save image with detection boxes
    output_path = OUTPUT_DIR / f"{image_path.stem}_detected.jpg"
    result.save(filename=str(output_path))

    # Display results
    print("=" * 45)
    print("YOLO STREETGUARD AI — DETECTION RESULTS")
    print("=" * 45)

    print(f"Input image: {image_path.name}")
    print(f"Potholes detected: {len(boxes)}")
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")

    for index, box in enumerate(boxes, start=1):
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        print(f"\nPothole {index}")
        print(f"  Confidence: {confidence:.2%}")
        print(
            f"  Bounding box: "
            f"x1={x1:.1f}, y1={y1:.1f}, "
            f"x2={x2:.1f}, y2={y2:.1f}"
        )

    print("\nAnnotated image saved to:")
    print(output_path.resolve())
    print("=" * 45)


if __name__ == "__main__":
    try:
        image_input = input(
            "Enter the full path to a road image: "
        ).strip().strip('"')

        detect_potholes(image_input)

    except (FileNotFoundError, ValueError) as error:
        print(f"\nError: {error}")

    except Exception as error:
        print(f"\nUnexpected error: {error}")
