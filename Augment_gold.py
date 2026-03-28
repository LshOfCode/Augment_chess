import random

# =========================
# apply 함수들 (더미)
# =========================

def apply_blitz_game(game, player):
    enemy = "B" if player == "W" else "W"
    game.effects[enemy]["increment"] = 10

def apply_gambit_brain(game, player):
    enemy = "B" if player == "W" else "W"

    my_pawns = []
    enemy_minors = []

    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if not piece:
                continue

            if piece.color == player and piece.name == "P":
                my_pawns.append((x, y))

            elif piece.color == enemy and piece.name in ("N", "B"):
                enemy_minors.append((x, y))

    # 내 폰 최대 2개 제거
    remove_pawn_count = min(2, len(my_pawns))
    if remove_pawn_count > 0:
        for x, y in random.sample(my_pawns, remove_pawn_count):
            game.grid[y][x] = None

    # 상대 마이너피스 1개 제거
    if enemy_minors:
        x, y = random.choice(enemy_minors)
        game.grid[y][x] = None

def apply_sealed_queen(game, player):
    enemy = "B" if player == "W" else "W"
    game.effects[enemy]["sealed_queen"] = True

def apply_gold_dummy_4(game, player):
    return

def apply_gold_dummy_5(game, player):
    return
def apply_gold_dummy_1(game, player):
    return
def apply_gold_dummy_2(game, player):
    return

# =========================
# 골드 증강 리스트
# =========================

GOLD_AUGMENTS = [
    {
    "id": "blitz_game",
    "name": "블리츠 게임",
    "desc": "상대의 시간을 7분 제거합니다. 상대는 자신의 턴을 둘때마다 10초씩 시간을 얻습니다.",
    "tier": "gold",
    "timing": ["start"],
    "icon": "static/Augment_icon/Augment_blitz_game.png",
    "apply": apply_blitz_game,
    },
    {
    "id": "gambit_brain",
    "name": "갬빗 두뇌",
    "desc": "자신의 무작위 폰이 최대 2개 제거되고, 상대의 무작위 마이너피스(나이트 또는 비숍) 1개가 제거됩니다.",
    "tier": "gold",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_gambit_brain.png",
    "apply": apply_gambit_brain,
},
    {
    "id": "sealed_queen",
    "name": "봉인된 여왕",
    "desc": "다음 증강 획득 시까지 상대의 퀸은 이동할 수 없습니다.",
    "tier": "gold",
    "timing": ["start", "2"],
    "icon": "static/Augment_icon/Augment_sealed_queen.png",
    "apply": apply_sealed_queen,
},
    {
        "id": "gold_dummy_4",
        "name": "골드 더미 4",
        "desc": "골드 더미 증강 4번입니다.",
        "tier": "gold",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_gold_dummy_4.png",
        "apply": apply_gold_dummy_4,
    },
    {
        "id": "gold_dummy_5",
        "name": "골드 더미 5",
        "desc": "골드 더미 증강 5번입니다.",
        "tier": "gold",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_gold_dummy_5.png",
        "apply": apply_gold_dummy_5,
    },
    {
        "id": "gold_dummy_4",
        "name": "골드 더미 4",
        "desc": "골드 더미 증강 4번입니다.",
        "tier": "gold",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_gold_dummy_4.png",
        "apply": apply_gold_dummy_1,
    },
    {
        "id": "gold_dummy_4",
        "name": "골드 더미 4",
        "desc": "골드 더미 증강 4번입니다.",
        "tier": "gold",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_gold_dummy_4.png",
        "apply": apply_gold_dummy_2,
    },
]