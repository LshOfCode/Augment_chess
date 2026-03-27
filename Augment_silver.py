import random

# =========================
# apply 함수들
# =========================

def apply_no_castling(game, player):
    enemy = 'B' if player == 'W' else 'W'

    if game.effects[enemy].get("no_castling"):
        apply_pawn_supply(game, player)
        return

    game.effects[enemy]["no_castling"] = True
    
def apply_king_buff(game, player):
    game.effects[player]["king_buff"] = True
    game.effects[player]["no_castling"] = True

def apply_pawn_supply(game, player):
    row = 5 if player == "W" else 2

    empty_cells = []
    for x in range(8):
        if game.grid[row][x] is None:
            empty_cells.append((x, row))

    if empty_cells:
        spawn_x, spawn_y = random.choice(empty_cells)
        game.spawn_pawn(player, spawn_x, spawn_y)

def apply_pawn_slow(game, player):
    enemy = 'B' if player == 'W' else 'W'
    game.effects[enemy]["pawn_slow"] = 2  # 2개 제한


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
        "desc": "상대의 캐슬링이 금지됩니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "static/Augment_icon/Augment_no_castling.png",
        "apply": apply_no_castling,
    },

    {
        "id": "pawn_supply",
        "name": "폰 보급",
        "desc": "자신의 폰 앞 열중 무작위 한칸에 폰이 생성됩니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "static/Augment_icon/Augment_pawn_supply.png",
        "apply": apply_pawn_supply,
    },
    
    {
    "id": "king_buff",
    "name": "왕권 강화",
    "desc": "내 킹이 원래 이동 외에 상하좌우로 2칸 이동할 수 있지만 캐슬링이 금지됩니다.",
    "tier": "silver",
    "timing": "start",
    "icon": "static/Augment_icon/Augment_king_buff.png",
    "apply": apply_king_buff,
    },

    {
        "id": "pawn_slow",
        "name": "달팽이 폰",
        "desc": "상대의 처음 2개의 기본 폰은 2칸 전진이 금지됩니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "static/Augment_icon/Augment_pawn_slow.png",
        "apply": apply_pawn_slow,
    },

    {
        "id": "bishop_to_knight",
        "name": "몽골리안 갬빗",
        "desc": "자신의 모든 비숍이 나이트로 전환됩니다.",
        "tier": "silver",
        "timing": "start",
        "icon": "static/Augment_icon/Augment_bishop_to_knight.png",
        "apply": apply_bishop_to_knight,
    },

    {
        "id": "pawn_retreat",
        "name": "후퇴하라!",
        "desc": "자신의 모든 폰이 1칸 뒤로 이동할 수 있습니다.(잡기는 불가능)",
        "tier": "silver",
        "timing": "start",
        "icon": "static/Augment_icon/Augment_pawn_retreat.png",
        "apply": apply_pawn_retreat,
    },

    {
        "id": "reorganize",
        "name": "재정비",
        "desc": "자신의 비숍 또는 나이트가 잡히면 무작위 빈칸에 폰을 하나 생성합니다.(1회 한정)",
        "tier": "silver",
        "timing": "start",
        "icon": "static/Augment_icon/Augment_reorganize.png",
        "apply": apply_reorganize,
    },

]