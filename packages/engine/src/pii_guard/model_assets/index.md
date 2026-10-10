# Required face model assets

- `face_detection_yunet_2023mar.onnx`: CPU YuNet, 232589 bytes; SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`. Runtime rejects missing/corrupt models.
- `YUNET_LICENSE.txt`: model MIT license.
- `index.md`: provenance.

Pinned upstream: https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet .

YuNet uses a conservative 0.35 threshold to cover profile/candid examples; extra masks/false positives are possible. Detection is probabilistic, not proof that an arbitrary photo has no face.
