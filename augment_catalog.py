import random


def enemy_of(player):
    return "B" if player == "W" else "W"


def apply_countdown(game, player):
    game.effects[player]["countdown"] = 45


def apply_no_castling(game, player):
    enemy = enemy_of(player)
    if game.effects[enemy].get("no_castling"):
        apply_pawn_supply(game, player)
        return
    game.effects[enemy]["no_castling"] = True


def apply_king_buff(game, player):
    game.effects[player]["king_buff"] = True
    game.effects[player]["no_castling"] = True


def apply_pawn_supply(game, player):
    row = 5 if player == "W" else 2
    empty_cells = [(x, row) for x in range(8) if game.grid[row][x] is None]
    if empty_cells:
        x, y = random.choice(empty_cells)
        game.spawn_pawn(player, x, y)


def apply_pawn_slow(game, player):
    game.effects[enemy_of(player)]["pawn_slow"] = 2


def apply_bishop_to_knight(game, player):
    bishops = []
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece and piece.color == player and piece.name == "B":
                bishops.append((x, y))
    for x, y in bishops:
        game.grid[y][x] = game.create_piece("N", player)


def apply_pawn_retreat(game, player):
    game.effects[player]["pawn_retreat"] = True


def apply_reorganize(game, player):
    game.effects[player]["reorganize"] = 1


def apply_bishop_battery(game, player):
    knights = []
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece and piece.color == player and piece.name == "N":
                knights.append((x, y))
    if not knights:
        return
    x, y = random.choice(knights)
    game.grid[y][x] = game.create_piece("B", player)


def apply_pawn_vs_pawn(game, player):
    pawns = []
    for row in game.grid:
        for piece in row:
            if piece and piece.color == player and piece.name == "P":
                pawns.append(piece)
    if pawns:
        game.effects[player]["pawn_vs_pawn_piece"] = random.choice(pawns)


def apply_weak_infection(game, player):
    game.effects[player]["weak_infection"] = True


def apply_blitz_game(game, player):
    game.effects[enemy_of(player)]["increment"] = 10


def apply_gambit_brain(game, player):
    enemy = enemy_of(player)
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
    for x, y in random.sample(my_pawns, min(2, len(my_pawns))):
        game.grid[y][x] = None
    if enemy_minors:
        x, y = random.choice(enemy_minors)
        game.grid[y][x] = None


def apply_death_mark(game, player):
    return


def apply_fast_promotion(game, player):
    game.effects[player]["fast_promotion"] = True


def apply_hill_king(game, player):
    game.effects[player]["hill_king"] = True


def apply_weaken_enemy_bishop(game, player):
    enemy = enemy_of(player)
    bishops = []
    for row in game.grid:
        for piece in row:
            if piece and piece.color == enemy and piece.name == "B":
                bishops.append(piece)
    if bishops:
        game.effects[enemy]["weakened_bishop_piece"] = random.choice(bishops)


def apply_weaken_enemy_rook(game, player):
    enemy = enemy_of(player)
    rooks = []
    for row in game.grid:
        for piece in row:
            if piece and piece.color == enemy and piece.name == "R":
                rooks.append(piece)
    if rooks:
        game.effects[enemy]["weakened_rook_piece"] = random.choice(rooks)


def apply_underpromotion_enemy(game, player):
    game.effects[enemy_of(player)]["no_queen_promotion"] = True


def apply_bishop_awakening(game, player):
    game.effects[player]["bishop_awakened"] = True


def apply_forward_attack(game, player):
    game.effects[player]["forward_attack"] = True


def apply_rook_awakening(game, player):
    game.effects[player]["rook_awakened"] = True


def apply_infection(game, player):
    game.effects[player]["infection"] = True


def apply_bullet_game(game, player):
    game.effects[enemy_of(player)]["increment"] = 5


def apply_thanos(game, player):
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece is None or piece.name == "K":
                continue
            if piece.color == player and piece.name == "P":
                continue
            if random.random() < 0.25:
                game.grid[y][x] = None


def apply_fast_pawn(game, player):
    game.effects[player]["fast_pawn"] = True


