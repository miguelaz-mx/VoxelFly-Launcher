from __future__ import annotations

import ctypes
import threading
from pathlib import Path
from typing import Callable

import customtkinter as ctk
import minecraft_launcher_lib
from PIL import Image

from minecraft_manager import MinecraftManager, LaunchResult
from mod_browser import ModBrowserFrame


# ============================================================
# RUTAS
# ============================================================

ASSETS_DIR = Path(__file__).parent / "assets"
BACKGROUND_DIR = ASSETS_DIR / "backgrounds"


# ============================================================
# COLORES
# ============================================================

COLORS = {
    "background": "#0d0f14",
    "topbar": "#181b22",
    "panel": "#171a21",
    "panel_alt": "#20242c",
    "panel_hover": "#292e39",
    "border": "#303642",
    "purple": "#7d67cb",
    "purple_hover": "#927ce0",
    "green": "#2fa866",
    "green_hover": "#3abb79",
    "orange": "#f18b35",
    "orange_hover": "#ff9d4d",
    "text": "#ffffff",
    "muted": "#9ba1ad",
    "danger": "#d85c69",
}


# ============================================================
# CARGADORES DISPONIBLES
# ============================================================

LOADERS = {
    "Vanilla": {
        "id": "vanilla",
        "description": (
            "Minecraft original, sin cargadores de mods. "
            "Incluye lanzamientos, snapshots y versiones antiguas."
        ),
    },
    "Fabric": {
        "id": "fabric",
        "description": (
            "Cargador ligero y rápido. Recomendado para mods "
            "de rendimiento como Sodium."
        ),
    },
    "Forge": {
        "id": "forge",
        "description": (
            "Cargador clásico compatible con una enorme cantidad "
            "de mods y paquetes."
        ),
    },
    "NeoForge": {
        "id": "neoforge",
        "description": (
            "Cargador moderno enfocado principalmente en versiones "
            "recientes de Minecraft."
        ),
    },
}


class VoxelFlyApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("VoxelFly Launcher")
        self.geometry("1180x720")
        self.minsize(1050, 650)
        self.configure(fg_color=COLORS["background"])

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Selección de cargador y versión.
        self.selected_loader = ctk.StringVar(value="Vanilla")
        self.selected_version = ctk.StringVar(value="Cargando...")

        # RAM detectada y seleccionada.
        self.total_ram_mb = self.get_total_ram_mb()
        self.maximum_ram_mb = self.get_maximum_assignable_ram()

        default_memory = min(4096, self.maximum_ram_mb)

        self.memory_value = ctk.IntVar(
            value=default_memory
        )

        # Versiones disponibles.
        self.available_versions: dict[str, list[str]] = {
            "Vanilla": [],
            "Fabric": [],
            "Forge": [],
            "NeoForge": [],
        }

        self.versions_loaded = False
        self.loading_versions = False
        self.installing_game = False
        self.install_progress_max = 0
        self.minecraft_manager = MinecraftManager()

        # Imágenes.
        self.background_image: ctk.CTkImage | None = None

        # Widgets principales.
        self.content: ctk.CTkFrame | None = None
        self.status_label: ctk.CTkLabel | None = None
        self.connection_label: ctk.CTkLabel | None = None

        self.loader_menu: ctk.CTkOptionMenu | None = None
        self.version_menu: ctk.CTkOptionMenu | None = None
        self.profile_description: ctk.CTkLabel | None = None
        self.selected_summary: ctk.CTkLabel | None = None
        self.play_profile_button: ctk.CTkButton | None = None
        self.banner_play_button: ctk.CTkButton | None = None

        self.memory_label: ctk.CTkLabel | None = None
        self.memory_slider: ctk.CTkSlider | None = None

        self.create_topbar()
        self.create_statusbar()
        self.create_home_screen()

    # ========================================================
    # RAM DEL SISTEMA
    # ========================================================

    def get_total_ram_mb(self) -> int:
        """
        Detecta la cantidad total de RAM instalada en Windows.
        Si ocurre un error, usa 8 GB como valor de respaldo.
        """

        try:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong),
                    ("available_physical", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong),
                    ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("available_virtual", ctypes.c_ulonglong),
                    (
                        "available_extended_virtual",
                        ctypes.c_ulonglong,
                    ),
                ]

            memory_status = MemoryStatus()
            memory_status.length = ctypes.sizeof(
                MemoryStatus
            )

            result = (
                ctypes.windll.kernel32.GlobalMemoryStatusEx(
                    ctypes.byref(memory_status)
                )
            )

            if not result:
                return 8192

            return int(
                memory_status.total_physical
                / 1024
                / 1024
            )

        except Exception:
            return 8192

    def get_maximum_assignable_ram(self) -> int:
        """
        Deja al menos 2 GB para Windows y otros programas.
        Limita Minecraft a un máximo de 16 GB.
        """

        available_for_minecraft = (
            self.total_ram_mb - 2048
        )

        maximum = min(
            available_for_minecraft,
            16384,
        )

        return max(
            2048,
            maximum,
        )

    def memory_text(self) -> str:
        memory_mb = self.memory_value.get()
        memory_gb = memory_mb / 1024

        return (
            f"RAM asignada: {memory_gb:.1f} GB "
            f"({memory_mb} MB)"
        )

    def update_memory(self, value: float) -> None:
        """
        Actualiza la RAM en pasos de 512 MB.
        """

        rounded_value = int(
            round(value / 512) * 512
        )

        rounded_value = max(
            2048,
            min(
                rounded_value,
                self.maximum_ram_mb,
            ),
        )

        self.memory_value.set(
            rounded_value
        )

        if self.memory_label is not None:
            self.memory_label.configure(
                text=self.memory_text()
            )

        self.refresh_profile_information()

        self.set_status(
            f"RAM seleccionada: "
            f"{rounded_value / 1024:.1f} GB"
        )

    def set_memory_preset(
        self,
        memory_mb: int,
    ) -> None:
        """
        Selecciona rápidamente una cantidad de RAM.
        """

        memory_mb = min(
            memory_mb,
            self.maximum_ram_mb,
        )

        memory_mb = max(
            2048,
            memory_mb,
        )

        self.memory_value.set(
            memory_mb
        )

        if self.memory_slider is not None:
            self.memory_slider.set(
                memory_mb
            )

        if self.memory_label is not None:
            self.memory_label.configure(
                text=self.memory_text()
            )

        self.refresh_profile_information()

        self.set_status(
            f"RAM asignada: "
            f"{memory_mb / 1024:.1f} GB"
        )

    # ========================================================
    # BARRA SUPERIOR
    # ========================================================

    def create_topbar(self) -> None:
        topbar = ctk.CTkFrame(
            self,
            height=78,
            corner_radius=0,
            fg_color=COLORS["topbar"],
            border_width=1,
            border_color=COLORS["border"],
        )

        topbar.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(
            topbar,
            text="VOXELFLY",
            font=ctk.CTkFont(
                size=24,
                weight="bold",
            ),
            text_color=COLORS["purple"],
        ).grid(
            row=0,
            column=0,
            padx=(24, 34),
            pady=18,
        )

        self.create_nav_button(
            parent=topbar,
            text="⌂\nINICIO",
            column=1,
            command=self.show_home,
            active=True,
        )

        self.create_nav_button(
            parent=topbar,
            text="●\nPERFILES",
            column=2,
            command=self.show_profiles,
        )

        self.create_nav_button(
            parent=topbar,
            text="▦\nMODS",
            column=3,
            command=self.show_mods,
        )

        self.create_nav_button(
            parent=topbar,
            text="⚙\nAJUSTES",
            column=4,
            command=self.show_settings,
        )

        ctk.CTkButton(
            topbar,
            text="👤  Invitado\n     Iniciar sesión",
            width=190,
            height=52,
            corner_radius=12,
            fg_color=COLORS["panel"],
            hover_color=COLORS["panel_hover"],
            border_width=1,
            border_color=COLORS["border"],
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            command=self.open_account,
        ).grid(
            row=0,
            column=6,
            padx=(20, 24),
            pady=12,
        )

    def create_nav_button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        column: int,
        command: Callable[[], None],
        active: bool = False,
    ) -> None:
        button = ctk.CTkButton(
            parent,
            text=text,
            width=88,
            height=58,
            corner_radius=10,
            fg_color=(
                COLORS["purple"]
                if active
                else "transparent"
            ),
            hover_color=COLORS["panel_hover"],
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            command=command,
        )

        button.grid(
            row=0,
            column=column,
            padx=4,
            pady=10,
        )

    # ========================================================
    # BARRA INFERIOR
    # ========================================================

    def create_statusbar(self) -> None:
        statusbar = ctk.CTkFrame(
            self,
            height=34,
            corner_radius=0,
            fg_color="#101217",
            border_width=1,
            border_color=COLORS["border"],
        )

        statusbar.grid(
            row=2,
            column=0,
            sticky="ew",
        )

        statusbar.grid_propagate(False)
        statusbar.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            statusbar,
            text="VoxelFly listo",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["muted"],
        )

        self.status_label.grid(
            row=0,
            column=0,
            padx=16,
            pady=7,
            sticky="w",
        )

        self.connection_label = ctk.CTkLabel(
            statusbar,
            text="SIN CUENTA",
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            text_color=COLORS["orange"],
        )

        self.connection_label.grid(
            row=0,
            column=2,
            padx=16,
            sticky="e",
        )

    def set_status(
        self,
        message: str,
    ) -> None:
        if self.status_label is not None:
            self.status_label.configure(
                text=message
            )

    # ========================================================
    # PANTALLA PRINCIPAL
    # ========================================================

    def create_home_screen(self) -> None:
        self.content = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=COLORS["background"],
        )

        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=14,
            pady=14,
        )

        self.content.grid_rowconfigure(
            0,
            weight=1,
        )

        self.content.grid_columnconfigure(
            0,
            weight=3,
        )

        self.content.grid_columnconfigure(
            1,
            weight=1,
        )

        self.create_banner()
        self.create_profiles_panel()

    def clear_content(self) -> None:
        if self.content is None:
            return

        for widget in self.content.winfo_children():
            widget.destroy()

        self.loader_menu = None
        self.version_menu = None
        self.profile_description = None
        self.selected_summary = None
        self.play_profile_button = None
        self.banner_play_button = None
        self.memory_label = None
        self.memory_slider = None

    # ========================================================
    # BANNER PRINCIPAL
    # ========================================================

    def create_banner(self) -> None:
        if self.content is None:
            return

        banner = ctk.CTkFrame(
            self.content,
            corner_radius=16,
            fg_color=COLORS["panel"],
            border_width=1,
            border_color=COLORS["border"],
        )

        banner.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 14),
        )

        background_path = (
            BACKGROUND_DIR / "home.png"
        )

        if background_path.exists():
            image = Image.open(
                background_path
            )

            self.background_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(790, 560),
            )

            ctk.CTkLabel(
                banner,
                text="",
                image=self.background_image,
            ).place(
                x=0,
                y=0,
                relwidth=1,
                relheight=1,
            )

        overlay = ctk.CTkFrame(
            banner,
            width=470,
            height=315,
            corner_radius=18,
            fg_color="#11141b",
            border_width=1,
            border_color=COLORS["border"],
        )

        overlay.place(
            relx=0.06,
            rely=0.56,
            anchor="w",
        )

        overlay.pack_propagate(False)

        ctk.CTkLabel(
            overlay,
            text="VOXELFLY LAUNCHER",
            font=ctk.CTkFont(
                size=12,
                weight="bold",
            ),
            text_color=COLORS["orange"],
        ).pack(
            anchor="w",
            padx=28,
            pady=(26, 4),
        )

        ctk.CTkLabel(
            overlay,
            text="AVENTURA CÚBICA",
            font=ctk.CTkFont(
                size=36,
                weight="bold",
            ),
            text_color=COLORS["text"],
        ).pack(
            anchor="w",
            padx=28,
        )

        ctk.CTkLabel(
            overlay,
            text=(
                "Selecciona cualquier versión disponible, elige\n"
                "Vanilla, Fabric, Forge o NeoForge y prepara\n"
                "tu próxima partida."
            ),
            justify="left",
            font=ctk.CTkFont(
                size=14
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=28,
            pady=(12, 24),
        )

        buttons = ctk.CTkFrame(
            overlay,
            fg_color="transparent",
        )

        buttons.pack(
            anchor="w",
            padx=28,
        )

        self.banner_play_button = ctk.CTkButton(
            buttons,
            text="▶  JUGAR",
            width=155,
            height=46,
            corner_radius=10,
            fg_color=COLORS["orange"],
            hover_color=COLORS["orange_hover"],
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
            command=self.play,
        )

        self.banner_play_button.pack(
            side="left",
            padx=(0, 10),
        )

        ctk.CTkButton(
            buttons,
            text="⚙  CONFIGURAR",
            width=150,
            height=46,
            corner_radius=10,
            fg_color=COLORS["panel"],
            hover_color=COLORS["panel_hover"],
            border_width=1,
            border_color=COLORS["border"],
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            command=self.show_settings,
        ).pack(
            side="left"
        )

    # ========================================================
    # SELECTOR DE PERFIL, VERSIÓN Y RAM
    # ========================================================

    def create_profiles_panel(self) -> None:
        if self.content is None:
            return

        panel = ctk.CTkScrollableFrame(
            self.content,
            width=315,
            corner_radius=16,
            fg_color=COLORS["panel"],
            border_width=1,
            border_color=COLORS["border"],
            scrollbar_button_color=COLORS["purple"],
            scrollbar_button_hover_color=(
                COLORS["purple_hover"]
            ),
        )

        panel.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        ctk.CTkLabel(
            panel,
            text="PERFIL DE JUEGO",
            font=ctk.CTkFont(
                size=17,
                weight="bold",
            ),
            text_color=COLORS["text"],
        ).pack(
            anchor="w",
            padx=20,
            pady=(22, 4),
        )

        ctk.CTkLabel(
            panel,
            text="Elige cargador, versión y memoria RAM",
            font=ctk.CTkFont(
                size=12
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20),
        )

        # Tipo de instalación.

        ctk.CTkLabel(
            panel,
            text="TIPO DE INSTALACIÓN",
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=20,
        )

        self.loader_menu = ctk.CTkOptionMenu(
            panel,
            values=list(LOADERS.keys()),
            variable=self.selected_loader,
            height=44,
            corner_radius=10,
            fg_color=COLORS["panel_alt"],
            button_color=COLORS["purple"],
            button_hover_color=COLORS["purple_hover"],
            dropdown_fg_color=COLORS["panel"],
            dropdown_hover_color=COLORS["panel_hover"],
            command=self.on_loader_changed,
        )

        self.loader_menu.pack(
            fill="x",
            padx=20,
            pady=(7, 18),
        )

        # Versión.

        ctk.CTkLabel(
            panel,
            text="VERSIÓN DE MINECRAFT",
            font=ctk.CTkFont(
                size=11,
                weight="bold",
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=20,
        )

        self.version_menu = ctk.CTkOptionMenu(
            panel,
            values=["Cargando..."],
            variable=self.selected_version,
            height=44,
            corner_radius=10,
            fg_color=COLORS["panel_alt"],
            button_color=COLORS["purple"],
            button_hover_color=COLORS["purple_hover"],
            dropdown_fg_color=COLORS["panel"],
            dropdown_hover_color=COLORS["panel_hover"],
            command=self.on_version_changed,
        )

        self.version_menu.pack(
            fill="x",
            padx=20,
            pady=(7, 18),
        )

        # Descripción del cargador.

        info_card = ctk.CTkFrame(
            panel,
            corner_radius=10,
            fg_color=COLORS["panel_alt"],
            border_width=1,
            border_color=COLORS["border"],
        )

        info_card.pack(
            fill="x",
            padx=20,
            pady=(2, 12),
        )

        self.profile_description = ctk.CTkLabel(
            info_card,
            text=LOADERS[
                self.selected_loader.get()
            ]["description"],
            justify="left",
            wraplength=245,
            font=ctk.CTkFont(
                size=12
            ),
            text_color=COLORS["muted"],
        )

        self.profile_description.pack(
            anchor="w",
            padx=14,
            pady=12,
        )

        # Selector de RAM.

        memory_card = ctk.CTkFrame(
            panel,
            corner_radius=10,
            fg_color=COLORS["panel_alt"],
            border_width=1,
            border_color=COLORS["border"],
        )

        memory_card.pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

        ctk.CTkLabel(
            memory_card,
            text="MEMORIA RAM",
            font=ctk.CTkFont(
                size=10,
                weight="bold",
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=14,
            pady=(10, 2),
        )

        self.memory_label = ctk.CTkLabel(
            memory_card,
            text=self.memory_text(),
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=COLORS["text"],
        )

        self.memory_label.pack(
            anchor="w",
            padx=14,
        )

        slider_steps = max(
            1,
            int(
                (
                    self.maximum_ram_mb
                    - 2048
                )
                / 512
            ),
        )

        self.memory_slider = ctk.CTkSlider(
            memory_card,
            from_=2048,
            to=self.maximum_ram_mb,
            number_of_steps=slider_steps,
            variable=self.memory_value,
            command=self.update_memory,
            progress_color=COLORS["purple"],
            button_color=COLORS["purple"],
            button_hover_color=COLORS["purple_hover"],
        )

        self.memory_slider.pack(
            fill="x",
            padx=14,
            pady=(8, 10),
        )

        preset_frame = ctk.CTkFrame(
            memory_card,
            fg_color="transparent",
        )

        preset_frame.pack(
            fill="x",
            padx=14,
            pady=(0, 10),
        )

        preset_values = [
            2048,
            4096,
            6144,
            8192,
        ]

        for memory_mb in preset_values:
            if memory_mb > self.maximum_ram_mb:
                continue

            ctk.CTkButton(
                preset_frame,
                text=f"{memory_mb // 1024} GB",
                width=54,
                height=28,
                corner_radius=8,
                fg_color="#292e39",
                hover_color=COLORS["purple"],
                font=ctk.CTkFont(
                    size=11,
                    weight="bold",
                ),
                command=(
                    lambda value=memory_mb:
                    self.set_memory_preset(value)
                ),
            ).pack(
                side="left",
                padx=(0, 6),
            )

        ctk.CTkLabel(
            memory_card,
            text=(
                f"RAM detectada: "
                f"{self.total_ram_mb / 1024:.1f} GB"
            ),
            font=ctk.CTkFont(
                size=10
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=14,
            pady=(0, 10),
        )

        # Resumen.

        summary_card = ctk.CTkFrame(
            panel,
            corner_radius=10,
            fg_color="#14171e",
            border_width=1,
            border_color=COLORS["border"],
        )

        summary_card.pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

        ctk.CTkLabel(
            summary_card,
            text="SELECCIÓN ACTUAL",
            font=ctk.CTkFont(
                size=10,
                weight="bold",
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=14,
            pady=(10, 2),
        )

        self.selected_summary = ctk.CTkLabel(
            summary_card,
            text="Consultando versiones...",
            justify="left",
            font=ctk.CTkFont(
                size=13,
                weight="bold",
            ),
            text_color=COLORS["purple"],
        )

        self.selected_summary.pack(
            anchor="w",
            padx=14,
            pady=(0, 10),
        )

        self.play_profile_button = ctk.CTkButton(
            panel,
            text="CARGANDO VERSIONES...",
            height=54,
            corner_radius=10,
            fg_color=COLORS["green"],
            hover_color=COLORS["green_hover"],
            font=ctk.CTkFont(
                size=14,
                weight="bold",
            ),
            state="disabled",
            command=self.play,
        )

        self.play_profile_button.pack(
            fill="x",
            padx=20,
            pady=(0, 24),
        )

        if self.versions_loaded:
            self.update_version_menu()
        else:
            self.load_versions_async()

    # ========================================================
    # CARGA DE VERSIONES
    # ========================================================

    def load_versions_async(self) -> None:
        if self.loading_versions:
            return

        self.loading_versions = True

        self.set_status(
            "Consultando versiones de Minecraft..."
        )

        threading.Thread(
            target=self.fetch_all_versions,
            daemon=True,
        ).start()

    def fetch_all_versions(self) -> None:
        try:
            versions: dict[str, list[str]] = {
                "Vanilla": (
                    self.fetch_vanilla_versions()
                ),
                "Fabric": (
                    self.fetch_mod_loader_versions(
                        "fabric"
                    )
                ),
                "Forge": (
                    self.fetch_mod_loader_versions(
                        "forge"
                    )
                ),
                "NeoForge": (
                    self.fetch_mod_loader_versions(
                        "neoforge"
                    )
                ),
            }

        except Exception as error:
            error_text = str(error)

            self.after(
                0,
                lambda: self.show_version_error(
                    error_text
                ),
            )

            return

        self.after(
            0,
            lambda: self.finish_loading_versions(
                versions
            ),
        )

    def fetch_vanilla_versions(
        self,
    ) -> list[str]:
        version_information = (
            minecraft_launcher_lib.utils
            .get_version_list()
        )

        versions: list[str] = []

        for item in version_information:
            version_id = item.get("id")

            if not version_id:
                continue

            if version_id not in versions:
                versions.append(
                    version_id
                )

        return versions

    def fetch_mod_loader_versions(
        self,
        loader_id: str,
    ) -> list[str]:
        loader_ids = (
            minecraft_launcher_lib.mod_loader
            .list_mod_loader()
        )

        if loader_id not in loader_ids:
            return []

        mod_loader = (
            minecraft_launcher_lib.mod_loader
            .get_mod_loader(loader_id)
        )

        versions = (
            mod_loader.get_minecraft_versions(
                False
            )
        )

        return list(
            dict.fromkeys(versions)
        )

    def finish_loading_versions(
        self,
        versions: dict[str, list[str]],
    ) -> None:
        self.available_versions = versions
        self.versions_loaded = True
        self.loading_versions = False

        self.update_version_menu()

        self.set_status(
            "Versiones cargadas correctamente"
        )

    def show_version_error(
        self,
        error_text: str,
    ) -> None:
        self.loading_versions = False
        self.versions_loaded = False

        self.selected_version.set(
            "No disponible"
        )

        if self.version_menu is not None:
            self.version_menu.configure(
                values=["No disponible"]
            )

        if self.play_profile_button is not None:
            self.play_profile_button.configure(
                text="NO SE PUDIERON CARGAR",
                state="disabled",
            )

        if self.selected_summary is not None:
            self.selected_summary.configure(
                text=(
                    "No se pudieron obtener "
                    "las versiones."
                )
            )

        self.set_status(
            f"Error al cargar versiones: "
            f"{error_text}"
        )

    # ========================================================
    # EVENTOS DE LOS SELECTORES
    # ========================================================

    def on_loader_changed(
        self,
        loader_name: str,
    ) -> None:
        self.selected_loader.set(
            loader_name
        )

        if self.profile_description is not None:
            self.profile_description.configure(
                text=LOADERS[
                    loader_name
                ]["description"]
            )

        self.update_version_menu()

    def update_version_menu(self) -> None:
        loader_name = (
            self.selected_loader.get()
        )

        versions = self.available_versions.get(
            loader_name,
            [],
        )

        if not versions:
            versions = ["No disponible"]

        if self.version_menu is not None:
            self.version_menu.configure(
                values=versions
            )

        self.selected_version.set(
            versions[0]
        )

        self.refresh_profile_information()

    def on_version_changed(
        self,
        version: str,
    ) -> None:
        self.selected_version.set(
            version
        )

        self.refresh_profile_information()

        self.set_status(
            f"Seleccionado: "
            f"{self.selected_loader.get()} "
            f"{version}"
        )

    def refresh_profile_information(
        self,
    ) -> None:
        loader_name = (
            self.selected_loader.get()
        )

        version = (
            self.selected_version.get()
        )

        memory_gb = (
            self.memory_value.get()
            / 1024
        )

        if self.selected_summary is not None:
            self.selected_summary.configure(
                text=(
                    f"{loader_name}\n"
                    f"Minecraft {version}\n"
                    f"RAM: {memory_gb:.1f} GB"
                )
            )

        if self.play_profile_button is None:
            return

        if version in {
            "Cargando...",
            "No disponible",
        }:
            self.play_profile_button.configure(
                text="VERSIÓN NO DISPONIBLE",
                state="disabled",
            )

            return

        self.play_profile_button.configure(
            text=self.profile_play_button_text(),
            state="normal",
        )

    # ========================================================
    # NAVEGACIÓN
    # ========================================================

    def show_home(self) -> None:
        if self.content is None:
            return

        self.clear_content()

        self.content.grid_rowconfigure(
            0,
            weight=1,
        )

        self.content.grid_columnconfigure(
            0,
            weight=3,
        )

        self.content.grid_columnconfigure(
            1,
            weight=1,
        )

        self.create_banner()
        self.create_profiles_panel()

        self.set_status(
            "Inicio"
        )

    def show_profiles(self) -> None:
        self.show_simple_screen(
            title="Perfiles",
            description=(
                "Aquí podrás guardar varias configuraciones "
                "con distintas versiones, cargadores, mods "
                "y memoria RAM."
            ),
        )

    def show_mods(self) -> None:
        if self.content is None:
            return

        self.clear_content()

        self.content.grid_rowconfigure(
            0,
            weight=1,
        )

        self.content.grid_columnconfigure(
            0,
            weight=1,
        )

        mod_browser = ModBrowserFrame(
            self.content,
            loader_getter=self.selected_loader.get,
            version_getter=self.selected_version.get,
            status_callback=self.set_status,
        )

        mod_browser.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        self.set_status(
            "Navegador de mods abierto."
        )

    def show_settings(self) -> None:
        self.show_simple_screen(
            title="Ajustes",
            description=(
                "Aquí configuraremos la memoria RAM, Java, "
                "carpeta del juego y argumentos JVM."
            ),
        )

    def show_simple_screen(
        self,
        title: str,
        description: str,
    ) -> None:
        if self.content is None:
            return

        self.clear_content()

        panel = ctk.CTkFrame(
            self.content,
            corner_radius=16,
            fg_color=COLORS["panel"],
            border_width=1,
            border_color=COLORS["border"],
        )

        panel.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        ctk.CTkLabel(
            panel,
            text=title,
            font=ctk.CTkFont(
                size=38,
                weight="bold",
            ),
            text_color=COLORS["text"],
        ).pack(
            anchor="w",
            padx=40,
            pady=(40, 10),
        )

        ctk.CTkLabel(
            panel,
            text=description,
            justify="left",
            wraplength=700,
            font=ctk.CTkFont(
                size=16
            ),
            text_color=COLORS["muted"],
        ).pack(
            anchor="w",
            padx=40,
        )

        self.set_status(
            title
        )

    # ========================================================
    # ACCIONES TEMPORALES
    # ========================================================

    def play(self) -> None:
        if self.installing_game:
            self.set_status(
                "Ya hay una instalación en proceso."
            )
            return

        loader_name = self.selected_loader.get()
        version = self.selected_version.get()
        memory_mb = self.memory_value.get()

        if version in {
            "Cargando...",
            "No disponible",
        }:
            self.set_status(
                "Selecciona una versión válida."
            )
            return

        self.installing_game = True
        self.install_progress_max = 0
        self.set_play_buttons_enabled(False)

        self.set_status(
            f"Preparando {loader_name} "
            f"{version} con "
            f"{memory_mb / 1024:.1f} GB..."
        )

        threading.Thread(
            target=self.install_and_launch_worker,
            args=(loader_name, version, memory_mb),
            daemon=True,
        ).start()

    def set_play_buttons_enabled(
        self,
        enabled: bool,
    ) -> None:
        state = "normal" if enabled else "disabled"

        if self.banner_play_button is not None:
            self.banner_play_button.configure(
                state=state,
                text=(
                    "▶  JUGAR"
                    if enabled
                    else "INSTALANDO..."
                ),
            )

        if self.play_profile_button is not None:
            self.play_profile_button.configure(
                state=state,
                text=(
                    self.profile_play_button_text()
                    if enabled
                    else "INSTALANDO..."
                ),
            )

    def profile_play_button_text(self) -> str:
        return (
            f"JUGAR {self.selected_loader.get().upper()} "
            f"{self.selected_version.get()}"
        )

    def install_and_launch_worker(
        self,
        loader_name: str,
        version: str,
        memory_mb: int,
    ) -> None:
        callback = {
            "setStatus": self.install_status_callback,
            "setProgress": self.install_progress_callback,
            "setMax": self.install_max_callback,
        }

        try:
            result = self.minecraft_manager.install_and_launch(
                loader_name=loader_name,
                minecraft_version=version,
                memory_mb=memory_mb,
                callback=callback,
            )
        except Exception as error:
            error_text = str(error)
            self.after(
                0,
                lambda: self.finish_installation_error(
                    error_text
                ),
            )
            return

        self.after(
            0,
            lambda: self.finish_installation_success(
                result
            ),
        )

    def install_status_callback(
        self,
        status: str,
    ) -> None:
        self.after(
            0,
            lambda: self.set_status(
                str(status)
            ),
        )

    def install_max_callback(
        self,
        maximum: int,
    ) -> None:
        self.install_progress_max = max(
            int(maximum),
            0,
        )

    def install_progress_callback(
        self,
        progress: int,
    ) -> None:
        current = int(progress)
        maximum = self.install_progress_max

        if maximum > 0:
            percentage = min(
                100,
                int(current / maximum * 100),
            )
            message = (
                f"Descargando archivos: "
                f"{percentage}% "
                f"({current}/{maximum})"
            )
        else:
            message = (
                f"Descargando archivos: {current}"
            )

        self.after(
            0,
            lambda: self.set_status(message),
        )

    def finish_installation_success(
        self,
        result: LaunchResult,
    ) -> None:
        self.installing_game = False
        self.set_play_buttons_enabled(True)

        if result.launched:
            self.set_status(result.message)
            return

        self.set_status(
            f"Instalado: {result.installed_version}. "
            f"{result.message}"
        )

    def finish_installation_error(
        self,
        error_text: str,
    ) -> None:
        self.installing_game = False
        self.set_play_buttons_enabled(True)

        self.set_status(
            f"Error al instalar o iniciar: "
            f"{error_text}"
        )

    def open_account(self) -> None:
        self.set_status(
            "Inicio de sesión con Microsoft pendiente"
        )


def start_app() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = VoxelFlyApp()
    app.mainloop()