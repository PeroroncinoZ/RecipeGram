import requests
import os

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

API_KEY = 'YOUR_PIXABAY_API_KEY'  # <- paste your key here

def download_image_for_ingredient(ingredient_name):
    query = ingredient_name.strip().lower()
    url = f"https://pixabay.com/api/?key={API_KEY}&q={query}&image_type=photo&category=food&per_page=3"

    try:
        response = requests.get(url)
        data = response.json()

        if not data['hits']:
            print(f"[❌] No image found for {ingredient_name}")
            return None

        image_url = data['hits'][0]['webformatURL']
        image_data = requests.get(image_url).content

        filename = f"{ingredient_name.lower()}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)

        return filename
    except Exception as e:
        print(f"[❌] Failed to fetch image for {ingredient_name}: {e}")
        return None
