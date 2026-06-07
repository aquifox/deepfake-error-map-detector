# Model Artifacts

이 저장소는 GitHub 배포를 위해 `.pth` 모델 가중치를 포함하지 않습니다.

## 필요한 파일

권장 방식:

```text
models/deepfake_detector_full.pth
models/label_map.json
```

대체 방식:

```text
models/ae_weights.pth
models/classifier_weights.pth
models/label_map.json
```

## 배포 권장 방식

- GitHub Releases에 `deepfake_detector_artifacts.zip` 업로드
- Google Drive 공유 링크 제공
- Hugging Face Hub에 모델 파일 업로드

GitHub 저장소 본문에는 큰 `.pth` 파일을 직접 커밋하지 않는 것을 권장합니다.

## 모델 성능 예시

현재 학습 결과 예시:

```text
test accuracy: 0.8974
test f1-score: 0.8966
fake precision: 0.8445
fake recall: 0.9760
confusion matrix:
[[4426,  987],
 [ 132, 5360]]
```

이 성능은 사용한 데이터셋 기준입니다. 다른 웹 이미지, 다른 생성 모델, 다른 압축 환경에서는 달라질 수 있습니다.
