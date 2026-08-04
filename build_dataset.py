"""Build a YOLO dataset from locally-extracted frames using yolo11n.pt on the GPU.

Pipeline:
  1. Run YOLOv11 inference (device 0) over F:/flowsense_dataset/frames -> YOLO txt labels.
  2. Split frames + labels 90/10 into images/{train,val} + labels/{train,val}.
  3. Write F:/flowsense_dataset/data.yaml (class names taken from the model, so IDs
     stay aligned with the pretrained weights -- no hand-typed list to get wrong).
"""
from pathlib import Path
import shutil
import random

from ultralytics import YOLO

# NOTE: python here is Windows-native, so use drive-letter paths (F:/...), not
# Unix-style (/f/...), which Windows python resolves to C:\f\...
FRAMES = Path("F:/flowsense_dataset/frames")
ROOT = Path("F:/flowsense_dataset")
PREDS = ROOT / "preds"
CONF = 0.35
SEED = 42
SPLIT = 0.9


def torch_ok() -> bool:
    import torch
    return torch.cuda.is_available()


def main():
    if not FRAMES.exists():
        raise SystemExit(f"Frames dir missing: {FRAMES}. Run frame extraction first.")
    if not list(FRAMES.glob("*.jpg")):
        raise SystemExit(f"No frames found in {FRAMES}.")

    if not torch_ok():
        raise SystemExit("CUDA torch not available - install torch with cu126 first.")

    model = YOLO("yolo11n.pt")
    # Derive class names from the loaded model so IDs always match the weights.
    names = [model.names[i] for i in range(len(model.names))]

    # Clean any previous prediction output so we never pick up stale labels.
    if PREDS.exists():
        shutil.rmtree(PREDS)

    model.predict(
        source=str(FRAMES),
        device=0,
        conf=CONF,
        save_txt=True,
        save_conf=False,
        exist_ok=True,
        project=str(PREDS),
        name="detect",
        verbose=False,
    )

    label_files = {p.stem: p for p in PREDS.rglob("*.txt")}
    if not label_files:
        raise SystemExit("No label files produced - check CUDA / model load.")

    frames = sorted(FRAMES.glob("*.jpg"))
    random.seed(SEED)
    random.shuffle(frames)
    split = int(SPLIT * len(frames))
    splits = {"train": frames[:split], "val": frames[split:]}

    for split_name, fset in splits.items():
        img_dir = ROOT / "images" / split_name
        lbl_dir = ROOT / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)
        for img in fset:
            shutil.copy(img, img_dir / img.name)
            lbl = label_files.get(img.stem)
            if lbl is not None:
                shutil.copy(lbl, lbl_dir / lbl.name)
            # Frames with no detections simply have no label file (background).

    names_block = "[\n" + ",\n".join(f"  '{n}'" for n in names) + "\n]"
    # as_posix() -> forward slashes so the YAML path is portable on Windows.
    data_yaml = (
        f"path: {ROOT.as_posix()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: {len(names)}\n"
        f"names: {names_block}\n"
    )
    (ROOT / "data.yaml").write_text(data_yaml, encoding="utf-8")

    print(f"DATASET READY: {len(splits['train'])} train / {len(splits['val'])} val frames")
    print(f"data.yaml -> {ROOT / 'data.yaml'}")


if __name__ == "__main__":
    main()
