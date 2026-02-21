import base64

def generate_image(client, prompt, width, height):
    print("prompt", prompt)
    response = client.images.generate(
        prompt=prompt,
        model="black-forest-labs/FLUX.1-schnell",
        width=width,
        height=height,
        steps=4,
        n=3,
        response_format="b64_json",
    )

    if not response.data:
        raise ValueError("No image data received.")

    image_data = response.data[0].b64_json
    image_bytes = base64.b64decode(image_data)

    return image_bytes
