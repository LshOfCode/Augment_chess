import random

# =========================
# apply 함수들
# =========================

def apply_silver_dummy_1(game, player):
    return

def apply_silver_dummy_2(game, player):
    return

def apply_silver_dummy_3(game, player):
    return

def apply_silver_dummy_4(game, player):
    return

def apply_silver_dummy_5(game, player):
    return

def apply_countdown(game, player):
    game.effects[player]["countdown"] = 8
    
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
    bishops = []

    # 비숍 위치 수집
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece and piece.color == player and piece.name == "B":
                bishops.append((x, y))

    # 비숍 없으면 바로 종료
    if not bishops:
        return

    # 전부 나이트로 변경
    for x, y in bishops:
        game.grid[y][x] = game.create_piece("N", player)


def apply_pawn_retreat(game, player):
    game.effects[player]["pawn_retreat"] = True


def apply_reorganize(game, player):
    game.effects[player]["reorganize"] = 1  # 1회 한정
    
def apply_bishop_battery(game, player):
    knights = []

    # 내 나이트 찾기
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece and piece.color == player and piece.name == "N":
                knights.append((x, y))

    # 나이트 없으면 아무 일도 안 일어남
    if not knights:
        return

    # 랜덤 1개 선택
    x, y = random.choice(knights)

    # 비숍으로 변경
    game.grid[y][x] = game.create_piece("B", player)


# =========================
# 증강 리스트
# =========================

SILVER_AUGMENTS = [
    {
    "id": "bishop_battery",
    "name": "비숍 배터리!!",
    "desc": "자신의 랜덤한 나이트 1개가 비숍으로 변경됩니다.",
    "tier": "silver",
    "timing": ["start"],
    "icon": "static/Augment_icon/Augment_bishop_battery.png",
    "apply": apply_bishop_battery,
},
    {
    "id": "countdown",
    "name": "종말의 카운트다운",
    "desc": "40턴이 지나면 즉시 승리합니다.",
    "tier": "silver",
    "timing": ["start"],
    "icon": "static/Augment_icon/Augment_countdown.png",
    "apply": apply_countdown,
},
    
    {
    "id": "guardian_of_balance",
    "name": "균형의 수호자",
    "desc": "자신의 기물 1개를 선택하고 같은 점수 이하로 상대 기물을 제거합니다.",
    "tier": "silver",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_guardian_of_balance.png",
    "type": "interactive"
},
    
    {
        "id": "no_castling",
        "name": "캐슬링 금지",
        "desc": "상대의 캐슬링이 금지됩니다.",
        "tier": "silver",
        "timing": ["start"],
        "icon": "static/Augment_icon/Augment_no_castling.png",
        "apply": apply_no_castling,
    },

    {
        "id": "pawn_supply",
        "name": "폰 보급",
        "desc": "자신의 폰 앞 열중 무작위 한칸에 폰이 생성됩니다.",
        "tier": "silver",
        "timing": ["start", "2", "4"],
        "icon": "static/Augment_icon/Augment_pawn_supply.png",
        "apply": apply_pawn_supply,
    },
    
    {
    "id": "king_buff",
    "name": "왕권 강화",
    "desc": "내 킹이 원래 이동 외에 상하좌우로 2칸 이동할 수 있지만 캐슬링이 금지됩니다.",
    "tier": "silver",
    "timing": ["start"],
    "icon": "static/Augment_icon/Augment_king_buff.png",
    "apply": apply_king_buff,
    },

    {
        "id": "pawn_slow",
        "name": "달팽이 폰",
        "desc": "상대의 처음 2개의 기본 폰은 2칸 전진이 금지됩니다.",
        "tier": "silver",
        "timing": ["start"],
        "icon": "static/Augment_icon/Augment_pawn_slow.png",
        "apply": apply_pawn_slow,
    },

    {
        "id": "bishop_to_knight",
        "name": "몽골리안 갬빗",
        "desc": "자신의 모든 비숍이 나이트로 전환됩니다.",
        "tier": "silver",
        "timing": ["start"],
        "icon": "static/Augment_icon/Augment_bishop_to_knight.png",
        "apply": apply_bishop_to_knight,
    },

    {
        "id": "pawn_retreat",
        "name": "후퇴하라!",
        "desc": "자신의 모든 폰이 1칸 뒤로 이동할 수 있습니다.(잡기는 불가능)",
        "tier": "silver",
        "timing": ["start", "2"],
        "icon": "static/Augment_icon/Augment_pawn_retreat.png",
        "apply": apply_pawn_retreat,
    },

    {
        "id": "reorganize",
        "name": "재정비",
        "desc": "자신의 비숍 또는 나이트가 잡히면 무작위 빈칸에 폰을 하나 생성합니다.(1회 한정)",
        "tier": "silver",
        "timing": ["start", "2"],
        "icon": "static/Augment_icon/Augment_reorganize.png",
        "apply": apply_reorganize,
    },
    
    {
    "id": "silver_dummy_1",
    "name": "실버 더미 1",
    "desc": "실버 더미 증강 1번입니다.",
    "tier": "silver",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_silver_dummy_1.png",
    "apply": apply_silver_dummy_1,
},
{
    "id": "silver_dummy_2",
    "name": "실버 더미 2",
    "desc": "실버 더미 증강 2번입니다.",
    "tier": "silver",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_silver_dummy_2.png",
    "apply": apply_silver_dummy_2,
},
{
    "id": "silver_dummy_3",
    "name": "실버 더미 3",
    "desc": "실버 더미 증강 3번입니다.",
    "tier": "silver",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_silver_dummy_3.png",
    "apply": apply_silver_dummy_3,
},
{
    "id": "silver_dummy_4",
    "name": "실버 더미 4",
    "desc": "실버 더미 증강 4번입니다.",
    "tier": "silver",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_silver_dummy_4.png",
    "apply": apply_silver_dummy_4,
},
{
    "id": "silver_dummy_5",
    "name": "실버 더미 5",
    "desc": "실버 더미 증강 5번입니다.",
    "tier": "silver",
    "timing": ["start", "2", "4"],
    "icon": "static/Augment_icon/Augment_silver_dummy_5.png",
    "apply": apply_silver_dummy_5,
},

]