SUBTITLE_TEMPLATES = {
    "classic_white": {
        "name": "经典黑底白字",
        "ffmpeg_style": "Fontname=SimHei,Fontsize=18,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0",
        "qt_style": "color: white; background-color: rgba(0, 0, 0, 150); font-family: 'SimHei', 'Microsoft YaHei', sans-serif; font-size: 22px; padding: 4px; border-radius: 2px;",
        "use_outline": False
    },
    "variety_yellow": {
        "name": "综艺大黄字",
        "ffmpeg_style": "Fontname=Microsoft YaHei,Fontsize=22,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Bold=-1",
        "qt_style": "color: #FFFF00; font-family: 'Microsoft YaHei', sans-serif; font-size: 26px; font-weight: bold; background-color: transparent;",
        "use_outline": True,
        "outline_color": "#000000",
        "outline_width": 2
    },
    "cinematic": {
        "name": "电影感宽银幕",
        "ffmpeg_style": "Fontname=SimSun,Fontsize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=0,Shadow=2",
        "qt_style": "color: white; font-family: 'SimSun', serif; font-size: 20px; background-color: transparent;",
        "use_shadow": True,
        "shadow_color": "rgba(0, 0, 0, 200)",
        "shadow_radius": 5,
        "shadow_offset": (2, 2)
    },
    "apple_minimal": {
        "name": "苹果极简风",
        "ffmpeg_style": "Fontname=Microsoft YaHei Light,Fontsize=18,PrimaryColour=&H00F0F0F0,OutlineColour=&H00000000,BorderStyle=1,Outline=0,Shadow=0",
        "qt_style": "color: #F0F0F0; font-family: 'Microsoft YaHei Light', 'Microsoft YaHei', sans-serif; font-size: 22px; font-weight: 300; background-color: transparent;"
    },
    "sweet_pink": {
        "name": "甜美少女粉",
        "ffmpeg_style": "Fontname=Microsoft YaHei,Fontsize=22,PrimaryColour=&H00C1B6FF,OutlineColour=&H00FFFFFF,BorderStyle=1,Outline=2,Shadow=0,Bold=-1",
        "qt_style": "color: #FFB6C1; font-family: 'Microsoft YaHei', sans-serif; font-size: 26px; font-weight: bold; background-color: transparent;",
        "use_shadow": True,
        "shadow_color": "rgba(255, 255, 255, 255)",
        "shadow_radius": 3,
        "shadow_offset": (0, 0)
    },
    "esports_cyan": {
        "name": "电竞青蓝亮边",
        "ffmpeg_style": "Fontname=Microsoft YaHei,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00FFFF00,BorderStyle=1,Outline=2,Shadow=1,Bold=-1",
        "qt_style": "color: #FFFFFF; font-family: 'Microsoft YaHei', sans-serif; font-size: 26px; font-weight: bold; background-color: transparent;",
        "use_shadow": True,
        "shadow_color": "rgba(0, 255, 255, 255)",
        "shadow_radius": 6,
        "shadow_offset": (0, 0)
    },
    "tutorial_green": {
        "name": "知识区白底绿字",
        "ffmpeg_style": "Fontname=SimHei,Fontsize=18,PrimaryColour=&H0000B050,BackColour=&HCCFFFFFF,BorderStyle=3,Outline=1,Shadow=0",
        "qt_style": "color: #00B050; background-color: rgba(255, 255, 255, 200); font-family: 'SimHei', 'Microsoft YaHei', sans-serif; font-size: 22px; padding: 4px; border-radius: 4px;"
    },
    "immersive_white": {
        "name": "沉浸式无边框",
        "ffmpeg_style": "Fontname=Microsoft YaHei,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=0,Shadow=1",
        "qt_style": "color: white; font-family: 'Microsoft YaHei', sans-serif; font-size: 22px; background-color: transparent;",
        "use_shadow": True,
        "shadow_color": "rgba(0, 0, 0, 180)",
        "shadow_radius": 2,
        "shadow_offset": (1, 1)
    },
    "retro_yellow": {
        "name": "经典复古黄",
        "ffmpeg_style": "Fontname=SimHei,Fontsize=20,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0",
        "qt_style": "color: #FFFF00; font-family: 'SimHei', 'Microsoft YaHei', sans-serif; font-size: 24px; background-color: transparent;",
        "use_shadow": True,
        "shadow_color": "rgba(0, 0, 0, 255)",
        "shadow_radius": 1,
        "shadow_offset": (1, 1)
    },
    "neon_purple": {
        "name": "霓虹赛博紫",
        "ffmpeg_style": "Fontname=Microsoft YaHei,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00FF00FF,BorderStyle=1,Outline=3,Shadow=0,Bold=-1",
        "qt_style": "color: #FFFFFF; font-family: 'Microsoft YaHei', sans-serif; font-size: 26px; font-weight: bold; background-color: transparent;",
        "use_shadow": True,
        "shadow_color": "rgba(255, 0, 255, 255)",
        "shadow_radius": 8,
        "shadow_offset": (0, 0)
    },
    "vlog_black_box": {
        "name": "VLOG圆角黑框",
        "ffmpeg_style": "Fontname=Microsoft YaHei,Fontsize=20,PrimaryColour=&H00FFFFFF,BackColour=&H40000000,BorderStyle=3,Outline=1,Shadow=0",
        "qt_style": "color: white; background-color: rgba(0, 0, 0, 190); font-family: 'Microsoft YaHei', sans-serif; font-size: 24px; padding: 6px; border-radius: 8px;"
    },
    "documentary_yellow": {
        "name": "纪录片标配黄",
        "ffmpeg_style": "Fontname=SimHei,Fontsize=18,PrimaryColour=&H0000E0FF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0",
        "qt_style": "color: #FFE000; background-color: rgba(0, 0, 0, 150); font-family: 'SimHei', 'Microsoft YaHei', sans-serif; font-size: 22px; padding: 4px; border-radius: 2px;"
    }
}
