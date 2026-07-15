from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


APP_NAME = "VoxelFly 2.0"


def get_app_directory() -> Path:
    """Devuelve la carpeta principal de datos de VoxelFly."""
    appdata = os.environ.get("APPDATA")

    if appdata:
        directory = Path(appdata) / APP_NAME
    else:
        directory = Path.home() / ".voxelfly"

    directory.mkdir(parents=True, exist_ok=True)
    return directory


@dataclass
class AppSettings:
    """Configuración global del launcher."""

    default_ram_mb: int = 4096
    keep_launcher_open: bool = True
    close_launcher_on_game_start: bool = False
    java_path: str = ""
    theme: str = "dark"
    language: str = "es"
    last_loader: str = "Vanilla"
    last_version: str = ""
    last_profile_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        valid_fields = cls.__dataclass_fields__
        filtered = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }
        return cls(**filtered)


class SettingsManager:
    """Carga y guarda la configuración en JSON."""

    def __init__(self, settings_file: Path | None = None) -> None:
        self.app_directory = get_app_directory()
        self.settings_file = (
            Path(settings_file)
            if settings_file is not None
            else self.app_directory / "settings.json"
        )

    def load(self) -> AppSettings:
        if not self.settings_file.exists():
            settings = AppSettings()
            self.save(settings)
            return settings

        try:
            with self.settings_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return AppSettings()

        if not isinstance(data, dict):
            return AppSettings()

        return AppSettings.from_dict(data)

    def save(self, settings: AppSettings) -> None:
        self.settings_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.settings_file.with_suffix(".json.tmp")

        with temporary.open("w", encoding="utf-8") as file:
            json.dump(
                asdict(settings),
                file,
                ensure_ascii=False,
                indent=4,
            )

        temporary.replace(self.settings_file)

    def update(self, **changes: Any) -> AppSettings:
        settings = self.load()

        for key, value in changes.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.save(settings)
        return settings