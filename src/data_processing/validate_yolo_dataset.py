from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_YAML = PROJECT_ROOT / "data" / "processed" / "potholes" / "data.yaml"

def main():
    with DATA_YAML.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    dataset_root = Path(config["path"])
    class_names = config["names"]
    expected_class_ids = {int(class_id) for class_id in class_names}

    total_images = 0
    total_boxes = 0
    issues = []

    for split in ("train", "val", "test"):
        image_dir = dataset_root / config[split]
        label_dir = dataset_root / "labels" / split

        if not image_dir.is_dir():
            issues.append(f"{split}: missing image directory: {image_dir}")
            continue

        if not label_dir.is_dir():
            issues.append(f"{split}: missing label directory: {label_dir}")
            continue

        images = sorted(
            path for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {
                ".jpg", ".jpeg", ".png", ".bmp", ".webp"
            }
        )

        labels = {path.stem: path for path in label_dir.glob("*.txt")}
        image_stems = {path.stem for path in images}

        missing_labels = image_stems - set(labels)
        orphan_labels = set(labels) - image_stems

        for stem in sorted(missing_labels):
            issues.append(f"{split}: image has no label file: {stem}")

        for stem in sorted(orphan_labels):
            issues.append(f"{split}: label has no matching image: {stem}")

        split_boxes = 0

        for image_path in images:
            label_path = labels.get(image_path.stem)

            if label_path is None:
                continue

            try:
                lines = label_path.read_text(encoding="utf-8").splitlines()

                for line_number, line in enumerate(lines, start=1):
                    parts = line.split()

                    if len(parts) != 5:
                        issues.append(
                            f"{label_path.name}:{line_number}: "
                            "expected 5 values per bounding box"
                        )
                        continue

                    try:
                        class_id = int(parts[0])
                        x_center, y_center, width, height = map(
                            float, parts[1:]
                        )
                    except ValueError:
                        issues.append(
                            f"{label_path.name}:{line_number}: "
                            "non-numeric label value"
                        )
                        continue

                    if class_id not in expected_class_ids:
                        issues.append(
                            f"{label_path.name}:{line_number}: "
                            f"unknown class ID {class_id}"
                        )

                    if not all(
                        0 <= value <= 1
                        for value in (x_center, y_center, width, height)
                    ):
                        issues.append(
                            f"{label_path.name}:{line_number}: "
                            "coordinates must be normalized between 0 and 1"
                        )

                    if width <= 0 or height <= 0:
                        issues.append(
                            f"{label_path.name}:{line_number}: "
                            "box width and height must be positive"
                        )

                    if (
                        x_center - width / 2 < -1e-6
                        or y_center - height / 2 < -1e-6
                        or x_center + width / 2 > 1 + 1e-6
                        or y_center + height / 2 > 1 + 1e-6
                    ):
                        issues.append(
                            f"{label_path.name}:{line_number}: "
                            "bounding box extends outside the image"
                        )

                    split_boxes += 1

            except OSError as error:
                issues.append(f"{label_path.name}: unable to read label: {error}")

        total_images += len(images)
        total_boxes += split_boxes

        print(
            f"{split.upper()}: "
            f"{len(images)} images, "
            f"{len(labels)} label files, "
            f"{split_boxes} bounding boxes"
        )

    print("\n========== INTEGRITY REPORT ==========")
    print(f"Total images: {total_images}")
    print(f"Total bounding boxes: {total_boxes}")
    print(f"Issues found: {len(issues)}")

    for issue in issues[:50]:
        print(f"- {issue}")

    if len(issues) > 50:
        print(f"... and {len(issues) - 50} more issues")

    if not issues:
        print("SUCCESS: No structural or label-format issues found.")

if __name__ == "__main__":
    main()
    