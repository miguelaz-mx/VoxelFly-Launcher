from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import minecraft_launcher_lib

from auth import microsoft_login


MINECRAFT_DIRECTORY = (
    Path(os.environ["APPDATA"])
    / "VoxelFly 2.0"
)


def mostrar_progreso() -> dict:
    """
    Crea los callbacks de progreso para la instalación.
    """

    progreso = {
        "maximo": 0,
        "actual": 0,
    }

    def set_status(texto: str) -> None:
        print(f"\nEstado: {texto}")

    def set_max(maximo: int) -> None:
        progreso["maximo"] = maximo

    def set_progress(actual: int) -> None:
        progreso["actual"] = actual
        maximo = progreso["maximo"]

        if maximo <= 0:
            return

        porcentaje = int(
            (actual / maximo) * 100
        )

        print(
            f"\rDescargando: {porcentaje}% "
            f"({actual}/{maximo})",
            end="",
        )

    return {
        "setStatus": set_status,
        "setMax": set_max,
        "setProgress": set_progress,
    }


def instalar_minecraft(version: str) -> None:
    """
    Instala la versión solicitada si todavía no está instalada.
    """

    versiones = obtener_versiones_instaladas()

    if version in versiones:
        print(
            f"\nMinecraft {version} ya está instalado."
        )
        return

    print("\n==============================")
    print(f"Instalando Minecraft {version}")
    print("==============================")

    MINECRAFT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    minecraft_launcher_lib.install.install_minecraft_version(
        version,
        str(MINECRAFT_DIRECTORY),
        callback=mostrar_progreso(),
    )

    print(
        "\n\nInstalación terminada correctamente."
    )


def obtener_versiones_instaladas() -> list[str]:
    """
    Devuelve una lista con las versiones instaladas.
    """

    versiones = (
        minecraft_launcher_lib.utils.get_installed_versions(
            str(MINECRAFT_DIRECTORY)
        )
    )

    return [
        version["id"]
        for version in versiones
        if "id" in version
    ]


def mostrar_versiones_instaladas() -> None:
    """
    Imprime las versiones encontradas.
    """

    versiones = obtener_versiones_instaladas()

    print("\nVersiones instaladas:")

    if not versiones:
        print("- Todavía no hay versiones.")
        return

    for version in versiones:
        print(f"- {version}")


def pedir_version() -> str:
    """
    Solicita al usuario una versión.
    """

    print("\nEjemplos:")
    print("- 1.21.1")
    print("- 1.20.4")
    print("- 1.20.1")

    return input(
        "\nEscribe la versión que deseas usar: "
    ).strip()


def preparar_opciones(
    account: dict[str, Any],
) -> dict[str, Any]:
    """
    Genera las opciones necesarias para iniciar Minecraft.
    """

    return {
        "username": account["name"],
        "uuid": account["id"],
        "token": account["access_token"],

        "launcherName": "VoxelFly",
        "launcherVersion": "0.0.1",

        "gameDirectory": str(
            MINECRAFT_DIRECTORY
        ),

        "jvmArguments": [
            "-Xms1024M",
            "-Xmx4096M",
        ],
    }


def ejecutar_minecraft(
    version: str,
    account: dict[str, Any],
) -> None:
    """
    Genera el comando y abre Minecraft.
    """

    options = preparar_opciones(account)

    minecraft_command = (
        minecraft_launcher_lib.command.get_minecraft_command(
            version,
            str(MINECRAFT_DIRECTORY),
            options,
        )
    )

    print("\nAbriendo Minecraft...")
    print(f"Jugador: {account['name']}")
    print(f"Versión: {version}")

    subprocess.Popen(
        minecraft_command,
        cwd=str(MINECRAFT_DIRECTORY),
    )


def main() -> None:
    print("==============================")
    print("       VoxelFly 2.0")
    print("==============================")

    try:
        account = microsoft_login()

    except Exception as error:
        print("\nNo se pudo iniciar sesión.")
        print(f"Error: {error}")
        return

    print("\n==============================")
    print("Sesión iniciada correctamente")
    print("==============================")
    print(f"Nombre: {account['name']}")
    print(f"UUID: {account['id']}")

    print("\nCarpeta de Minecraft:")
    print(MINECRAFT_DIRECTORY)

    mostrar_versiones_instaladas()

    version = pedir_version()

    if not version:
        print("\nNo escribiste una versión.")
        return

    try:
        instalar_minecraft(version)

    except Exception as error:
        print("\nNo se pudo instalar Minecraft.")
        print(f"Error: {error}")
        return

    try:
        ejecutar_minecraft(
            version,
            account,
        )

    except Exception as error:
        print("\nNo se pudo abrir Minecraft.")
        print(f"Error: {error}")


if __name__ == "__main__":
    main()