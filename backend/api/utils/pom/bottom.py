from PIL import Image, ImageDraw, ImageFilter, ImageStat, ImageChops
import math

# ---------------------------------------------------------
# 🛠️ FUNKCJE POMOCNICZE (Odwzorowanie logiki CSS w PIL)
# ---------------------------------------------------------

def hex_to_rgb(hex_color):
    """Zamienia hex string (np. #ffffff) na tuple (255, 255, 255)."""
    if not isinstance(hex_color, str):
        return (255, 255, 255) # Fallback na biały
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)

def create_linear_gradient(size, start_color, end_color, direction='vertical'):
    """Generuje gradient liniowy."""
    width, height = size
    base = Image.new('RGB', size)
    draw = ImageDraw.Draw(base)

    if direction == 'vertical':
        for y in range(height):
            r = start_color[0] + (end_color[0] - start_color[0]) * y / height
            g = start_color[1] + (end_color[1] - start_color[1]) * y / height
            b = start_color[2] + (end_color[2] - start_color[2]) * y / height
            draw.line([(0, y), (width, y)], fill=(int(r), int(g), int(b)))
            
    elif direction == 'horizontal':
        for x in range(width):
            r = start_color[0] + (end_color[0] - start_color[0]) * x / width
            g = start_color[1] + (end_color[1] - start_color[1]) * x / width
            b = start_color[2] + (end_color[2] - start_color[2]) * x / width
            draw.line([(x, 0), (x, height)], fill=(int(r), int(g), int(b)))
            
    elif direction == 'diagonal' or direction == '135deg' or direction == '120deg':
        # Aproksymacja gradientu diagonalnego (Top-Left -> Bottom-Right)
        # Dla dokładnych kątów należałoby obrócić obraz, ale to wystarczy do symulacji CSS
        for y in range(height):
            for x in range(width):
                ratio = (x / width + y / height) / 2
                r = start_color[0] + (end_color[0] - start_color[0]) * ratio
                g = start_color[1] + (end_color[1] - start_color[1]) * ratio
                b = start_color[2] + (end_color[2] - start_color[2]) * ratio
                draw.point((x, y), fill=(int(r), int(g), int(b)))
                
    return base

def create_radial_gradient(size, start_color, end_color, center=(0.5, 0.5)):
    """Generuje gradient radialny."""
    width, height = size
    cx, cy = int(width * center[0]), int(height * center[1])
    # Maksymalny promień (do najdalszego rogu)
    max_dist = math.sqrt(max(cx, width-cx)**2 + max(cy, height-cy)**2)
    
    base = Image.new('RGB', size)
    pixels = base.load()
    
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            ratio = min(dist / max_dist, 1.0)
            
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            pixels[x, y] = (r, g, b)
            
    return base

