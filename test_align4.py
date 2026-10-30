import os
from PIL import Image, ImageFont, ImageDraw

def test_alignment():
    img = Image.new("RGBA", (500, 200), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font_main = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 60)
    font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 60)
    
    y = 50
    size = 60
    
    # Draw a line at y and y+size to see the bounding box
    draw.line([(0, y), (500, y)], fill="red", width=1)
    draw.line([(0, y+size), (500, y+size)], fill="red", width=1)
    draw.line([(0, y+size//2), (500, y+size//2)], fill="blue", width=1) # middle line
    
    # 1. Left-Ascent alignment (anchor="la") - what we currently have
    draw.text((10, y), "🔴", font=font_emoji, embedded_color=True, anchor="la")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), y), "【极度危险】", font=font_main, fill="black", anchor="la")

    # 2. Left-Middle alignment (anchor="lm") - centered around y + size//2
    cy = y + 100
    draw.line([(0, cy), (500, cy)], fill="red", width=1)
    draw.line([(0, cy+size), (500, cy+size)], fill="red", width=1)
    draw.line([(0, cy+size//2), (500, cy+size//2)], fill="blue", width=1) # middle line
    
    draw.text((10, cy + size//2), "🔴", font=font_emoji, embedded_color=True, anchor="lm")
    draw.text((10 + draw.textlength("🔴", font=font_emoji), cy + size//2), "【极度危险】", font=font_main, fill="black", anchor="lm")

    img.save("align_test4.png")
    print("Done")

if __name__ == "__main__":
    test_alignment()
