import base64
import os
import requests
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def generate_extended_calendar_background(input_image_path,output_dir, output_format="png"):
   
    api_host = os.getenv("API_HOST", "https://api.stability.ai")
    api_key = os.getenv("STABILITY_API_KEY")
    if api_key is None:
        raise Exception("Missing Stability API key. Set it in STABILITY_API_KEY env var.")

    response = requests.post(
        f"{api_host}/v2beta/stable-image/edit/outpaint",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/*"
        },
        files={
            "image": open(input_image_path, "rb")
        },
        data={
            "left": 0,
            "right": 0,
            "up": 0,
            "down": 1999,
            "output_format": output_format
        },
    )

    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.status_code} -> {response.text}")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"outpainted_image.{output_format}")
    with open(out_path, "wb") as f:
        f.write(response.content)
    print(f"✅ Saved: {out_path}")
    print("✅ Finished outpainting.")

