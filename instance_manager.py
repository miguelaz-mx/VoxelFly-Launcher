from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from settings import get_app_directory


@dataclass
class InstanceInfo:
    """Información guardada dentro de cada instancia."""

    id: str
    name: str
    loader: str
    minecraft_version: str
    installed_version: str = ""

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "InstanceInfo":
        valid_fields = cls.__dataclass_fields__

        filtered = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        return cls(**filtered)


class InstanceManager:
    """Crea y administra instancias independientes."""

    SUBDIRECTORIES = (
        "mods",
        "resourcepacks",
        "shaderpacks",
        "saves",
        "screenshots",
        "config",
    )

    def __init__(
        self,
        instances_directory: Path | None = None,
    ) -> None:
        self.instances_directory = (
            Path(instances_directory)
            if instances_directory is not None
            else get_app_directory() / "instances"
        )

        self.instances_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def instance_path(
        self,
        instance_id: str,
    ) -> Path:
        return self.instances_directory / instance_id

    def metadata_path(
        self,
        instance_id: str,
    ) -> Path:
        return self.instance_path(instance_id) / "instance.json"

    def create_instance(
        self,
        info: InstanceInfo,
    ) -> Path:
        directory = self.instance_path(info.id)
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for name in self.SUBDIRECTORIES:
            (directory / name).mkdir(
                parents=True,
                exist_ok=True,
            )

        self.save_info(info)
        return directory

    def save_info(
        self,
        info: InstanceInfo,
    ) -> None:
        path = self.metadata_path(info.id)
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
                asdict(info),
                file,
                ensure_ascii=False,
                indent=4,
            )

        temporary.replace(path)

    def load_info(
        self,
        instance_id: str,
    ) -> InstanceInfo | None:
        path = self.metadata_path(instance_id)

        if not path.exists():
            return None

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        try:
            return InstanceInfo.from_dict(data)
        except TypeError:
            return None

    def list_instances(self) -> list[InstanceInfo]:
        instances: list[InstanceInfo] = []

        for directory in self.instances_directory.iterdir():
            if not directory.is_dir():
                continue

            info = self.load_info(directory.name)

            if info is not None:
                instances.append(info)

        return instances

    def delete_instance(
        self,
        instance_id: str,
    ) -> bool:
        directory = self.instance_path(instance_id)

        if not directory.exists():
            return False

        shutil.rmtree(directory)
        return True

    def mods_directory(
        self,
        instance_id: str,
    ) -> Path:
        directory = self.instance_path(instance_id) / "mods"
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        return directory