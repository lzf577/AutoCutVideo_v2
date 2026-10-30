import os
from PIL import Image, ImageFont, ImageDraw

def test_alignment():
    img = Image.new("RGBA", (500, 300), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font_main = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 60)
    font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 60)
    
    size = 60
    
    # 1. Left-Middle (what we just did)
    y1 = 50
    draw_y1 = y1 + size // 2
    draw.text((10, draw_y1), "🔴", font=font_emoji, embedded_color=True, anchor="lm")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), draw_y1), "【极度危险】", font=font_main, fill="black", anchor="lm")
    draw.line([(0, draw_y1), (500, draw_y1)], fill="blue", width=1) # midline

    # 2. Left-Baseline (ls)
    y2 = 120
    draw_y2 = y2 + int(size * 0.8) # rough baseline
    draw.text((10, draw_y2), "🔴", font=font_emoji, embedded_color=True, anchor="ls")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), draw_y2), "【极度危险】", font=font_main, fill="black", anchor="ls")
    draw.line([(0, draw_y2), (500, draw_y2)], fill="blue", width=1) # baseline

    # 3. Left-Middle + manual empirical shift down for emoji
    y3 = 190
    draw_y3 = y3 + size // 2
    emoji_y_shift = int(size * 0.05) # 5% shift down
    draw.text((10, draw_y3 + emoji_y_shift), "🔴", font=font_emoji, embedded_color=True, anchor="lm")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), draw_y3), "【极度危险】", font=font_main, fill="black", anchor="lm")
    draw.line([(0, draw_y3), (500, draw_y3)], fill="blue", width=1) # text midline

    img.save("align_test5.png")
    print("Done")

if __name__ == "__main__":
    test_alignment()
