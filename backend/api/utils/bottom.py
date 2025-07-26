from PIL import Image, ImageDraw, ImageFilter, ImageStat

def extend_to_aspect_31x81(image_path, output_path, mist_opacity=120, transition_height=300):
    img = Image.open(image_path).convert("RGB")
    orig_w, orig_h = img.size

    # 🔸 Oblicz docelową wysokość (31:81 proporcja)
    final_h = int(orig_w * (81 / 31))
    bottom_extension_height = final_h - orig_h
    if bottom_extension_height <= 0:
        raise ValueError(f"Obraz już spełnia lub przekracza proporcję 31:81 ({orig_h}px vs {final_h}px)")

    # 🔸 Średni kolor z dołu oryginału
    sample = img.crop((0, orig_h - 50, orig_w, orig_h))
    avg_color = tuple(int(x) for x in ImageStat.Stat(sample).mean[:3])

    # 🔸 Jednolite tło w kolorze dołu
    base = Image.new("RGB", (orig_w, bottom_extension_height), avg_color)

    # 🔸 Warstwa mgły: biały gradient (RGB, nieprzezroczysty)
    mist_layer = Image.new("RGB", (orig_w, bottom_extension_height), avg_color)
    draw = ImageDraw.Draw(mist_layer)
    for y in range(bottom_extension_height):
        blend_color = int(255 * (y / bottom_extension_height))
        draw.line([(0, y), (orig_w, y)], fill=(blend_color, blend_color, blend_color))

    # 🔸 Blend: tło + mgła (np. 120/255 = ~47%)
    blended = Image.blend(base, mist_layer, alpha=mist_opacity / 255.0)

    # 🔸 Rozmycie
    blurred_bottom = blended.filter(ImageFilter.GaussianBlur(radius=6))

    # 🔸 Maska przejścia (gradient)
    transition_height = min(transition_height, orig_h)
    transition_mask = Image.new("L", (orig_w, transition_height), 0)
    mask_draw = ImageDraw.Draw(transition_mask)
    for y in range(transition_height):
        alpha = int(255 * (y / transition_height))
        mask_draw.line([(0, y), (orig_w, y)], fill=alpha)

    # 🔸 Wytnij z oryginału + blur
    orig_bottom = img.crop((0, orig_h - transition_height, orig_w, orig_h))
    blur_top = blurred_bottom.crop((0, 0, orig_w, transition_height))
    blended_transition = Image.composite(blur_top, orig_bottom, transition_mask)

    # 🔸 Złożenie wszystkiego
    result = Image.new("RGB", (orig_w, final_h))
    result.paste(img.crop((0, 0, orig_w, orig_h - transition_height)), (0, 0))
    result.paste(blended_transition, (0, orig_h - transition_height))
    result.paste(blurred_bottom.crop((0, transition_height, orig_w, bottom_extension_height)), (0, orig_h))

    result.save(output_path)
    print(f"✅ Gotowe: {output_path} ({orig_w}px × {final_h}px) – proporcja 31:81 bez czarnego paska.")
