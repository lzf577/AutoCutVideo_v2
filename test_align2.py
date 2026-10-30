import os
from PIL import Image, ImageFont, ImageDraw

def test_alignment():
    img = Image.new("RGBA", (500, 200), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font_main = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 60)
    font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 60)
    
    y = 10
    
    # 1. Left-Top alignment (anchor="lt")
    draw.text((10, y), "🔴", font=font_emoji, embedded_color=True, anchor="lt")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), y), "【测试】", font=font_main, fill="black", anchor="lt")
    
    # 2. Left-Ascent alignment (anchor="la")
    draw.text((10, y+80), "🔴", font=font_emoji, embedded_color=True, anchor="la")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), y+80), "【测试】", font=font_main, fill="black", anchor="la")

    img.save("align_test2.png")
    print("Done")

if __name__ == "__main__":
    test_alignment()
