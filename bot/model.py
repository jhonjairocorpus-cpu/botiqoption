import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple


@dataclass
class LogisticModel:
    weights: List[float]
    bias: float
    means: List[float]
    scales: List[float]

    def predict_proba(self, features: Sequence[float]) -> float:
        normalized = [(value - mean) / scale for value, mean, scale in zip(features, self.means, self.scales)]
        score = self.bias + sum(weight * value for weight, value in zip(self.weights, normalized))
        return 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, score))))

    def save(self, path: str) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "weights": self.weights,
                    "bias": self.bias,
                    "means": self.means,
                    "scales": self.scales,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str) -> "LogisticModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            weights=[float(value) for value in payload["weights"]],
            bias=float(payload["bias"]),
            means=[float(value) for value in payload["means"]],
            scales=[float(value) for value in payload["scales"]],
        )


def train_logistic_regression(
    samples: List[Tuple[List[float], int]],
    learning_rate: float = 0.05,
    epochs: int = 600,
    l2: float = 0.001,
) -> LogisticModel:
    if not samples:
        raise ValueError("No hay muestras suficientes para entrenar.")

    feature_count = len(samples[0][0])
    means = []
    scales = []
    for feature_index in range(feature_count):
        column = [features[feature_index] for features, _ in samples]
        mean = sum(column) / len(column)
        variance = sum((value - mean) ** 2 for value in column) / len(column)
        scale = variance ** 0.5 or 1.0
        means.append(mean)
        scales.append(scale)

    weights = [0.0] * feature_count
    bias = 0.0

    for _ in range(epochs):
        for raw_features, label in samples:
            features = [(value - mean) / scale for value, mean, scale in zip(raw_features, means, scales)]
            score = bias + sum(weight * value for weight, value in zip(weights, features))
            prediction = 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, score))))
            error = prediction - label

            for index, value in enumerate(features):
                weights[index] -= learning_rate * (error * value + l2 * weights[index])
            bias -= learning_rate * error

    return LogisticModel(weights=weights, bias=bias, means=means, scales=scales)
