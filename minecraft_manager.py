from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypedDict

import minecraft_launcher_lib


class InstallCallback(TypedDict, total=False):
    setStatus: Callable[[str], None]
    setProgress: Callable[[int], None]
    setMax: Callable[[int], None]


class AccountRequiredError(RuntimeError):
    """Se usa cuando Minecraft quedó instalado, pero falta una sesión oficial."""


@dataclass(frozen=True)
class LaunchResult:
    installed_version: str
    launched: bool
    message: str


class MinecraftManager:
    """
    Instala Vanilla, Fabric, Forge o NeoForge y después intenta
    iniciar Minecraft con una cuenta oficial de Microsoft.
    """

    LOADER_IDS = {
        "Vanilla": "vanilla",
        "Fabric": "fabric",
        "Forge": "forge",
        "NeoForge": "neoforge",
    }

    def __init__(self) -> None:
        appdata = os.environ.get("APPDATA")

        if appdata:
            self.minecraft_directory = Path(appdata) / "VoxelFly 2.0"
        else:
            self.minecraft_directory = (
                Path.home() / "AppData" / "Roaming" / "VoxelFly 2.0"
            )

        self.minecraft_directory.mkdir(parents=True, exist_ok=True)

    @property
    def account_file(self) -> Path:
        return self.minecraft_directory / "account.json"

    def install_profile(
        self,
        loader_name: str,
        minecraft_version: str,
        callback: InstallCallback | None = None,
    ) -> str:
        """
        Instala o repara la versión seleccionada.

        Devuelve el identificador real que debe usarse para arrancar.
        En Vanilla es la propia versión. En loaders es el ID generado
        por Fabric, Forge o NeoForge.
        """

        if loader_name not in self.LOADER_IDS:
            raise ValueError(f"Cargador no reconocido: {loader_name}")

        if loader_name == "Vanilla":
            minecraft_launcher_lib.install.install_minecraft_version(
                minecraft_version,
                self.minecraft_directory,
                callback=callback,
            )
            return minecraft_version

        loader_id = self.LOADER_IDS[loader_name]
        mod_loader = minecraft_launcher_lib.mod_loader.get_mod_loader(loader_id)

        if not mod_loader.is_minecraft_version_supported(minecraft_version):
            raise ValueError(
                f"{loader_name} no es compatible con Minecraft "
                f"{minecraft_version}."
            )

        # install() también instala Vanilla si todavía no existe.
        installed_version = mod_loader.install(
            minecraft_version,
            self.minecraft_directory,
            callback=callback,
        )

        return installed_version

    def load_account(self) -> dict:
        """
        Carga la cuenta guardada por auth.py.

        Para iniciar el juego se necesitan name, id y access_token.
        El access_token es temporal y debe renovarse con Microsoft.
        """

        if not self.account_file.exists():
            return {}

        try:
            with self.account_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}

        return data if isinstance(data, dict) else {}

    def launch(
        self,
        installed_version: str,
        memory_mb: int,
        account_data: dict,
    ) -> None:
        required = ("name", "id", "access_token")
        missing = [key for key in required if not account_data.get(key)]

        if missing:
            raise AccountRequiredError(
                "La versión quedó instalada, pero falta iniciar o renovar "
                "la sesión oficial de Microsoft antes de jugar."
            )

        options = {
            "username": account_data["name"],
            "uuid": account_data["id"],
            "token": account_data["access_token"],
            "jvmArguments": [
                f"-Xmx{memory_mb}M",
                f"-Xms{min(1024, memory_mb)}M",
            ],
            "launcherName": "VoxelFly",
            "launcherVersion": "0.2",
            "gameDirectory": str(self.minecraft_directory),
        }

        command = minecraft_launcher_lib.command.get_minecraft_command(
            installed_version,
            self.minecraft_directory,
            options,
        )

        subprocess.Popen(
            command,
            cwd=self.minecraft_directory,
        )

    def install_and_launch(
        self,
        loader_name: str,
        minecraft_version: str,
        memory_mb: int,
        callback: InstallCallback | None = None,
    ) -> LaunchResult:
        installed_version = self.install_profile(
            loader_name,
            minecraft_version,
            callback,
        )

        account_data = self.load_account()

        try:
            self.launch(
                installed_version,
                memory_mb,
                account_data,
            )
        except AccountRequiredError as error:
            return LaunchResult(
                installed_version=installed_version,
                launched=False,
                message=str(error),
            )

        return LaunchResult(
            installed_version=installed_version,
            launched=True,
            message=f"Minecraft {installed_version} iniciado.",
        )