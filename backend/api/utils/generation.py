from itertools import count
import os
from dotenv import load_dotenv
from .prompt_generator import get_detailed_prompt_from_model
from .image_generator import generate_image
from together import Together

load_dotenv()

def generate_image_from_prompt(base_prompt, width, height,
                                inspiration, color, composition,
                                style, atmosfera=None, tlo=None, perspektywa=None,
                                detale=None, realizm=None, styl_narracyjny=None):
    api_key = os.getenv("TOGETHER_API_KEY")
    client = Together(api_key=api_key)
    
    detailed_prompt = get_detailed_prompt_from_model(
        client=client,
        base_prompt=base_prompt,
        inspiration=inspiration,
        color=color,
        composition=composition,
        style=style,
        atmosfera=atmosfera,
        tlo=tlo,
        perspektywa=perspektywa,
        detale=detale,
        realizm=realizm,
        styl_narracyjny=styl_narracyjny
    )

    if not detailed_prompt:
        raise ValueError("Failed to get detailed prompt.")
    image_bytes = generate_image(client, detailed_prompt, width, height)
    print(detailed_prompt)
    if not image_bytes:
        raise ValueError("Failed to generate image.")
    return image_bytes
