import sys
from PIL import Image, ImageFont, ImageDraw

img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
font = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 50)
draw = ImageDraw.Draw(img)
draw.text((10, 10), "🔴", font=font, fill="white", embedded_color=True)
img.save("d:/AutoCutVideo_v2/test_emoji2.png")
print("Done")
