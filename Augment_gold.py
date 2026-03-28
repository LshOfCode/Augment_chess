import random

# =========================
# apply 함수들 (더미)
# =========================

def apply_gold_dummy_1(game, player):
    return

def apply_gold_dummy_2(game, player):
    return

def apply_gold_dummy_3(game, player):
    return

def apply_gold_dummy_4(game, player):
    return

def apply_gold_dummy_5(game, player):
    return


# =========================
# 골드 증강 리스트
# =========================

GOLD_AUGMENTS = [
    {
        "id": "gold_dummy_1",
        "name": "골드 더미 1",
        "desc": "골드 더미 증강 1번입니다.",
        "tier": "gold",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_gold_dummy_1.png",
        "apply": apply_gold_dummy_1,
    },
    {
        "id": "gold_dummy_2",
        "name": "골드 더미 2",
        "desc": "골드 더미 증강 2번입니다.",
        "tier": "gold",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_gold_dummy_2.png",
        "apply": apply_gold_dummy_2,
    },
    {
        "id": "gold_dummy_3",
        "name": "골드 더미 3",
        "desc": "골드 더미 증강 3번입니다.",
        "tier": "gold",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_gold_dummy_3.png",
        "apply": apply_gold_dummy_3,
    },
    {
        "id": "gold_dummy_4",
        "name": "골드 더미 4",
        "desc": "골드 더미 증강 4번입니다.",
        "tier": "gold",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_gold_dummy_4.png",
        "apply": apply_gold_dummy_4,
    },
    {
        "id": "gold_dummy_5",
        "name": "골드 더미 5",
        "desc": "골드 더미 증강 5번입니다.",
        "tier": "gold",
        "timing": ["start", "20", "40"],
        "icon": "static/Augment_icon/Augment_gold_dummy_5.png",
        "apply": apply_gold_dummy_5,
    },
]