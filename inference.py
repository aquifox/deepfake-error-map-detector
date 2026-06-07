import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image, UnidentifiedImageError
import torch
import torch.nn as nn
from torchvision import models, transforms


DEFAULT_LABEL_MAP = {
    "real": 0,
    "fake": 1,
    "id_to_label": {"0": "real", "1": "fake"},
}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
SAFETY_NOTE = "AI analysis result for reference only; not legal or factual proof."


class ConvAutoEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(32, 3, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


def build_classifier(num_classes: int = 2) -> nn.Module:
    classifier = models.resnet18(weights=None)
    classifier.fc = nn.Linear(classifier.fc.in_features, num_classes)
    return classifier


def normalize_error_map(error_map: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor(IMAGENET_MEAN, device=error_map.device).view(1, 3, 1, 1)
    std = torch.tensor(IMAGENET_STD, device=error_map.device).view(1, 3, 1, 1)
    return (error_map - mean) / std


def load_label_map(label_map_path: Optional[str]) -> Dict[str, Any]:
    if not label_map_path:
        return DEFAULT_LABEL_MAP
    path = Path(label_map_path)
    if not path.exists():
        return DEFAULT_LABEL_MAP
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "id_to_label" not in data:
        data["id_to_label"] = {str(v): k for k, v in data.items() if isinstance(v, int)}
    return data


def get_class_indices(label_map: Dict[str, Any]) -> Tuple[int, int]:
    if "real" in label_map and "fake" in label_map:
        return int(label_map["real"]), int(label_map["fake"])

    id_to_label = label_map.get("id_to_label", {})
    real_idx = None
    fake_idx = None
    for idx, label in id_to_label.items():
        normalized = str(label).lower()
        if normalized == "real":
            real_idx = int(idx)
        if normalized == "fake":
            fake_idx = int(idx)
    if real_idx is None or fake_idx is None:
        raise ValueError("label_map.json must define real and fake class indices.")
    return real_idx, fake_idx


def load_detector(
    full_weights: Optional[str],
    ae_weights: Optional[str],
    classifier_weights: Optional[str],
    label_map_path: Optional[str],
    device: torch.device,
) -> Tuple[nn.Module, nn.Module, Dict[str, Any], Dict[str, Any]]:
    label_map = load_label_map(label_map_path)
    ae = ConvAutoEncoder().to(device)
    classifier = build_classifier(num_classes=2).to(device)
    checkpoint_meta: Dict[str, Any] = {}

    if full_weights:
        full_path = Path(full_weights)
        if not full_path.exists():
            raise FileNotFoundError(f"Full checkpoint not found: {full_path}")
        checkpoint = torch.load(full_path, map_location=device)
        if isinstance(checkpoint, dict) and "ae_state_dict" in checkpoint:
            ae.load_state_dict(checkpoint["ae_state_dict"])
            classifier.load_state_dict(checkpoint["classifier_state_dict"])
            label_map = checkpoint.get("label_map", label_map)
            checkpoint_meta = {
                "image_size": checkpoint.get("image_size"),
                "fake_threshold": checkpoint.get("fake_threshold"),
                "config": checkpoint.get("config", {}),
            }
        else:
            raise ValueError(
                "Full checkpoint must contain ae_state_dict and classifier_state_dict."
            )
    else:
        if not ae_weights or not classifier_weights:
            raise ValueError(
                "Provide either --weights or both --ae-weights and --classifier-weights."
            )
        ae_path = Path(ae_weights)
        classifier_path = Path(classifier_weights)
        if not ae_path.exists():
            raise FileNotFoundError(f"AE weights not found: {ae_path}")
        if not classifier_path.exists():
            raise FileNotFoundError(f"Classifier weights not found: {classifier_path}")
        ae.load_state_dict(torch.load(ae_path, map_location=device))
        classifier.load_state_dict(torch.load(classifier_path, map_location=device))

    ae.eval()
    classifier.eval()
    return ae, classifier, label_map, checkpoint_meta


def build_preprocess(image_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
        ]
    )


def predict_pil_image(
    image: Image.Image,
    ae: nn.Module,
    classifier: nn.Module,
    label_map: Dict[str, Any],
    device: torch.device,
    image_size: int = 224,
    fake_threshold: float = 0.5,
) -> Dict[str, Any]:
    real_idx, fake_idx = get_class_indices(label_map)
    preprocess = build_preprocess(image_size)
    image = image.convert("RGB")
    x = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        reconstruction = ae(x).clamp(0.0, 1.0)
        error_map = torch.abs(x - reconstruction)
        logits = classifier(normalize_error_map(error_map))
        probabilities = torch.softmax(logits, dim=1)[0].detach().cpu()

    real_probability = float(probabilities[real_idx].item())
    fake_probability = float(probabilities[fake_idx].item())
    label = "fake" if fake_probability >= fake_threshold else "real"
    confidence = fake_probability if label == "fake" else real_probability

    return {
        "label": label,
        "confidence": confidence,
        "real_probability": real_probability,
        "fake_probability": fake_probability,
        "fake_threshold": fake_threshold,
        "note": SAFETY_NOTE,
    }


def predict_image_path(
    image_path: str,
    ae: nn.Module,
    classifier: nn.Module,
    label_map: Dict[str, Any],
    device: torch.device,
    image_size: int = 224,
    fake_threshold: float = 0.5,
) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    try:
        with Image.open(path) as image:
            return predict_pil_image(
                image=image,
                ae=ae,
                classifier=classifier,
                label_map=label_map,
                device=device,
                image_size=image_size,
                fake_threshold=fake_threshold,
            )
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupted image: {path}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run CNN AutoEncoder Error Map + ResNet18 deepfake inference."
    )
    parser.add_argument("--image", required=True, help="Path to one image file.")
    parser.add_argument(
        "--weights",
        default="models/deepfake_detector_full.pth",
        help="Path to full checkpoint saved by the Colab notebook.",
    )
    parser.add_argument("--ae-weights", default=None, help="Path to ae_weights.pth.")
    parser.add_argument(
        "--classifier-weights",
        default=None,
        help="Path to classifier_weights.pth.",
    )
    parser.add_argument(
        "--label-map",
        default="models/label_map.json",
        help="Path to label_map.json.",
    )
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        choices=["cuda", "cpu"],
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = torch.device(args.device)
    use_full_weights = args.weights if args.weights and Path(args.weights).exists() else None
    ae, classifier, label_map, checkpoint_meta = load_detector(
        full_weights=use_full_weights,
        ae_weights=args.ae_weights,
        classifier_weights=args.classifier_weights,
        label_map_path=args.label_map,
        device=device,
    )
    image_size = int(checkpoint_meta.get("image_size") or args.image_size)
    fake_threshold = float(checkpoint_meta.get("fake_threshold") or args.threshold)
    result = predict_image_path(
        image_path=args.image,
        ae=ae,
        classifier=classifier,
        label_map=label_map,
        device=device,
        image_size=image_size,
        fake_threshold=fake_threshold,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
