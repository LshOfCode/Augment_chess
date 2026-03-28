import random

# =========================
# apply 함수들 (더미)
# =========================

def apply_diamond_dummy_1(game, player):
    return

def apply_diamond_dummy_2(game, player):
    return

def apply_diamond_dummy_3(game, player):
    return

def apply_diamond_dummy_4(game, player):
    return

def apply_diamond_dummy_5(game, player):
    return


# =========================
# 다이아 증강 리스트
# =========================

DIAMOND_AUGMENTS = [
    {
        "id": "diamond_dummy_1",
        "name": "다이아 더미 1",
        "desc": "다이아 더미 증강 1번입니다.",
        "tier": "diamond",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_1.png",
        "apply": apply_diamond_dummy_1,
    },
    {
        "id": "diamond_dummy_2",
        "name": "다이아 더미 2",
        "desc": "다이아 더미 증강 2번입니다.",
        "tier": "diamond",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_2.png",
        "apply": apply_diamond_dummy_2,
    },
    {
        "id": "diamond_dummy_3",
        "name": "다이아 더미 3",
        "desc": "다이아 더미 증강 3번입니다.",
        "tier": "diamond",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_3.png",
        "apply": apply_diamond_dummy_3,
    },
    {
        "id": "diamond_dummy_4",
        "name": "다이아 더미 4",
        "desc": "다이아 더미 증강 4번입니다.",
        "tier": "diamond",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_4.png",
        "apply": apply_diamond_dummy_4,
    },
    {
        "id": "diamond_dummy_5",
        "name": "다이아 더미 5",
        "desc": "다이아 더미 증강 5번입니다.",
        "tier": "diamond",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_5.png",
        "apply": apply_diamond_dummy_5,
    },
]