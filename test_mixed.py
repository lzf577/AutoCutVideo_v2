import sys
import emoji
from PIL import Image, ImageFont, ImageDraw

def render_mixed_text(draw, text, font_main, font_emoji, start_x, start_y, fill):
    x = start_x
    for token in emoji.analyze(text):
        char = token.value
        if token.value.is_emoji:
            # draw emoji
            draw.text((x, start_y), char, font=font_emoji, embedded_color=True)
            x += draw.textlength(char, font=font_emoji)
        else:
            draw.text((x, start_y), char, font=font_main, fill=fill)
            x += draw.textlength(char, font=font_main)

img = Image.new("RGBA", (1000, 500), (0, 0, 0, 0))
font_main = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 50)
font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 50)
draw = ImageDraw.Draw(img)

text = "🔴 【混沌难测】 🟢"
# We need to tokenize properly because emoji.analyze might not yield non-emoji parts!
# wait, emoji.analyze doesn't yield non-emoji parts in all versions.
# Let's write a simple regex or use emoji.replace_emoji

def my_tokenizer(text):
    res = []
    # Actually just iterate chars? No, emojis can be multiple chars.
    import emoji
    emoji_list = emoji.emoji_list(text)
    last = 0
    for e in emoji_list:
        start, end = e['match_start'], e['match_end']
        if start > last:
            res.append({"type": "text", "text": text[last:start]})
        res.append({"type": "emoji", "text": text[start:end]})
        last = end
    if last < len(text):
        res.append({"type": "text", "text": text[last:]})
    return res

tokens = my_tokenizer(text)
x = 10
for t in tokens:
    if t["type"] == "emoji":
        draw.text((x, 10), t["text"], font=font_emoji, embedded_color=True)
        x += draw.textlength(t["text"], font=font_emoji)
    else:
        draw.text((x, 10), t["text"], font=font_main, fill="white")
        x += draw.textlength(t["text"], font=font_main)

img.save("d:/AutoCutVideo_v2/test_mixed.png")
print("Done")
