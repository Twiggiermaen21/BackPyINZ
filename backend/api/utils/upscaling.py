import os
from PIL import Image
from bigjpg import Bigjpg, Styles, Noises, EnlargeValues

def upscale_image_with_bigjpg(image_url,export_dir):
    bigjpg = Bigjpg("7636406dfd0e4876ab57c95199cc1d75")

    # Wywołaj API bigjpg
    image_info = bigjpg.enlarge(
        style=Styles.Art,
        noise=Noises.Highest,
        enlarge_value=EnlargeValues._4x,
        image_url=image_url
    )

    

    # Znajdź numerację
    existing_files = os.listdir(export_dir)
    existing_numbers = []
    for filename in existing_files:
        if filename.startswith("enlarged_image_") and filename.endswith(".png"):
            num_part = filename[len("enlarged_image_"):-4]
            if num_part.isdigit():
                existing_numbers.append(int(num_part))
    next_number = max(existing_numbers, default=0) + 1

    # Ścieżka zapisu x4
    upscaled_path = os.path.join(export_dir, f"enlarged_image_{next_number}.png")
    image_info.download(upscaled_path)
    print(f"✅ Image saved to: {upscaled_path}")

    # Katalog na wersję 300dpi
    # dpi_dir = "300dpi"
    # os.makedirs(dpi_dir, exist_ok=True)

    # dpi_path = os.path.join(dpi_dir, f"enlarged_image_{next_number}.png")

    # Zapis z DPI=300
    # img = Image.open(upscaled_path)
    # img.save(dpi_path, dpi=(300, 300))
    # print(f"✅ Saved 300 DPI to: {dpi_path}")

    return {
        "bigjpg_url": image_info.get_url(),
        "local_upscaled": upscaled_path,
        # "local_300dpi": dpi_path
    }