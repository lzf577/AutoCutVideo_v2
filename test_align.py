import os
from PIL import Image, ImageFont, ImageDraw

def test_alignment():
    img = Image.new("RGBA", (500, 200), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font_main = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 60)
    font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 60)
    
    y = 100
    
    # 1. Default alignment (no anchor)
    draw.text((10, 10), "🔴", font=font_emoji, embedded_color=True)
    draw.text((10 + draw.textlength("🔴", font=font_emoji), 10), "【测试】", font=font_main, fill="black")
    
    # 2. Left-Middle alignment (anchor="lm")
    draw.text((10, y), "🔴", font=font_emoji, embedded_color=True, anchor="lm")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), y), "【测试】", font=font_main, fill="black", anchor="lm")
    
    # 3. Left-Baseline alignment (anchor="ls")
    draw.text((10, y+80), "🔴", font=font_emoji, embedded_color=True, anchor="ls")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), y+80), "【测试】", font=font_main, fill="black", anchor="ls")

    img.save("align_test.png")
    print("Done")

if __name__ == "__main__":
    test_alignment()
