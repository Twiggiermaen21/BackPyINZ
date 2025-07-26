import os
from together import Together

def generate_custom_prompt(
    baseprompt,
    inspiration=None,
    color_style=None,
    composition=None,
    style=None,
    atmosfera=None,
    tlo=None,
    perspektywa=None,
    detale=None,
    realizm=None,
    styl_narracyjny=None
):
    prompt = (
        f"Create a complete and visually rich illustration inspired by the theme: {baseprompt}. "
        "Explore various artistic styles such as surrealist, watercolor, digital painting, retro-futurism, brutalism, baroque, minimalist, or others, and choose the one that best fits the theme. "
        "Emphasize the following aspects: "
        "1. A strong, detailed main subject placed in the upper half of the composition, evoking emotion, narrative, or symbolic meaning. "
        "2. A cohesive background environment that supports the mood and naturally flows downward, with elements gradually becoming simpler and softer toward the bottom. "
        "3. Clearly define the time of day, lighting conditions, and atmosphere to establish a distinct visual identity. "
        "4. Avoid visual noise or sharp contrasts in the lower part of the image; instead, use gentle textures or decorative elements like faint patterns, mist, fabric, or natural scenery. "
        "5. Ensure that the image as a whole feels unified, elegant, and expressive, with a natural visual gradient that leads the eye from the bottom toward the main subject. "
        "Do not include any watermarks, signatures, logos, or text of any kind. "
        "The image must not contain captions, titles, calligraphy, labels, typography, or any form of written language, whether visible or hidden. "
        "The final result must be clean, purely visual, and entirely free of any textual elements or overlays. "
    )
    if inspiration:
        prompt += f"The image may draw subtle inspiration from {inspiration}, but should not imitate it literally. "
    if color_style:
        prompt += f"Use a color palette that reflects this concept: {color_style}. "
    if composition:
        prompt += f"The composition should follow this visual approach: {composition}. "
    if style:
        prompt += f"The artistic style should be primarily {style}. "
    if atmosfera:
        prompt += f"The overall atmosphere should evoke a feeling of: {atmosfera}. "
    if tlo:
        prompt += f"The background should include elements like: {tlo}. "
    if perspektywa:
        prompt += f"Use this perspective: {perspektywa}. "
    if detale:
        prompt += f"Pay special attention to details such as: {detale}. "
    if realizm:
        prompt += f"The level of realism should be: {realizm}. "
    if styl_narracyjny:
        prompt += f"The narrative style of the image should resemble: {styl_narracyjny}. "
    return prompt

def get_detailed_prompt_from_model(
    client,
    base_prompt: str,
    inspiration: str,
    color: str,
    composition: str,
    style: str = None,
    atmosfera: str = None,
    tlo: str = None,
    perspektywa: str = None,
    detale: str = None,
    realizm: str = None,
    styl_narracyjny: str = None,
    model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    temperature: float = 0.7,
    stream: bool = False
):
    full_prompt = generate_custom_prompt(
        baseprompt=base_prompt,
        inspiration=inspiration,
        color_style=color,
        composition=composition,
        style=style,
        atmosfera=atmosfera,
        tlo=tlo,
        perspektywa=perspektywa,
        detale=detale,
        realizm=realizm,
        styl_narracyjny=styl_narracyjny
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Respond clearly and concisely."},
        {"role": "user", "content": full_prompt}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=stream
    )

    return response.choices[0].message.content