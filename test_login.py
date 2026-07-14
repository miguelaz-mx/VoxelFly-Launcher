from auth import microsoft_login


def main() -> None:
    print("==============================")
    print("   Prueba de inicio VoxelFly")
    print("==============================")

    try:
        account = microsoft_login()

    except Exception as error:
        print("\nNo se pudo iniciar sesión.")
        print(f"Error: {error}")
        return

    print("\n==============================")
    print("Inicio de sesión correcto")
    print("==============================")

    print(f"Nombre: {account['name']}")
    print(f"UUID: {account['id']}")

    skins = account.get("skins", [])

    if skins:
        print(f"Skin: {skins[0].get('url', 'No disponible')}")
    else:
        print("Skin: No se encontró una skin activa.")

    print("\nLa sesión quedó guardada.")


if __name__ == "__main__":
    main()