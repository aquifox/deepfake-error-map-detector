from pathlib import Path
import sys

from PIL import Image
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from inference import load_detector, predict_pil_image


def main() -> None:
    if Path.cwd() != REPO_ROOT:
        print(f"Run from repository root for predictable relative paths: {REPO_ROOT}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ae, classifier, label_map, _ = load_detector(
        full_weights=str(REPO_ROOT / "models" / "deepfake_detector_full.pth"),
        ae_weights=None,
        classifier_weights=None,
        label_map_path=str(REPO_ROOT / "models" / "label_map.json"),
        device=device,
    )
    image = Image.new("RGB", (224, 224), color=(128, 96, 64))
    result = predict_pil_image(image, ae, classifier, label_map, device)
    print(result)


if __name__ == "__main__":
    main()
