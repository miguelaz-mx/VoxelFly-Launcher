from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from settings import get_app_directory


@dataclass
class GameProfile:
    """Perfil guardado de Minecraft."""

    id: str
    name: str
    loader: str
    minecraft_version: str
    ram_mb: int = 4096
    instance_id: str = ""
    java_path: str = ""
    jvm_arguments: list[str] = field(
        default_factory=list
    )
    favorite: bool = False

    @classmethod
    def create(
        cls,
        name: str,
        loader: str,
        minecraft_version: str,
        ram_mb: int = 4096,
    ) -> "GameProfile":
        profile_id = uuid.uuid4().hex

        return cls(
            id=profile_id,
            name=name.strip() or "Nuevo perfil",
            loader=loader,
            minecraft_version=minecraft_version,
            ram_mb=ram_mb,
            instance_id=profile_id,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "GameProfile":
        valid_fields = cls.__dataclass_fields__

        filtered = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        return cls(**filtered)


class ProfileManager:
    """CRUD de perfiles almacenados en profiles.json."""

    def __init__(
        self,
        profiles_file: Path | None = None,
    ) -> None:
        app_directory = get_app_directory()
        profiles_directory = app_directory / "profiles"
        profiles_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.profiles_file = (
            Path(profiles_file)
            if profiles_file is not None
            else profiles_directory / "profiles.json"
        )

    def list_profiles(self) -> list[GameProfile]:
        if not self.profiles_file.exists():
            return []

        try:
            with self.profiles_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(data, list):
            return []

        profiles: list[GameProfile] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                profiles.append(
                    GameProfile.from_dict(item)
                )
            except TypeError:
                continue

        return profiles

    def save_profiles(
        self,
        profiles: list[GameProfile],
    ) -> None:
        self.profiles_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.profiles_file.with_suffix(
            ".json.tmp"
        )

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                [asdict(profile) for profile in profiles],
                file,
                ensure_ascii=False,
                indent=4,
            )

        temporary.replace(self.profiles_file)

    def get_profile(
        self,
        profile_id: str,
    ) -> GameProfile | None:
        return next(
            (
                profile
                for profile in self.list_profiles()
                if profile.id == profile_id
            ),
            None,
        )

    def add_profile(
        self,
        profile: GameProfile,
    ) -> None:
        profiles = self.list_profiles()
        profiles.append(profile)
        self.save_profiles(profiles)

    def update_profile(
        self,
        updated_profile: GameProfile,
    ) -> bool:
        profiles = self.list_profiles()

        for index, profile in enumerate(profiles):
            if profile.id == updated_profile.id:
                profiles[index] = updated_profile
                self.save_profiles(profiles)
                return True

        return False

    def delete_profile(
        self,
        profile_id: str,
    ) -> bool:
        profiles = self.list_profiles()

        filtered = [
            profile
            for profile in profiles
            if profile.id != profile_id
        ]

        if len(filtered) == len(profiles):
            return False

        self.save_profiles(filtered)
        return True