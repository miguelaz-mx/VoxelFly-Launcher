from __future__ import annotations

import threading
from io import BytesIO
from typing import Callable

import customtkinter as ctk
import requests
from PIL import Image

from modrinth_api import ModrinthClient, ModrinthError


COLORS = {
    "panel": "#171a21",
    "panel_alt": "#20242c",
    "panel_hover": "#292e39",
    "border": "#303642",
    "purple": "#7d67cb",
    "purple_hover": "#927ce0",
    "green": "#2fa866",
    "green_hover": "#3abb79",
    "text": "#ffffff",
    "muted": "#9ba1ad",
    "danger": "#d85c69",
}


class ModBrowserFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        loader_getter: Callable[[], str],
        version_getter: Callable[[], str],
        status_callback: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            corner_radius=16,
            fg_color=COLORS["panel"],
            border_width=1,
            border_color=COLORS["border"],
        )

        self.loader_getter = loader_getter
        self.version_getter = version_getter
        self.status_callback = status_callback
        self.client = ModrinthClient()

        self.icon_images: list[ctk.CTkImage] = []
        self.searching = False

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_filters()
        self._create_results()

        self.after(200, self.search)

    def _create_header(self) -> None:
        header = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(24, 12),
        )
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="NAVEGADOR DE MODS",
            font=ctk.CTkFont(
                size=28,
                weight="bold",
            ),
            text_color=COLORS["text"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.compatibility_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["purple"],
        )
        self.compatibility_label.grid(
            row=0,
            column=1,
            sticky="e",
        )

    def _create_filters(self) -> None:
        filters = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        filters.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 16),
        )
        filters.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            filters,
            height=44,
            corner_radius=10,
            placeholder_text=(
                "Buscar Sodium, Iris, JEI, Create..."
            ),
            fg_color=COLORS["panel_alt"],
            border_color=COLORS["border"],
        )
        self.search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10),
        )
        self.search_entry.bind(
            "<Return>",
            lambda _: self.search(),
        )

        self.search_button = ctk.CTkButton(
            filters,
            text="BUSCAR",
            width=120,
            height=44,
            corner_radius=10,
            fg_color=COLORS["purple"],
            hover_color=COLORS["purple_hover"],
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            command=self.search,
        )
        self.search_button.grid(
            row=0,
            column=1,
        )

    def _create_results(self) -> None:
        self.results_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
            fg_color="#12151b",
            scrollbar_button_color=COLORS["purple"],
            scrollbar_button_hover_color=(
                COLORS["purple_hover"]
            ),
        )
        self.results_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(0, 24),
        )
        self.results_frame.grid_columnconfigure(
            0,
            weight=1,
        )

    def search(self) -> None:
        if self.searching:
            return

        loader = self.loader_getter()
        version = self.version_getter()

        if loader == "Vanilla":
            self._show_message(
                "Selecciona Fabric, Forge o NeoForge para instalar mods."
            )
            return

        if version in {
            "Cargando...",
            "No disponible",
        }:
            self._show_message(
                "Primero selecciona una versión válida de Minecraft."
            )
            return

        self.searching = True
        self.search_button.configure(
            text="BUSCANDO...",
            state="disabled",
        )

        self.compatibility_label.configure(
            text=f"{loader} • Minecraft {version}"
        )
        self.status_callback(
            f"Buscando mods para {loader} {version}..."
        )

        query = self.search_entry.get().strip()

        threading.Thread(
            target=self._search_worker,
            args=(query, loader, version),
            daemon=True,
        ).start()

    def _search_worker(
        self,
        query: str,
        loader: str,
        version: str,
    ) -> None:
        try:
            results = self.client.search_mods(
                query,
                version,
                loader,
                limit=30,
            )
        except Exception as error:
            error_text = str(error)
            self.after(
                0,
                lambda: self._finish_search_error(
                    error_text
                ),
            )
            return

        self.after(
            0,
            lambda: self._finish_search(
                results,
                loader,
                version,
            ),
        )

    def _finish_search(
        self,
        results: list[dict],
        loader: str,
        version: str,
    ) -> None:
        self.searching = False
        self.search_button.configure(
            text="BUSCAR",
            state="normal",
        )

        self._clear_results()

        if not results:
            self._show_message(
                "No se encontraron mods compatibles."
            )
            return

        for index, project in enumerate(results):
            card = self._create_mod_card(
                project,
                loader,
                version,
            )
            card.grid(
                row=index,
                column=0,
                sticky="ew",
                padx=6,
                pady=6,
            )

        self.status_callback(
            f"Se encontraron {len(results)} mods compatibles."
        )

    def _finish_search_error(
        self,
        error_text: str,
    ) -> None:
        self.searching = False
        self.search_button.configure(
            text="BUSCAR",
            state="normal",
        )
        self._show_message(
            f"No se pudo completar la búsqueda:\n{error_text}"
        )
        self.status_callback(
            "Error al buscar mods."
        )

    def _clear_results(self) -> None:
        self.icon_images.clear()

        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def _show_message(
        self,
        message: str,
    ) -> None:
        self._clear_results()

        ctk.CTkLabel(
            self.results_frame,
            text=message,
            justify="center",
            wraplength=600,
            font=ctk.CTkFont(size=15),
            text_color=COLORS["muted"],
        ).grid(
            row=0,
            column=0,
            padx=30,
            pady=80,
        )

    def _create_mod_card(
        self,
        project: dict,
        loader: str,
        version: str,
    ) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.results_frame,
            height=112,
            corner_radius=12,
            fg_color=COLORS["panel_alt"],
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)

        icon_label = ctk.CTkLabel(
            card,
            text="MOD",
            width=72,
            height=72,
            corner_radius=12,
            fg_color="#292e39",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=COLORS["purple"],
        )
        icon_label.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=16,
            pady=18,
        )

        icon_url = project.get("icon_url")

        if icon_url:
            threading.Thread(
                target=self._load_icon_worker,
                args=(icon_label, str(icon_url)),
                daemon=True,
            ).start()

        title = project.get("title") or project.get("slug") or "Mod"
        description = project.get("description") or "Sin descripción."
        downloads = int(project.get("downloads") or 0)

        ctk.CTkLabel(
            card,
            text=str(title),
            font=ctk.CTkFont(
                size=16,
                weight="bold",
            ),
            text_color=COLORS["text"],
        ).grid(
            row=0,
            column=1,
            sticky="sw",
            pady=(17, 2),
        )

        ctk.CTkLabel(
            card,
            text=(
                f"{description}\n"
                f"{downloads:,} descargas"
            ),
            justify="left",
            wraplength=520,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
        ).grid(
            row=1,
            column=1,
            sticky="nw",
            pady=(0, 14),
        )

        install_button = ctk.CTkButton(
            card,
            text="INSTALAR",
            width=112,
            height=40,
            corner_radius=10,
            fg_color=COLORS["green"],
            hover_color=COLORS["green_hover"],
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            command=lambda: self.install_project(
                project,
                loader,
                version,
                install_button,
            ),
        )
        install_button.grid(
            row=0,
            column=2,
            rowspan=2,
            padx=18,
        )

        return card

    def _load_icon_worker(
        self,
        label: ctk.CTkLabel,
        url: str,
    ) -> None:
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": "VoxelFly/0.3",
                },
            )
            response.raise_for_status()

            image = Image.open(
                BytesIO(response.content)
            ).convert("RGBA")

            icon = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(72, 72),
            )
        except Exception:
            return

        self.after(
            0,
            lambda: self._apply_icon(
                label,
                icon,
            ),
        )

    def _apply_icon(
        self,
        label: ctk.CTkLabel,
        icon: ctk.CTkImage,
    ) -> None:
        if not label.winfo_exists():
            return

        self.icon_images.append(icon)
        label.configure(
            text="",
            image=icon,
        )

    def install_project(
        self,
        project: dict,
        loader: str,
        version: str,
        button: ctk.CTkButton,
    ) -> None:
        project_id = str(
            project.get("project_id")
            or project.get("slug")
            or ""
        )
        title = str(
            project.get("title")
            or project.get("slug")
            or "Mod"
        )

        if not project_id:
            self.status_callback(
                "Este proyecto no tiene un identificador válido."
            )
            return

        button.configure(
            text="INSTALANDO...",
            state="disabled",
        )
        self.status_callback(
            f"Instalando {title}..."
        )

        threading.Thread(
            target=self._install_worker,
            args=(
                project_id,
                title,
                loader,
                version,
                button,
            ),
            daemon=True,
        ).start()

    def _install_worker(
        self,
        project_id: str,
        title: str,
        loader: str,
        version: str,
        button: ctk.CTkButton,
    ) -> None:
        try:
            installed_files = self.client.install_project(
                project_id,
                version,
                loader,
            )
        except Exception as error:
            error_text = str(error)
            self.after(
                0,
                lambda: self._finish_install_error(
                    title,
                    error_text,
                    button,
                ),
            )
            return

        self.after(
            0,
            lambda: self._finish_install_success(
                title,
                installed_files,
                button,
            ),
        )

    def _finish_install_success(
        self,
        title: str,
        installed_files,
        button: ctk.CTkButton,
    ) -> None:
        if button.winfo_exists():
            button.configure(
                text="INSTALADO ✓",
                state="disabled",
                fg_color="#256d49",
            )

        file_count = len(installed_files)
        self.status_callback(
            f"{title} instalado con "
            f"{file_count} archivo(s), incluyendo dependencias."
        )

    def _finish_install_error(
        self,
        title: str,
        error_text: str,
        button: ctk.CTkButton,
    ) -> None:
        if button.winfo_exists():
            button.configure(
                text="REINTENTAR",
                state="normal",
                fg_color=COLORS["danger"],
            )

        self.status_callback(
            f"No se pudo instalar {title}: {error_text}"
        )