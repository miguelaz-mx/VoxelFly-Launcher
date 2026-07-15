from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


APP_NAME = "VoxelFly 2.0"


def get_cache_directory() -> Path:
    appdata = os.environ.get("APPDATA")

    if appdata:
        directory = Path(appdata) / APP_NAME / "cache"
    else:
        directory = Path.home() / ".voxelfly" / "cache"

    directory.mkdir(parents=True, exist_ok=True)
    return directory


class CacheManager:
    """Administra caché JSON e imágenes descargadas."""

    def __init__(self, cache_directory: Path | None = None) -> None:
        self.cache_directory = (
            Path(cache_directory)
            if cache_directory is not None
            else get_cache_directory()
        )

        self.json_directory = self.cache_directory / "json"
        self.image_directory = self.cache_directory / "images"

        self.json_directory.mkdir(parents=True, exist_ok=True)
        self.image_directory.mkdir(parents=True, exist_ok=True)

    def _safe_key(self, key: str) -> str:
        return hashlib.sha256(
            key.encode("utf-8")
        ).hexdigest()

    def json_path(self, key: str) -> Path:
        return self.json_directory / f"{self._safe_key(key)}.json"

    def image_path(
        self,
        key: str,
        extension: str = ".png",
    ) -> Path:
        if not extension.startswith("."):
            extension = f".{extension}"

        return (
            self.image_directory
            / f"{self._safe_key(key)}{extension}"
        )

    def set_json(
        self,
        key: str,
        value: Any,
    ) -> None:
        path = self.json_path(key)
        temporary = path.with_suffix(".json.tmp")

        payload = {
            "saved_at": time.time(),
            "value": value,
        }

        with temporary.open("w", encoding="utf-8") as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temporary.replace(path)

    def get_json(
        self,
        key: str,
        max_age_seconds: int | None = None,
    ) -> Any | None:
        path = self.json_path(key)

        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        saved_at = float(payload.get("saved_at", 0))

        if (
            max_age_seconds is not None
            and time.time() - saved_at > max_age_seconds
        ):
            path.unlink(missing_ok=True)
            return None

        return payload.get("value")

    def clear(self) -> None:
        for directory in (
            self.json_directory,
            self.image_directory,
        ):
            for path in directory.iterdir():
                if path.is_file():
                    path.unlink(missing_ok=True)