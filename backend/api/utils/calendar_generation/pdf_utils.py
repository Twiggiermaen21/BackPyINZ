import os
from PIL import Image, ImageCms

# sciezka do profilu ICC
CMYK_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "profiles", "FOGRA51_v3.icc")

def rgb_to_cmyk(pil_image):
    """
    Uzytkownik przesyla pliki i interfejs operuje domyslnie w systemie monitorowym (RGB - sRGB).
    Ta funkcja symuluje proces przejscia do druku profilu FOGRA51 uzywajac w tym celu narzedzia
    Zarzadzania Barwa ICC (ImageCms), co gwarantuje prawidlowe odwzorowanie finalnego druku w trybie CMYK.
    """
    if pil_image.mode == "CMYK":
        return pil_image
    
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    
    srgb_profile = ImageCms.createProfile("sRGB")
    cmyk_profile = ImageCms.getOpenProfile(CMYK_PROFILE_PATH)
    print(f"Konwersja RGB -> CMYK z profilem ICC: {CMYK_PROFILE_PATH}")
    
    transform = ImageCms.buildTransform(
        srgb_profile,
        cmyk_profile,
        "RGB",
        "CMYK",
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
        flags=ImageCms.FLAGS["BLACKPOINTCOMPENSATION"]
    )
    
    return ImageCms.applyTransform(pil_image, transform)

def save_as_pdf(pil_image, output_path):
    """
    Przejmuje zlozona matryce RGB (obraz PIL) ze spodem lub podkladem i jako koncowy punkt orkiestracji uruchamia 'rgb_to_cmyk',
    zapisujac zadanym wektorem rozdzielczosci na dysk ostateczny plik Portable Document Format (PDF) gotowy do produkcji.
    """
    cmyk_image = rgb_to_cmyk(pil_image)
    
    pdf_path = output_path.replace(".psd", ".pdf")
    cmyk_image.save(pdf_path, format="PDF", resolution=300.0)
    
    return pdf_path
