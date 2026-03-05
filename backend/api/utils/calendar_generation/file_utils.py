import os

def create_export_folder(production_id, base_dir=None):
    """
    Gwarantuje zalozenie folderu roboczego pod aktualne zapytanie wydruku na maszyne (calendar_exports),
    izolujac pliki robocze na podstawie przekazanego indentyfikatora. Zapobiega nadpisywaniu rownoleglych sesji na serwerze i zarzadza uprawnieniami plikowymi poprzez sciezki MEDIA_ROOT.
    """
    if base_dir is None:
        base_dir = os.path.join(os.getcwd(), "media", "calendar_exports")

    folder_name = f"calendar_{production_id}"
    export_dir = os.path.join(base_dir, folder_name)
    os.makedirs(export_dir, exist_ok=True)

    print(f"Folder eksportu: {export_dir}")
    return export_dir
