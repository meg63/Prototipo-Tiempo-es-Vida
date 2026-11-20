"""CNN 1D de CuidaCor (SRS MOD-01).

Copia de inferencia de `cuidaecg.model` (repositorio del modelo). La arquitectura
debe coincidir con `artefactos/inference_config.json` para cargar los pesos.
"""

from __future__ import annotations

from typing import Any

from torch import nn


class ECGCNN1D(nn.Module):
    """[B, 12, T] -> logits [B, 5]. Convoluciones con stride 1 y padding k // 2."""

    def __init__(
        self,
        in_channels: int = 12,
        n_classes: int = 5,
        channels=(32, 64, 128),
        kernel_sizes=(7, 5, 3),
        pool_sizes=(2, 2, 0),
        dropout: float = 0.2,
        name: str = "ECGCNN1D",
    ):
        super().__init__()
        layers: list[nn.Module] = []
        prev = in_channels
        for ch, k, p in zip(channels, kernel_sizes, pool_sizes):
            layers += [
                nn.Conv1d(prev, ch, kernel_size=k, stride=1, padding=k // 2),
                nn.BatchNorm1d(ch),
                nn.ReLU(inplace=True),
            ]
            if p:
                layers.append(nn.MaxPool1d(p))
            prev = ch
        self.features = nn.Sequential(*layers)
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(start_dim=1),
            nn.Dropout(dropout),
            nn.Linear(prev, n_classes),
        )

    def forward(self, x):
        return self.head(self.features(x))


def construir_red(arquitectura: dict[str, Any]) -> ECGCNN1D:
    cfg = dict(arquitectura)
    if cfg.get("name", "ECGCNN1D") != "ECGCNN1D":
        raise ValueError(f"Arquitectura desconocida: {cfg.get('name')}")
    return ECGCNN1D(**cfg)
