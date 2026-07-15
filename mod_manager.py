from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from instance_manager import InstanceManager


@dataclass
class InstalledMod:
    """Metadatos básicos de un mod instalado."""

    project_id: str
    version_id: str
    name: str
    filename: str
    minecraft_version: str
    loader: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "InstalledMod":
        valid_fields = cls.__dataclass_fields__

        filtered = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        return cls(**filtered)


class ModManager:
    """Administra mods dentro de una instancia."""

    METADATA_FILE = "installed_mods.json"

    def __init__(
        self,
        instance_manager: InstanceManager,
    ) -> None:
        self.instance_manager = instance_manager

    def _metadata_path(
        self,
        instance_id: str,
    ) -> Path:
        return (
            self.instance_manager.instance_path(instance_id)
            / self.METADATA_FILE
        )

    def list_installed(
        self,
        instance_id: str,
    ) -> list[InstalledMod]:
        path = self._metadata_path(instance_id)

        if not path.exists():
            return []

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(data, list):
            return []

        mods: list[InstalledMod] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                mods.append(
                    InstalledMod.from_dict(item)
                )
            except TypeError:
                continue

        return mods

    def save_installed(
        self,
        instance_id: str,
        mods: list[InstalledMod],
    ) -> None:
        path = self._metadata_path(instance_id)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = path.with_suffix(".json.tmp")

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                [asdict(mod) for mod in mods],
                file,
                ensure_ascii=False,
                indent=4,
            )

        temporary.replace(path)

    def install_file(
        self,
        instance_id: str,
        source_file: Path,
        mod: InstalledMod,
    ) -> Path:
        source_file = Path(source_file)

        if not source_file.exists():
            raise FileNotFoundError(
                f"No existe el archivo: {source_file}"
            )

        mods_directory = (
            self.instance_manager.mods_directory(
                instance_id
            )
        )

        destination = mods_directory / mod.filename

        shutil.copy2(
            source_file,
            destination,
        )

        installed = self.list_installed(instance_id)

        installed = [
            current
            for current in installed
            if current.project_id != mod.project_id
        ]

        installed.append(mod)
        self.save_installed(
            instance_id,
            installed,
        )

        return destination

    def uninstall(
        self,
        instance_id: str,
        project_id: str,
    ) -> bool:
        installed = self.list_installed(instance_id)

        target = next(
            (
                mod
                for mod in installed
                if mod.project_id == project_id
            ),
            None,
        )

        if target is None:
            return False

        mod_file = (
            self.instance_manager.mods_directory(
                instance_id
            )
            / target.filename
        )

        mod_file.unlink(missing_ok=True)

        remaining = [
            mod
            for mod in installed
            if mod.project_id != project_id
        ]

        self.save_installed(
            instance_id,
            remaining,
        )

        return True

    def is_installed(
        self,
        instance_id: str,
        project_id: str,
    ) -> bool:
        return any(
            mod.project_id == project_id
            for mod in self.list_installed(instance_id)
        )