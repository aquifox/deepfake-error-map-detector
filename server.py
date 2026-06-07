import argparse
import io
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
import torch
import uvicorn

from inference import load_detector, predict_pil_image


APP_TITLE = "Deepfake Error Map Detector Local Server"
DEFAULT_SAFETY_NOTE = "AI analysis result for reference only; not legal or factual proof."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--weights",
        default=os.getenv(
            "DETECTOR_FULL_WEIGHTS", "models/deepfake_detector_full.pth"
        ),
        help="Full checkpoint path. Used first when the file exists.",
    )
    parser.add_argument(
        "--ae-weights",
        default=os.getenv("DETECTOR_AE_WEIGHTS", "models/ae_weights.pth"),
        help="Fallback path to ae_weights.pth.",
    )
    parser.add_argument(
        "--classifier-weights",
        default=os.getenv(
            "DETECTOR_CLASSIFIER_WEIGHTS", "models/classifier_weights.pth"
        ),
        help="Fallback path to classifier_weights.pth.",
    )
    parser.add_argument(
        "--label-map",
        default=os.getenv("DETECTOR_LABEL_MAP", "models/label_map.json"),
        help="Path to label_map.json.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=int(os.getenv("DETECTOR_IMAGE_SIZE", "224")),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.getenv("DETECTOR_THRESHOLD", "0.5")),
    )
    parser.add_argument(
        "--device",
        default=os.getenv(
            "DETECTOR_DEVICE", "cuda" if torch.cuda.is_available() else "cpu"
        ),
        choices=["cuda", "cpu"],
    )
    parser.add_argument(
        "--host",
        default=os.getenv("DETECTOR_HOST", "127.0.0.1"),
        help="Bind host. Keep 127.0.0.1 for privacy.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("DETECTOR_PORT", "8000")),
    )
    parser.add_argument(
        "--max-image-mb",
        type=float,
        default=float(os.getenv("DETECTOR_MAX_IMAGE_MB", "12")),
    )
    return parser.parse_args()


def resolve_full_weights(path_value: str) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    return str(path) if path.exists() else None


def create_app(args: argparse.Namespace) -> FastAPI:
    device = torch.device(args.device)
    full_weights = resolve_full_weights(args.weights)
    ae, classifier, label_map, checkpoint_meta = load_detector(
        full_weights=full_weights,
        ae_weights=args.ae_weights,
        classifier_weights=args.classifier_weights,
        label_map_path=args.label_map,
        device=device,
    )
    image_size = int(checkpoint_meta.get("image_size") or args.image_size)
    fake_threshold = float(checkpoint_meta.get("fake_threshold") or args.threshold)
    max_bytes = int(args.max_image_mb * 1024 * 1024)

    app = FastAPI(title=APP_TITLE)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_origin_regex=r"chrome-extension://.*",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    runtime: Dict[str, Any] = {
        "device": str(device),
        "image_size": image_size,
        "fake_threshold": fake_threshold,
        "full_weights": full_weights,
        "ae_weights": args.ae_weights,
        "classifier_weights": args.classifier_weights,
        "max_image_mb": args.max_image_mb,
    }

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ready",
            "model": "cnn_autoencoder_error_map_resnet18",
            "runtime": runtime,
            "note": DEFAULT_SAFETY_NOTE,
        }

    @app.post("/predict")
    async def predict(file: UploadFile = File(...)) -> Dict[str, Any]:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty image upload.")
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image is too large. Limit is {args.max_image_mb} MB.",
            )

        try:
            with Image.open(io.BytesIO(content)) as image:
                result = predict_pil_image(
                    image=image,
                    ae=ae,
                    classifier=classifier,
                    label_map=label_map,
                    device=device,
                    image_size=image_size,
                    fake_threshold=fake_threshold,
                )
        except UnidentifiedImageError as exc:
            raise HTTPException(
                status_code=400, detail="Unsupported or corrupted image."
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        result["filename"] = file.filename
        return result

    return app


def main() -> None:
    args = parse_args()
    app = create_app(args)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
