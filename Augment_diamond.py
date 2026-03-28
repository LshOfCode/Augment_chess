import random

# =========================
# apply 함수들 (더미)
# =========================

def apply_bullet_game(game, player):
    enemy = "B" if player == "W" else "W"
    game.effects[enemy]["increment"] = 5

def apply_thanos(game, player):
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece is None:
                continue

            # 양측 킹은 제거 제외
            if piece.name == "K":
                continue

            # 자신의 폰은 제거 제외
            if piece.color == player and piece.name == "P":
                continue

            # 나머지는 각각 50% 확률로 제거
            if random.random() < 0.5:
                game.grid[y][x] = None

def apply_diamond_dummy_4(game, player):
    return

def apply_diamond_dummy_5(game, player):
    return


# =========================
# 다이아 증강 리스트
# =========================

DIAMOND_AUGMENTS = [
    {
    "id": "bullet_game",
    "name": "불렛 게임",
    "desc": "상대의 시간을 9분 제거합니다. 상대는 자신의 턴을 둘때마다 5초씩 시 얻습니다.",
    "tier": "diamond",
    "timing": ["start"],
    "icon": "static/Augment_icon/Augment_bullet_game.png",
    "apply": apply_bullet_game,
    },
    {
    "id": "thanos",
    "name": "타노스",
    "desc": "자신의 폰과 양측의 킹을 제외한 모든 기물은 각각 50% 확률로 제거됩니다.",
    "tier": "diamond",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_thanos.png",
    "apply": apply_thanos,
},
    {
        "id": "diamond_dummy_4",
        "name": "다이아 더미 4",
        "desc": "다이아 더미 증강 4번입니다.",
        "tier": "diamond",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_4.png",
        "apply": apply_diamond_dummy_4,
    },
    {
        "id": "diamond_dummy_5",
        "name": "다이아 더미 5",
        "desc": "다이아 더미 증강 5번입니다.",
        "tier": "diamond",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_diamond_dummy_5.png",
        "apply": apply_diamond_dummy_5,
    },
]