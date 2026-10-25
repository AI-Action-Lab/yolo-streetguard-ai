import json
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "annotated-images"
SPLITS_FILE = PROJECT_ROOT / "data" / "raw" / "splits.json"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "potholes"

CLASS_NAMES = ["pothole"]
CLASS_TO_ID = {"pothole": 0}

VALIDATION_RATIO = 0.10
RANDOM_SEED = 42


# --------------------------------------------------
# Annotation utilities
# --------------------------------------------------

def find_image(filename):
    """Find an image by filename without relying on XML paths."""
    matches = list(RAW_DIR.rglob(Path(filename).name))

    if len(matches) == 0:
        return None

    if len(matches) > 1:
        raise ValueError(f"Duplicate image filename found: {filename}")

    return matches[0]


def convert_annotation(xml_path, label_path):
    """Convert Pascal VOC XML boxes to normalized YOLO labels."""
    root = ET.parse(xml_path).getroot()

    size = root.find("size")

    if size is None:
        raise ValueError("Missing image size")

    width = int(size.findtext("width", "0"))
    height = int(size.findtext("height", "0"))

    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions")

    lines = []

    for obj in root.findall("object"):
        class_name = (obj.findtext("name") or "").strip().lower()

        if class_name not in CLASS_TO_ID:
            continue

        box = obj.find("bndbox")

        if box is None:
            raise ValueError("Object is missing its bounding box")

        xmin = float(box.findtext("xmin", "0"))
        ymin = float(box.findtext("ymin", "0"))
        xmax = float(box.findtext("xmax", "0"))
        ymax = float(box.findtext("ymax", "0"))

        if not (
            0 <= xmin < xmax <= width
            and 0 <= ymin < ymax <= height
        ):
            raise ValueError(
                f"Invalid bounding box: {xmin}, {ymin}, {xmax}, {ymax}"
            )

        x_center = ((xmin + xmax) / 2) / width
        y_center = ((ymin + ymax) / 2) / height
        box_width = (xmax - xmin) / width
        box_height = (ymax - ymin) / height

        lines.append(
            f"{CLASS_TO_ID[class_name]} "
            f"{x_center:.6f} {y_center:.6f} "
            f"{box_width:.6f} {box_height:.6f}"
        )

    label_path.parent.mkdir(parents=True, exist_ok=True)

    label_path.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )

    return len(lines)


# --------------------------------------------------
# Split handling
# --------------------------------------------------

def prepare_splits(splits):
    """Create train/validation from train; preserve the original test list."""
    original_train = list(splits.get("train", []))
    original_test = list(splits.get("test", []))

    if not original_train or not original_test:
        raise ValueError(
            "Both train and test lists must exist and contain filenames."
        )

    if len(set(original_train)) != len(original_train):
        raise ValueError("Duplicate filenames exist in the training split.")

    if len(set(original_test)) != len(original_test):
        raise ValueError("Duplicate filenames exist in the test split.")

    overlap = set(original_train) & set(original_test)

    if overlap:
        raise ValueError(
            f"Train/test overlap detected: {sorted(overlap)[:10]}"
        )

    rng = random.Random(RANDOM_SEED)
    shuffled_train = original_train.copy()
    rng.shuffle(shuffled_train)

    val_count = max(1, round(len(shuffled_train) * VALIDATION_RATIO))

    if len(shuffled_train) < 2:
        raise ValueError("Not enough training files to create validation data.")

    val_files = shuffled_train[:val_count]
    train_files = shuffled_train[val_count:]

    return {
        "train": train_files,
        "val": val_files,
        "test": original_test,
    }


# --------------------------------------------------
# Conversion pipeline
# --------------------------------------------------

def main():
    if not RAW_DIR.is_dir():
        raise FileNotFoundError(f"Dataset folder not found: {RAW_DIR}")

    if not SPLITS_FILE.is_file():
        raise FileNotFoundError(f"Split file not found: {SPLITS_FILE}")

    with SPLITS_FILE.open("r", encoding="utf-8") as file:
        original_splits = json.load(file)

    splits = prepare_splits(original_splits)

    # Start fresh so old labels/images cannot be mixed with new results.
    # This deletes only the generated processed/potholes directory.
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    total_images = 0
    total_boxes = 0
    skipped = []

    for split_name, xml_files in splits.items():
        print(f"\nProcessing {split_name}: {len(xml_files)} annotations")

        for xml_name in xml_files:
            xml_path = RAW_DIR / Path(xml_name).name

            if not xml_path.is_file():
                skipped.append(f"Missing XML: {xml_name}")
                continue

            try:
                root = ET.parse(xml_path).getroot()
                image_name = root.findtext("filename")

                if not image_name:
                    skipped.append(f"Missing filename in XML: {xml_name}")
                    continue

                image_path = find_image(image_name)

                if image_path is None:
                    skipped.append(f"Missing image: {image_name}")
                    continue

                image_output_dir = OUTPUT_DIR / "images" / split_name
                label_output_dir = OUTPUT_DIR / "labels" / split_name

                image_output_dir.mkdir(parents=True, exist_ok=True)

                destination_image = image_output_dir / image_path.name
                destination_label = (
                    label_output_dir / f"{xml_path.stem}.txt"
                )

                if destination_image.exists() or destination_label.exists():
                    skipped.append(f"Output filename collision: {xml_name}")
                    continue

                box_count = convert_annotation(
                    xml_path,
                    destination_label,
                )

                shutil.copy2(image_path, destination_image)

                total_boxes += box_count
                total_images += 1

            except (ET.ParseError, ValueError, OSError) as error:
                skipped.append(f"{xml_name}: {error}")

    yaml_text = (
        f"path: {OUTPUT_DIR.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        "  0: pothole\n"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUTPUT_DIR / "data.yaml").write_text(
        yaml_text,
        encoding="utf-8",
    )

    print("\n========== DATASET SUMMARY ==========")

    for split_name in ("train", "val", "test"):
        image_dir = OUTPUT_DIR / "images" / split_name
        count = len(list(image_dir.glob("*"))) if image_dir.exists() else 0
        print(f"{split_name.capitalize()} images: {count}")

    print(f"Total images processed: {total_images}")
    print(f"Total pothole boxes converted: {total_boxes}")
    print(f"Skipped annotations: {len(skipped)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"YOLO configuration: {OUTPUT_DIR / 'data.yaml'}")

    if skipped:
        print("\nFirst skipped items:")

        for item in skipped[:20]:
            print(f"- {item}")

    if total_images == 0:
        raise RuntimeError("No images were converted successfully.")

    if skipped:
        print(
            "\nWARNING: Review skipped items before training. "
            "The generated dataset may be incomplete."
        )


if __name__ == "__main__":
    main()
