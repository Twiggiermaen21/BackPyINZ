import os
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_calendar_composition(top_filename, month_filename, output_filename):
    DPI = 150
    calendar_width_cm = 31
    calendar_height_cm = 81

    width = int(calendar_width_cm * DPI / 2.54)
    height = int(calendar_height_cm * DPI / 2.54)

    top_path = os.path.join(BASE_DIR, "images", top_filename)
    top_image = Image.open(top_path)
    month_path = os.path.join(BASE_DIR, "CAL_PARTS", month_filename)
    month_image = Image.open(month_path)

    new_image = Image.new("RGB", (width, height), "white")

    y_offset = 0
    top_height = int(21 * DPI / 2.54)
    gap_height_top = int(0.9 * DPI / 2.54)
    month_height = int(12.4 * DPI / 2.54)
    gap_height_bottom = int(1.6 * DPI / 2.54)
    text_area_height = int(4.9 * DPI / 2.54)
    left_offset = int(1.5 * DPI / 2.54)  # 1.5 cm margines

    # Wklejanie główki
    top_resized = top_image.resize((width, top_height))
    new_image.paste(top_resized, (0, y_offset))
    y_offset += top_height + gap_height_top

    # Trzy sekcje
    for i in range(3):
        # Kartka miesiąca z marginesami
        month_resized = month_image.resize((width - 2 * left_offset, month_height))
        new_image.paste(month_resized, (left_offset, y_offset))
        y_offset += month_height + gap_height_top

        # Pole wolne z tymi samymi marginesami
        draw = ImageDraw.Draw(new_image)
        draw.rectangle(
            [(left_offset, y_offset), (width - left_offset, y_offset + text_area_height)],
            outline="lightgray",
            width=2
        )
        y_offset += text_area_height + gap_height_bottom

    # Zapis do pliku
    output_dir = os.path.join(BASE_DIR, "CAL_IMG")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    new_image.save(output_path, dpi=(DPI, DPI))
    print(f"Saved final calendar header to {output_path}")

    return output_path
