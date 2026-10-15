import requests
import re
from urllib.parse import urljoin

url = 'https://breakthru.pk'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    r = requests.get(url, headers=headers, timeout=15)
    html = r.text

    print(f"Status Code: {r.status_code}")

    # Find images
    print("\n--- IMAGES & LOGOS ---")
    imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
    for img in imgs:
        full_url = urljoin(url, img)
        if any(k in img.lower() for k in ['logo', 'breakthru', 'brand', 'header', 'icon']):
            print("MATCH:", full_url)
        else:
            print("IMG:", full_url)

    # Find CSS
    print("\n--- CSS FILES ---")
    css_files = re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html, re.I)
    for css in css_files[:5]:
        print("CSS:", urljoin(url, css))

    # Fetch main theme CSS or inline colors
    print("\n--- COLORS IN HTML ---")
    colors = set(re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', html))
    print("Found colors:", list(colors)[:20])

except Exception as e:
    print("Error:", e)
