from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


API_BASE = "https://api.modrinth.com/v2"
USER_AGENT = "VoxelFly/0.3 (Minecraft launcher)"


class ModrinthError(RuntimeError):
    """Error controlado al comunicarse con Modrinth."""


class ModrinthClient:
    def __init__(self, game_directory: Path | None = None) -> None:
        appdata = os.environ.get("APPDATA")

        if game_directory is not None:
            self.game_directory = Path(game_directory)
        elif appdata:
            self.game_directory = Path(appdata) / "VoxelFly 2.0"
        else:
            self.game_directory = (
                Path.home() / "AppData" / "Roaming" / "VoxelFly 2.0"
            )

        self.mods_directory = self.game_directory / "mods"
        self.mods_directory.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self.session.get(
                f"{API_BASE}{path}",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise ModrinthError(
                f"No se pudo conectar con Modrinth: {error}"
            ) from error

        try:
            return response.json()
        except ValueError as error:
            raise ModrinthError(
                "Modrinth devolvió una respuesta inválida."
            ) from error

    def search_mods(
        self,
        query: str,
        minecraft_version: str,
        loader: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        loader_id = loader.lower()

        facets = [
            ["project_type:mod"],
            [f"versions:{minecraft_version}"],
        ]

        if loader_id != "vanilla":
            facets.append([f"categories:{loader_id}"])

        data = self._get(
            "/search",
            params={
                "query": query.strip(),
                "limit": max(1, min(limit, 100)),
                "offset": max(0, offset),
                "index": "relevance",
                "facets": json.dumps(facets),
            },
        )

        hits = data.get("hits", [])
        return hits if isinstance(hits, list) else []

    def get_compatible_versions(
        self,
        project_id: str,
        minecraft_version: str,
        loader: str,
    ) -> list[dict[str, Any]]:
        loader_id = loader.lower()

        params: dict[str, str] = {
            "game_versions": json.dumps([minecraft_version]),
            "include_changelog": "false",
        }

        if loader_id != "vanilla":
            params["loaders"] = json.dumps([loader_id])

        data = self._get(
            f"/project/{quote(project_id, safe='')}/version",
            params=params,
        )

        return data if isinstance(data, list) else []

    def choose_latest_version(
        self,
        project_id: str,
        minecraft_version: str,
        loader: str,
    ) -> dict[str, Any]:
        versions = self.get_compatible_versions(
            project_id,
            minecraft_version,
            loader,
        )

        if not versions:
            raise ModrinthError(
                "No existe una versión compatible de este mod."
            )

        release_versions = [
            version
            for version in versions
            if version.get("version_type") == "release"
        ]

        return (release_versions or versions)[0]

    def install_project(
        self,
        project_id: str,
        minecraft_version: str,
        loader: str,
    ) -> list[Path]:
        installed: list[Path] = []
        visited: set[str] = set()

        version = self.choose_latest_version(
            project_id,
            minecraft_version,
            loader,
        )

        self._install_version_recursive(
            version,
            minecraft_version,
            loader,
            installed,
            visited,
        )

        return installed

    def _install_version_recursive(
        self,
        version: dict[str, Any],
        minecraft_version: str,
        loader: str,
        installed: list[Path],
        visited: set[str],
    ) -> None:
        version_id = str(version.get("id", ""))

        if not version_id or version_id in visited:
            return

        visited.add(version_id)

        for dependency in version.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue

            dependency_version_id = dependency.get("version_id")
            dependency_project_id = dependency.get("project_id")

            if dependency_version_id:
                dependency_version = self._get(
                    f"/version/{quote(str(dependency_version_id), safe='')}"
                )
            elif dependency_project_id:
                dependency_version = self.choose_latest_version(
                    str(dependency_project_id),
                    minecraft_version,
                    loader,
                )
            else:
                continue

            self._install_version_recursive(
                dependency_version,
                minecraft_version,
                loader,
                installed,
                visited,
            )

        target = self._download_primary_file(version)

        if target not in installed:
            installed.append(target)

    def _download_primary_file(
        self,
        version: dict[str, Any],
    ) -> Path:
        files = version.get("files", [])

        if not files:
            raise ModrinthError(
                "La versión seleccionada no contiene archivos."
            )

        selected_file = next(
            (
                file
                for file in files
                if file.get("primary")
            ),
            files[0],
        )

        url = selected_file.get("url")
        filename = selected_file.get("filename")

        if not url or not filename:
            raise ModrinthError(
                "Modrinth no proporcionó una descarga válida."
            )

        target = self.mods_directory / str(filename)

        if target.exists() and target.stat().st_size > 0:
            return target

        temporary = target.with_suffix(target.suffix + ".part")

        try:
            with self.session.get(
                str(url),
                stream=True,
                timeout=60,
            ) as response:
                response.raise_for_status()

                with temporary.open("wb") as file:
                    for chunk in response.iter_content(
                        chunk_size=1024 * 128
                    ):
                        if chunk:
                            file.write(chunk)

            temporary.replace(target)

        except (requests.RequestException, OSError) as error:
            temporary.unlink(missing_ok=True)
            raise ModrinthError(
                f"No se pudo descargar {filename}: {error}"
            ) from error

        return target