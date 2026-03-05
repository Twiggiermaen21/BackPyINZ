from PIL import Image
import math
from .pdf_utils import hex_to_rgb

def create_gradient_vertical(size, start_rgb, end_rgb):
    """
    Generuje prosty gradient pionowy miedzy dwiema stalymi stanowiacymi RGB.
    Tworzy mape jednopikselowa i interpoluje ja na pelny rozmiar przy uzyciu algorytmu BICUBIC.
    """
    width, height = size
    gradient_h = 256
    base = Image.new('RGB', (1, gradient_h))
    pixels = base.load()
    
    for y in range(gradient_h):
        t = y / (gradient_h - 1)
        pixels[0, y] = interpolate_color(start_rgb, end_rgb, t)
        
    return base.resize((width, height), Image.Resampling.BICUBIC)

def create_radial_gradient_css(size, start_rgb, end_rgb, center=(0.5, 0.5), offset_y=0):
    """
    Tworzy promienisty (radialny) gradient okregowy ze srodkiem ustawianym parametrem (domyslnie srodek). 
    Rozchodzi w sposob gladki dzieki algorytmowi LANCZOS.
    """
    width, height = size
    
    small_w = 400
    small_h = int(400 * (height / width))
    
    base = Image.new('RGB', (small_w, small_h))
    pixels = base.load()
    
    relative_offset = offset_y / height
    target_cy_normalized = center[1] + relative_offset
    
    cx = int(small_w * center[0])
    cy = int(small_h * target_cy_normalized)
    
    max_dist = math.sqrt(max(cx, small_w - cx)**2 + max(cy, small_h - cy)**2)
    if max_dist == 0: max_dist = 1
    
    for y in range(small_h):
        for x in range(small_w):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            t = min(dist / max_dist, 1.0)
            pixels[x, y] = interpolate_color(start_rgb, end_rgb, t)
            
    return base.resize((width, height), Image.Resampling.LANCZOS)

def interpolate_color(start_rgb, end_rgb, factor):
    """Wylicza punkt posredni miedzy dwoma barwami RGB ze wskazana intensywnoscia przejscia (factor 0.0 do 1.0)."""
    return tuple(int(start + (end - start) * factor) for start, end in zip(start_rgb, end_rgb))

def create_waves_css(size, start_rgb, end_rgb):
    """
    Buduje zapetlony gradient ze stylistyka "fal". Interpoluje kolory z ciaglym powielaniem bazowej tekstury w tle.
    """
    w, h = size
    
    diagonal = math.sqrt(w**2 + h**2)
    canvas_side = int(diagonal * 1.5) 
    cycle_height = int(diagonal * 0.40)
    if cycle_height < 10: cycle_height = 10

    strip_h = 256
    strip = Image.new('RGB', (1, strip_h))
    px = strip.load()
    
    for y in range(strip_h):
        t = y / (strip_h - 1)
        if t <= 0.5:
            local_t = t * 2
            px[0, y] = interpolate_color(start_rgb, end_rgb, local_t)
        else:
            local_t = (t - 0.5) * 2
            px[0, y] = interpolate_color(end_rgb, start_rgb, local_t)
            
    cycle_img = strip.resize((canvas_side, cycle_height), Image.Resampling.BICUBIC)
    
    repeats = (canvas_side // cycle_height) + 2
    full_pattern = Image.new('RGB', (canvas_side, cycle_height * repeats))
    
    for i in range(repeats):
        full_pattern.paste(cycle_img, (0, i * cycle_height))
        
    rotated = full_pattern.rotate(45, resample=Image.Resampling.BICUBIC, expand=False)
    
    center_x, center_y = rotated.width // 2, rotated.height // 2
    left = center_x - w // 2
    top = center_y - h // 2
    
    return rotated.crop((left, top, left + w, top + h))


def create_liquid_css(size, start_rgb, end_rgb):
    """
    Tworzy gladki diagonalny (135 stopni) gradient przypominajacy "plynne" nachylenie kolorow 
    z wykorzystaniem narzedzia do obrotu wygenerowanego pasma miedzy katami.
    """
    w, h = size
    diagonal = int(math.sqrt(w**2 + h**2))
    
    grad = create_gradient_vertical((diagonal, diagonal), start_rgb, end_rgb)
    rotated = grad.rotate(-45, resample=Image.Resampling.BICUBIC)
    
    center_x, center_y = rotated.width // 2, rotated.height // 2
    left = center_x - w // 2
    top = center_y - h // 2
    return rotated.crop((left, top, left + w, top + h))

def generate_bottom_bg_image(width, height, bg_color, end_color, theme, variant):
    """
    Orkiestrator kompozycji tla dla sekcji dolnej plecow kalendarza. Przetwarza wariant i wlasciwosci (theme) 
    zapisane w modelu na stosowna metodoche gradientowa i wyciaga gotowy obraz RGB.
    """
    rgb_start = hex_to_rgb(bg_color)
    rgb_end = hex_to_rgb(end_color)

    if theme == "aurora":
        return create_radial_gradient_css((width, height), rgb_start, rgb_end, center=(0.3, 0.3))
        
    elif theme == "liquid":
        return create_liquid_css((width, height), rgb_start, rgb_end)
        
    elif theme == "waves":
        return create_waves_css((width, height), rgb_start, rgb_end)
        
    else:
        if variant == "horizontal":
            grad = create_gradient_vertical((height, width), rgb_start, rgb_end)
            return grad.rotate(90, expand=True)
            
        elif variant == "radial":
            return create_radial_gradient_css((width, height), rgb_start, rgb_end, center=(0.5, 0.5))
            
        elif variant == "diagonal":
            return create_liquid_css((width, height), rgb_start, rgb_end)
            
        else: 
            return create_gradient_vertical((width, height), rgb_start, rgb_end)