def apply_night_queen(game, player):
    game.effects[player]["night_queen"] = True


def apply_bishop_missile(game, player):
    bishops = []
    for row in game.grid:
        for piece in row:
            if piece and piece.color == player and piece.name == "B":
                bishops.append(piece)
    if bishops:
        game.effects[player]["missile_bishop_piece"] = random.choice(bishops)


def apply_checkmate_colossus(game, player):
    for y in range(8):
        for x in range(8):
            piece_on_board = game.grid[y][x]
            if piece_on_board and piece_on_board.color == player and piece_on_board.name == "P":
                game.grid[y][x] = None

    x = 3
    y = 6 if player == "W" else 1
    piece = game.create_piece("Q", player)
    game.grid[y][x] = piece
    game.effects[player]["colossus_piece"] = piece
    game.effects[player]["colossus_wait"] = 5


def apply_pawn_evolution(game, player):
    return


SILVER_AUGMENTS = [
    {"id": "bishop_battery", "name": "비숍 배터리", "desc": "내 나이트 1개를 비숍으로 바꿉니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_bishop_battery.png", "apply": apply_bishop_battery},
    {"id": "countdown", "name": "죽음의 카운트다운", "desc": "내 45턴 안에 끝내면 즉시 승리합니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_countdown.png", "apply": apply_countdown},
    {"id": "guardian_of_balance", "name": "균형의 수호자", "desc": "내 기물 1개와 같은 점수 이하의 상대 기물을 제거합니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_guardian_of_balance.png", "type": "interactive"},
    {"id": "no_castling", "name": "캐슬링 금지", "desc": "상대는 캐슬링할 수 없습니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_no_castling.png", "apply": apply_no_castling},
    {"id": "pawn_supply", "name": "폰 보급", "desc": "내 진영에 폰 1개를 생성합니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_pawn_supply.png", "apply": apply_pawn_supply},
    {"id": "king_buff", "name": "왕권 강화", "desc": "왕은 상하좌우로 2칸 이동할 수 있지만 캐슬링은 불가합니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_king_buff.png", "apply": apply_king_buff},
    {"id": "pawn_slow", "name": "달팽이 폰", "desc": "상대의 처음 2개 폰은 2칸 전진할 수 없습니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_pawn_slow.png", "apply": apply_pawn_slow},
    {"id": "bishop_to_knight", "name": "몽골리안 갬빗", "desc": "내 모든 비숍을 나이트로 바꿉니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_bishop_to_knight.png", "apply": apply_bishop_to_knight},
    {"id": "pawn_retreat", "name": "후퇴하라!", "desc": "내 폰은 뒤로 1칸 이동할 수 있습니다.", "tier": "silver", "timing": ["start", "20"], "icon": "static/Augment_icon/Augment_pawn_retreat.png", "apply": apply_pawn_retreat},
    {"id": "reorganize", "name": "재정비", "desc": "내 비숍이나 나이트가 잡히면 빈 칸에 폰을 생성합니다.", "tier": "silver", "timing": ["start", "20"], "icon": "static/Augment_icon/Augment_reorganize.png", "apply": apply_reorganize},
    {"id": "pawn_vs_pawn", "name": "폰 vs 폰", "desc": "내 무작위 폰 1개는 상대 폰에게 잡히지 않습니다.", "tier": "silver", "timing": ["start"], "icon": "", "apply": apply_pawn_vs_pawn},
    {"id": "weak_infection", "name": "약한 감염", "desc": "킹이 기물을 잡을 때 그 칸의 기물을 내 폰으로 바꾸고 킹은 이동하지 않습니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "", "apply": apply_weak_infection},
]


GOLD_AUGMENTS = [
    {"id": "blitz_game", "name": "블리츠 게임", "desc": "상대 시간 7분 제거, 상대는 자신의 턴마다 10초 증가합니다.", "tier": "gold", "timing": ["start"], "icon": "static/Augment_icon/Augment_blitz_game.png", "apply": apply_blitz_game},
    {"id": "gambit_brain", "name": "갬빗 두뇌", "desc": "내 폰 최대 2개 제거, 상대 마이너 피스 1개 제거.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_gambit_brain.png", "apply": apply_gambit_brain},
    {"id": "underpromotion_lock", "name": "언더 프로모션!!", "desc": "상대는 퀸으로 프로모션할 수 없습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_sealed_queen.png", "apply": apply_underpromotion_enemy},
    {"id": "death_mark", "name": "죽음의 표시", "desc": "상대의 킹, 퀸, 폰을 제외한 랜덤 기물 1개를 표시하고 3턴 뒤 제거합니다.", "tier": "gold", "timing": ["20", "40"], "icon": "static/Augment_icon/Augment_death_mark.png", "apply": apply_death_mark},
    {"id": "fast_promotion", "name": "빠른 승급", "desc": "내 폰의 프로모션 칸이 2칸 앞당겨집니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_fast_promotion.png", "apply": apply_fast_promotion},
    {"id": "hill_king", "name": "언덕의 왕", "desc": "내 왕이 중앙 4칸에 들어가면 즉시 승리합니다.", "tier": "gold", "timing": ["start"], "icon": "", "apply": apply_hill_king},
    {"id": "bishop_weaken", "name": "비숍 약화", "desc": "상대 무작위 비숍 1개의 이동 거리를 최대 2칸으로 제한합니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_weaken_enemy_bishop},
    {"id": "rook_weaken", "name": "룩 약화", "desc": "상대 무작위 룩 1개의 이동 거리를 최대 3칸으로 제한합니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_weaken_enemy_rook},
    {"id": "bishop_awakening", "name": "비숍 각성", "desc": "내 비숍은 추가로 주변 1칸을 킹처럼 이동할 수 있습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_bishop_awakening},
    {"id": "rook_awakening", "name": "룩 각성", "desc": "내 룩은 추가로 주변 1칸을 킹처럼 이동할 수 있습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_rook_awakening},
    {"id": "infection", "name": "감염", "desc": "킹이 기물을 잡을 때 그 기물을 같은 팀 기물로 바꾸고 킹은 이동하지 않습니다.", "tier": "gold", "timing": ["start"], "icon": "", "apply": apply_infection},
    {"id": "pawn_evolution", "name": "폰 진화", "desc": "한 턴을 소모해 폰 1개를 나이트 또는 비숍으로 진화시킵니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_pawn_evolution, "activatable": True},
]


DIAMOND_AUGMENTS = [
    {"id": "bullet_game", "name": "불릿 게임", "desc": "상대 시간 9분 제거, 상대는 자신의 턴마다 5초 증가합니다.", "tier": "diamond", "timing": ["start"], "icon": "static/Augment_icon/Augment_bullet_game.png", "apply": apply_bullet_game},
    {"id": "thanos", "name": "타노스", "desc": "내 폰과 양쪽 킹을 제외한 모든 기물을 25% 확률로 제거합니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_thanos.png", "apply": apply_thanos},
    {"id": "fast_pawn", "name": "fast 폰", "desc": "내 폰은 항상 2칸 전진할 수 있으며, 상대는 앙파상을 할 수 있습니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_fast_pawn},
    {"id": "forward_attack", "name": "전진 공격", "desc": "내 폰은 정면으로도 공격할 수 있습니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_forward_attack},
    {"id": "night_queen", "name": "밤의 여왕", "desc": "내 모든 퀸은 나이트 이동을 추가로 가집니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_night_queen},
    {"id": "bishop_missile", "name": "비숍 탄도 미사일", "desc": "내 무작위 비숍 1개는 포획 시 3x3 범위의 폰이 아닌 기물이 제거 됩니다. 이때 비숍도 함께 제거 됩니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_bishop_missile},
    {"id": "checkmate_colossus", "name": "체크메이트의 거신병", "desc": "폰을 모두 잃습니다. 즉시 퀸 앞에 퀸처럼 이동하는 거신병을 소환합니다. 5턴 동안 움직일 수 없고, 그동안 잡히지 않습니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_checkmate_colossus},
]
