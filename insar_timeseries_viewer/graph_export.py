# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Utilitários de exportação e marca d'água para os gráficos InSAR."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import numpy as np
from matplotlib.image import imread
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from .i18n import tr


VALID_FORMATS = {"png", "svg", "pdf"}
VALID_WATERMARK_POSITIONS = {
    "center",
    "lower_right",
    "lower_left",
    "upper_right",
    "upper_left",
}


@lru_cache(maxsize=1)
def load_watermark_image():
    """Load the bundled generic icon and make near-white pixels transparent."""
    path = Path(__file__).with_name("icon.png")
    if not path.exists():
        return None

    image = np.array(imread(str(path)), copy=True)
    if image.ndim != 3 or image.shape[2] < 3:
        return image

    # The generic icon has a near-white background. Remove only near-white
    # pixels so the remaining artwork can be used as a subtle watermark.
    rgb = image[..., :3]
    threshold = 0.97 if np.issubdtype(image.dtype, np.floating) else 247
    white_mask = np.min(rgb, axis=2) >= threshold

    if image.shape[2] == 3:
        alpha = np.ones(image.shape[:2], dtype=image.dtype)
        if not np.issubdtype(image.dtype, np.floating):
            alpha *= 255
        image = np.dstack((image, alpha))

    image[..., 3][white_mask] = 0
    return image


def apply_watermark(
    figure,
    *,
    enabled: bool,
    opacity: float,
    position: str,
    scale: float,
) -> bool:
    """Adiciona o logo a cada eixo visível da figura.

    Retorna ``True`` quando a imagem foi aplicada. A marca é desenhada abaixo
    das séries e acima do fundo do eixo.
    """
    if not enabled:
        return False

    image = load_watermark_image()
    if image is None:
        return False

    position = position if position in VALID_WATERMARK_POSITIONS else "center"
    xy, alignment = _position_spec(position)
    opacity = min(max(float(opacity), 0.01), 1.0)
    scale = min(max(float(scale), 0.10), 1.50)

    applied = False
    for axes in figure.axes:
        if not axes.get_visible() or not axes.axison:
            continue
        display_image = np.array(image, copy=True)
        if display_image.ndim == 3 and display_image.shape[2] >= 4:
            if np.issubdtype(display_image.dtype, np.floating):
                display_image[..., 3] *= opacity
            else:
                display_image[..., 3] = (
                    display_image[..., 3].astype(float) * opacity
                ).astype(display_image.dtype)
        image_box = OffsetImage(
            display_image,
            zoom=scale,
            interpolation="bilinear",
        )
        artist = AnnotationBbox(
            image_box,
            xy,
            xycoords="axes fraction",
            box_alignment=alignment,
            frameon=False,
            pad=0.0,
            annotation_clip=True,
            zorder=0.15,
        )
        axes.add_artist(artist)
        applied = True
    return applied


def add_export_header(figure, text: str, *, enabled: bool) -> None:
    """Adiciona o cabeçalho de dados na região superior da figura."""
    if not enabled or not text:
        return
    figure.suptitle(
        text,
        x=0.5,
        y=0.995,
        ha="center",
        va="top",
        fontsize=10.5,
        fontweight="semibold",
        wrap=True,
    )


def save_figure(
    figure,
    path: Path,
    *,
    file_format: str,
    dpi: int,
    transparent: bool,
) -> None:
    """Salva uma figura em PNG, SVG ou PDF."""
    file_format = file_format.lower()
    if file_format not in VALID_FORMATS:
        raise ValueError(tr("Formato de exportação não suportado: {format}", format=file_format))

    figure.savefig(
        str(path),
        format=file_format,
        dpi=int(dpi),
        transparent=bool(transparent),
        facecolor="none" if transparent else "white",
        edgecolor="none",
        bbox_inches="tight",
        pad_inches=0.14,
        metadata={"Creator": "InSAR Time Series Viewer"},
    )


def sanitize_filename(value: object, fallback: str = "grafico_insar") -> str:
    """Produz um nome de arquivo seguro para Windows."""
    text = str(value or "").strip()
    invalid_chars = '<>:"/\\|?*'
    text = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip(" ._")
    return text[:150] or fallback


def ensure_extension(path: Path, file_format: str) -> Path:
    suffix = f".{file_format.lower()}"
    return path if path.suffix.lower() == suffix else path.with_suffix(suffix)


def available_path(path: Path) -> Path:
    """Evita sobrescrever silenciosamente arquivos em exportações em lote."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _position_spec(position: str):
    positions = {
        "center": ((0.5, 0.5), (0.5, 0.5)),
        "lower_right": ((0.98, 0.03), (1.0, 0.0)),
        "lower_left": ((0.02, 0.03), (0.0, 0.0)),
        "upper_right": ((0.98, 0.97), (1.0, 1.0)),
        "upper_left": ((0.02, 0.97), (0.0, 1.0)),
    }
    return positions[position]
