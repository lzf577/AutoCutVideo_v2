import sys
from PIL import Image, ImageFont, ImageDraw

print("Start")
try:
    img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 50)
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), " 【混沌难测】", font=font, fill="white")
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
