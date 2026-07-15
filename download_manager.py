from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

import requests


ProgressCallback = Callable[[int, int], None]
StatusCallback = Callable[[str], None]


class DownloadError(RuntimeError):
    """Error controlado durante una descarga."""


class DownloadManager:
    """Descarga archivos de forma segura y atómica."""

    def __init__(
        self,
        user_agent: str = "VoxelFly/0.3",
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
            }
        )

    def download(
        self,
        url: str,
        destination: Path,
        *,
        progress_callback: ProgressCallback | None = None,
        status_callback: StatusCallback | None = None,
        expected_sha1: str | None = None,
        timeout: int = 60,
    ) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = destination.with_suffix(
            destination.suffix + ".part"
        )

        if status_callback is not None:
            status_callback(
                f"Descargando {destination.name}..."
            )

        try:
            with self.session.get(
                url,
                stream=True,
                timeout=timeout,
            ) as response:
                response.raise_for_status()

                total = int(
                    response.headers.get(
                        "content-length",
                        0,
                    )
                )
                downloaded = 0
                sha1 = hashlib.sha1()

                with temporary.open("wb") as file:
                    for chunk in response.iter_content(
                        chunk_size=1024 * 128
                    ):
                        if not chunk:
                            continue

                        file.write(chunk)
                        sha1.update(chunk)
                        downloaded += len(chunk)

                        if progress_callback is not None:
                            progress_callback(
                                downloaded,
                                total,
                            )

        except (requests.RequestException, OSError) as error:
            temporary.unlink(missing_ok=True)
            raise DownloadError(
                f"No se pudo descargar el archivo: {error}"
            ) from error

        if expected_sha1:
            actual_sha1 = sha1.hexdigest().lower()

            if actual_sha1 != expected_sha1.lower():
                temporary.unlink(missing_ok=True)
                raise DownloadError(
                    "La verificación SHA-1 del archivo falló."
                )

        temporary.replace(destination)

        if status_callback is not None:
            status_callback(
                f"Descarga terminada: {destination.name}"
            )

        return destination 