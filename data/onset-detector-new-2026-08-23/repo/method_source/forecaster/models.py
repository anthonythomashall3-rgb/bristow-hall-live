"""Small, deterministic probability models and training-only calibration."""

import dataclasses
from typing import Any, Dict

import numpy as np


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    result = np.empty_like(values)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponential = np.exp(values[~positive])
    result[~positive] = exponential / (1.0 + exponential)
    return np.clip(result, 1e-9, 1.0 - 1e-9)


@dataclasses.dataclass(frozen=True)
class LogisticFit:
    intercept: float
    coefficients: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    l2: float
    positive_weight: float

    def predict_proba(self, values: np.ndarray) -> np.ndarray:
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        standardized = (matrix - self.means) / self.scales
        return _sigmoid(self.intercept + standardized @ self.coefficients)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "intercept": float(self.intercept),
            "coefficients": [float(value) for value in self.coefficients],
            "means": [float(value) for value in self.means],
            "scales": [float(value) for value in self.scales],
            "l2": float(self.l2),
            "positive_weight": float(self.positive_weight),
        }


def fit_logistic(
    values: np.ndarray,
    labels: np.ndarray,
    l2: float = 1.0,
    positive_weight: float = 1.0,
    iterations: int = 80,
) -> LogisticFit:
    matrix = np.asarray(values, dtype=float)
    target = np.asarray(labels, dtype=float)
    if matrix.ndim != 2 or len(matrix) != len(target) or len(target) == 0:
        raise ValueError("invalid logistic training arrays")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(target)):
        raise ValueError("logistic training arrays must be finite")
    means = matrix.mean(axis=0)
    scales = matrix.std(axis=0)
    scales = np.where(scales < 1e-9, 1.0, scales)
    standardized = (matrix - means) / scales
    design = np.column_stack([np.ones(len(matrix)), standardized])
    prevalence = np.clip(target.mean(), 1e-6, 1.0 - 1e-6)
    beta = np.zeros(design.shape[1])
    beta[0] = np.log(prevalence / (1.0 - prevalence))
    sample_weight = np.where(target > 0.5, positive_weight, 1.0)
    penalty = np.eye(design.shape[1]) * l2
    penalty[0, 0] = 0.0
    for _ in range(iterations):
        probability = _sigmoid(design @ beta)
        gradient = design.T @ (sample_weight * (target - probability)) - penalty @ beta
        curvature = sample_weight * probability * (1.0 - probability)
        hessian = design.T @ (design * curvature[:, None]) + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        beta += step
        if float(np.max(np.abs(step))) < 1e-9:
            break
    return LogisticFit(
        intercept=float(beta[0]),
        coefficients=beta[1:].copy(),
        means=means.copy(),
        scales=scales.copy(),
        l2=float(l2),
        positive_weight=float(positive_weight),
    )


@dataclasses.dataclass(frozen=True)
class PlattCalibrator:
    model: LogisticFit

    @staticmethod
    def _logit(probabilities: np.ndarray) -> np.ndarray:
        clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
        return np.log(clipped / (1.0 - clipped)).reshape(-1, 1)

    @classmethod
    def fit(cls, probabilities: np.ndarray, labels: np.ndarray) -> "PlattCalibrator":
        return cls(
            fit_logistic(
                cls._logit(probabilities),
                np.asarray(labels, dtype=float),
                l2=0.1,
                positive_weight=1.0,
            )
        )

    def transform(self, probabilities: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(self._logit(probabilities))

    def as_dict(self) -> Dict[str, Any]:
        return {"method": "platt", "model": self.model.as_dict()}


@dataclasses.dataclass(frozen=True)
class IdentityCalibrator:
    def transform(self, probabilities: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1.0 - 1e-9)

    def as_dict(self) -> Dict[str, str]:
        return {"method": "none"}
