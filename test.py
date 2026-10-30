import sys
import traceback

sys.path.append('d:/AutoCutVideo_v2')

try:
    print("Importing timeline_renderer", flush=True)
    from timeline_renderer import generate_text_overlay_png
    print("Calling generate_text_overlay_png", flush=True)
    res = generate_text_overlay_png(1080, 1920, '🔴 【混沌难测】', '', 'C:/Windows/Fonts/msyhbd.ttc', 50, '.', 'classic_white_yellow', '', '')
    print("Success:", res, flush=True)
except Exception as e:
    print('Error caught:')
    traceback.print_exc()