def create_waves_pattern(size, start_color, end_color):
    """Symuluje CSS repeating-linear-gradient (waves)."""
    width, height = size
    base = Image.new('RGB', size, start_color)
    draw = ImageDraw.Draw(base)
    
    # Rysujemy pasy co 40px (symulacja 20% -> 40% w CSS)
    step = 40 
    for i in range(-height, width + height, step):
        draw.line([(i, 0), (i + height, height)], fill=end_color, width=step//2)
        
    return base

# ---------------------------------------------------------
# 🎨 GŁÓWNA LOGIKA GENEROWANIA TŁA (odpowiednik getBottomSectionBackground)
# ---------------------------------------------------------

def generate_bottom_background(width, height, style="style1", 
                               bg_color="#ffffff", gradient_end_color="#ffffff",
                               gradient_theme="classic", gradient_variant="diagonal",
                               background_image_path=None):
    
    rgb_bg = hex_to_rgb(bg_color)
    rgb_end = hex_to_rgb(gradient_end_color)

    # === STYLE 1: Solid Color ===
    if style == "style1":
        return Image.new("RGB", (width, height), rgb_bg)

    # === STYLE 2: Gradients ===
    if style == "style2":
        # 1. Themes (Aurora, Liquid, Mesh, Waves)
        if gradient_theme != "classic":
            if gradient_theme == "aurora":
                # CSS: radial-gradient(circle at 30% 30%...)
                return create_radial_gradient((width, height), rgb_bg, rgb_end, center=(0.3, 0.3))
            
            elif gradient_theme == "liquid":
                # CSS: linear-gradient(135deg...)
                return create_linear_gradient((width, height), rgb_bg, rgb_end, direction='135deg')
            
            elif gradient_theme == "mesh":
                # CSS: linear-gradient(120deg...)
                return create_linear_gradient((width, height), rgb_bg, rgb_end, direction='120deg')
                
            elif gradient_theme == "waves":
                # CSS: repeating-linear-gradient...
                return create_waves_pattern((width, height), rgb_bg, rgb_end)
            
            else:
                return Image.new("RGB", (width, height), rgb_bg)

        # 2. Classic Variants
        else:
            if gradient_variant == "vertical":
                return create_linear_gradient((width, height), rgb_bg, rgb_end, direction='vertical')
            elif gradient_variant == "horizontal":
                return create_linear_gradient((width, height), rgb_bg, rgb_end, direction='horizontal')
            elif gradient_variant == "radial":
                return create_radial_gradient((width, height), rgb_bg, rgb_end, center=(0.5, 0.5))
            elif gradient_variant == "diagonal":
                return create_linear_gradient((width, height), rgb_bg, rgb_end, direction='diagonal')
            else:
                # Default diagonal
                return create_linear_gradient((width, height), rgb_bg, rgb_end, direction='diagonal')

    # === STYLE 3: Background Image ===
    if style == "style3" and background_image_path:
        try:
            bg_img = Image.open(background_image_path).convert("RGB")
            # Odpowiednik CSS: background-size: cover
            # Skalujemy obraz tak, aby wypełnił obszar (zachowując proporcje)
            bg_ratio = bg_img.width / bg_img.height
            target_ratio = width / height
            
            if bg_ratio > target_ratio:
                # Obraz szerszy niż cel -> tniemy boki
                resize_h = height
                resize_w = int(height * bg_ratio)
            else:
                # Obraz wyższy niż cel -> tniemy góra/dół
                resize_w = width
                resize_h = int(width / bg_ratio)
                
            bg_img = bg_img.resize((resize_w, resize_h), Image.Resampling.LANCZOS)
            
            # Center crop
            left = (resize_w - width) // 2
            top = (resize_h - height) // 2
            return bg_img.crop((left, top, left + width, top + height))
            
        except Exception as e:
            print(f"⚠️ Nie udało się wczytać tła obrazkowego: {e}")
            return Image.new("RGB", (width, height), (255, 255, 255))

    # Fallback default
    return Image.new("RGB", (width, height), (255, 255, 255))


# ---------------------------------------------------------
# 🚀 GŁÓWNA FUNKCJA (ZMODYFIKOWANA)
# ---------------------------------------------------------

def extend_to_aspect_31x81(image_path, output_path, transition_height=300, 
                           # Nowe parametry sterujące wyglądem:
                           style="style2", 
                           bg_color="#6d8f91", 
                           gradient_end_color="#afe5e6",
                           gradient_theme="classic",
                           gradient_variant="vertical",
                           background_image_path=None):
    
    img = Image.open(image_path).convert("RGB")
    orig_w, orig_h = img.size

    # 🔸 Oblicz docelową wysokość (31:81 proporcja)
    final_h = int(orig_w * (81 / 31))
    bottom_extension_height = final_h - orig_h
    if bottom_extension_height <= 0:
        raise ValueError(f"Obraz już spełnia lub przekracza proporcję 31:81 ({orig_h}px vs {final_h}px)")

    # 🔸 GENEROWANIE TŁA (Zamiast mgły/average color)
    # Wywołujemy funkcję odwzorowującą logikę JS
    extension_layer = generate_bottom_background(
        width=orig_w, 
        height=bottom_extension_height,
        style=style,
        bg_color=bg_color,
        gradient_end_color=gradient_end_color,
        gradient_theme=gradient_theme,
        gradient_variant=gradient_variant,
        background_image_path=background_image_path
    )

    # 🔸 (Opcjonalnie) Maska przejścia (gradient alfa)
    # Żeby połączyć oryginalny obraz z nowym tłem płynnie, zachowujemy logikę blendowania
    # na styku obrazów.
    
    transition_height = min(transition_height, orig_h)
    
    # Przygotowanie maski przejścia
    transition_mask = Image.new("L", (orig_w, transition_height), 0)
    mask_draw = ImageDraw.Draw(transition_mask)
    for y in range(transition_height):
        # 0 (czarny) na górze przejścia -> 255 (biały) na dole przejścia
        alpha = int(255 * (y / transition_height))
        mask_draw.line([(0, y), (orig_w, y)], fill=alpha)

    # Wycinek dolnej części oryginału
    orig_bottom_strip = img.crop((0, orig_h - transition_height, orig_w, orig_h))
    
    # Wycinek górnej części nowego tła (o wysokości przejścia)
    new_bg_top_strip = extension_layer.crop((0, 0, orig_w, transition_height))
    
    # Nałożenie nowego tła na dół oryginału przy użyciu maski
    # To sprawi, że oryginał będzie płynnie zanikał w nowe tło
    blended_transition = Image.composite(new_bg_top_strip, orig_bottom_strip, transition_mask)

    # 🔸 Złożenie wszystkiego
    result = Image.new("RGB", (orig_w, final_h))
    
    # 1. Oryginał (bez dolnego paska przejścia)
    result.paste(img.crop((0, 0, orig_w, orig_h - transition_height)), (0, 0))
    
    # 2. Przejście (blend)
    result.paste(blended_transition, (0, orig_h - transition_height))
    
    # 3. Reszta nowego tła (poniżej przejścia)
    result.paste(extension_layer.crop((0, transition_height, orig_w, bottom_extension_height)), (0, orig_h))

    result.save(output_path)
    print(f"✅ Gotowe: {output_path} ({orig_w}px × {final_h}px) – Styl: {style}/{gradient_theme}")

