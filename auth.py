from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Any

import minecraft_launcher_lib


CLIENT_ID = "423059ec-4c44-47be-b654-3e05ec88b884"
REDIRECT_URI = "http://localhost"

VOXELFLY_DIRECTORY = Path.home() / "AppData" / "Roaming" / "VoxelFly 2.0"
ACCOUNT_FILE = VOXELFLY_DIRECTORY / "account.json"


def guardar_cuenta(account: dict[str, Any]) -> None:
    """
    Guarda los datos necesarios para recuperar la sesión más adelante.
    """

    VOXELFLY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    datos_guardados = {
        "id": account.get("id", ""),
        "name": account.get("name", ""),
        "refresh_token": account.get("refresh_token", ""),
        "skins": account.get("skins", []),
        "capes": account.get("capes", []),
    }

    with ACCOUNT_FILE.open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            datos_guardados,
            archivo,
            indent=4,
            ensure_ascii=False,
        )


def cargar_cuenta_guardada() -> dict[str, Any] | None:
    """
    Lee account.json si existe.
    """

    if not ACCOUNT_FILE.exists():
        return None

    try:
        with ACCOUNT_FILE.open(
            "r",
            encoding="utf-8",
        ) as archivo:
            datos = json.load(archivo)

        if isinstance(datos, dict):
            return datos

    except (OSError, json.JSONDecodeError):
        return None

    return None


def renovar_sesion(refresh_token: str) -> dict[str, Any]:
    """
    Obtiene un access token nuevo usando el refresh token guardado.
    """

    if not refresh_token:
        raise ValueError(
            "No existe un refresh token guardado."
        )

    account = (
        minecraft_launcher_lib.microsoft_account.complete_refresh(
            CLIENT_ID,
            None,
            REDIRECT_URI,
            refresh_token,
        )
    )

    guardar_cuenta(account)

    return account


def iniciar_sesion_nueva() -> dict[str, Any]:
    """
    Abre Microsoft en el navegador y completa el inicio de sesión.
    """

    login_url, state, code_verifier = (
        minecraft_launcher_lib.microsoft_account.get_secure_login_data(
            CLIENT_ID,
            REDIRECT_URI,
        )
    )

    print("\nAbriendo Microsoft en tu navegador...")

    navegador_abierto = webbrowser.open(
        login_url,
        new=1,
    )

    if not navegador_abierto:
        print("\nNo se pudo abrir el navegador automáticamente.")
        print("Copia y abre esta dirección:")
        print(login_url)

    print("\nPasos:")
    print("1. Inicia sesión con la cuenta que tiene Minecraft.")
    print("2. Microsoft te enviará a una dirección de localhost.")
    print("3. La página puede decir que no se puede conectar.")
    print("4. Copia toda la dirección de la barra del navegador.")
    print("5. Pégala aquí en la terminal.")

    callback_url = input(
        "\nPega aquí la URL completa:\n> "
    ).strip()

    if not callback_url:
        raise ValueError(
            "No pegaste ninguna dirección."
        )

    auth_code = (
        minecraft_launcher_lib.microsoft_account.parse_auth_code_url(
            callback_url,
            state,
        )
    )

    print("\nVerificando Microsoft, Xbox y Minecraft...")

    account = (
        minecraft_launcher_lib.microsoft_account.complete_login(
            CLIENT_ID,
            None,
            REDIRECT_URI,
            auth_code,
            code_verifier,
        )
    )

    guardar_cuenta(account)

    return account


def microsoft_login() -> dict[str, Any]:
    """
    Intenta renovar una sesión guardada.
    Si no existe o falla, solicita iniciar sesión nuevamente.
    """

    cuenta_guardada = cargar_cuenta_guardada()

    if cuenta_guardada:
        refresh_token = cuenta_guardada.get(
            "refresh_token",
            "",
        )

        if refresh_token:
            print("\nSe encontró una sesión guardada.")
            print("Intentando renovarla...")

            try:
                return renovar_sesion(refresh_token)

            except Exception as error:
                print("\nNo se pudo renovar la sesión guardada.")
                print(f"Motivo: {error}")
                print("Se abrirá Microsoft nuevamente.")

    return iniciar_sesion_nueva()