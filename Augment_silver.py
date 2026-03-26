import random

# =========================
# apply 함수들
# =========================

def apply_no_castling(game, player):
    enemy = 'B' if player == 'W' else 'W'
    game.effects[enemy]["no_castling"] = True


def apply_pawn_supply(game, player):
    direction = -1 if player == "W" else 1

    candidates = []

    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]

            if piece and piece.color == player and piece.name == "P":
                ny = y + direction
                if 0 <= ny < 8 and game.grid[ny][x] is None:
                    candidates.append((x, ny))

    if candidates:
        spawn_x, spawn_y = random.choice(candidates)
        game.spawn_pawn(player, spawn_x, spawn_y)


def apply_pawn_weaken(game, player):
    enemy = 'B' if player == 'W' else 'W'
    game.effects[enemy]["pawn_weaken"] = 2  # 2개 제한


def apply_bishop_to_knight(game, player):
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece and piece.color == player and piece.name == "B":
                game.grid[y][x] = game.create_piece("N", player)


def apply_pawn_retreat(game, player):
    game.effects[player]["pawn_retreat"] = True


def apply_reorganize(game, player):
    game.effects[player]["reorganize"] = 1  # 1회 한정


# =========================
# 증강 리스트
# =========================

SILVER_AUGMENTS = [

    {
        "id": "no_castling",
        "name": "캐슬링 금지",
        "desc": "상대의 캐슬링을 금지시킵니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "Augment_icon/Augment_no_castling.png",
        "apply": apply_no_castling,
    },

    {
        "id": "pawn_supply",
        "name": "폰 공급",
        "desc": "자신의 뒤에서 세 번째 줄에서 빈칸 하나를 골라 폰을 생성합니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "Augment_icon/Augment_pawn_supply.png",
        "apply": apply_pawn_supply,
    },

    {
        "id": "pawn_weaken",
        "name": "폰 약화",
        "desc": "상대의 처음 2개 폰은 2칸 전진이 불가능합니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "Augment_icon/Augment_pawn_weaken.png",
        "apply": apply_pawn_weaken,
    },

    {
        "id": "bishop_to_knight",
        "name": "몽골리안 갬빗",
        "desc": "자신의 모든 비숍이 나이트로 전환됩니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "Augment_icon/Augment_bishop_to_knight.png",
        "apply": apply_bishop_to_knight,
    },

    {
        "id": "pawn_retreat",
        "name": "후퇴하라!",
        "desc": "자신의 모든 폰이 1칸 뒤로 이동할 수 있습니다.(잡기는 불가능)",
        "tier": "silver",
        "timing": "start",
        "icon": "Augment_icon/Augment_pawn_retreat.png",
        "apply": apply_pawn_retreat,
    },

    {
        "id": "reorganize",
        "name": "재정비",
        "desc": "자신의 비숍 또는 나이트가 잡히면 무작위 빈칸에 폰을 하나 생성합니다.(1회 한정)",
        "tier": "silver",
        "timing": "start",
        "icon": "Augment_icon/Augment_reorganize.png",
        "apply": apply_reorganize,
    },

]