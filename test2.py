import sys
from PIL import Image, ImageFont
from pilmoji import Pilmoji

print("Start")
try:
    img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 50)
    with Pilmoji(img) as pilmoji:
        pilmoji.text((10, 10), "🔴", font=font)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
