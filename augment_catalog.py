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
    enemy = enemy_of(player)
    game.effects[enemy]["increment"] = 5
    game.effects[enemy]["time_cap"] = 180


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
            elif piece.color == enemy and game.is_minor_piece(piece):
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


def apply_twin_bishops(game, player):
    bishops = []
    for row in game.grid:
        for piece in row:
            if piece and piece.color == player and piece.name == "B":
                bishops.append(piece)
    if len(bishops) >= 2:
        game.effects[player]["twin_bishops"] = bishops[:2]


def apply_forward_attack(game, player):
    game.effects[player]["forward_attack"] = True


def apply_rook_awakening(game, player):
    game.effects[player]["rook_awakened"] = True


def apply_infection(game, player):
    game.effects[player]["infection"] = True


def apply_bullet_game(game, player):
    enemy = enemy_of(player)
    game.effects[enemy]["increment"] = 2
    game.effects[enemy]["time_cap"] = 60


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
    pawns = []
    for row in game.grid:
        for piece in row:
            if piece and piece.color == player and piece.name == "P":
                pawns.append(piece)
    if not pawns:
        return
    piece = random.choice(pawns)
    coords = game._find_piece_coords(piece)
    if coords is None:
        return
    x, y = coords
    piece = game.create_piece("Q", player)
    game.grid[y][x] = piece
    game.effects[player]["colossus_piece"] = piece
    game.effects[player]["colossus_wait"] = 5


def apply_pawn_evolution(game, player):
    return


def spawn_bonus_pawns(game, color, count):
    row = 5 if color == "W" else 2
    empty_cells = [(x, row) for x in range(8) if game.grid[row][x] is None]
    random.shuffle(empty_cells)
    for x, y in empty_cells[:count]:
        game.spawn_pawn(color, x, y)


def apply_random_augment_silver(game, player):
    return


def apply_random_augment_gold(game, player):
    spawn_bonus_pawns(game, player, 1)


def apply_random_augment_diamond(game, player):
    spawn_bonus_pawns(game, player, 2)


def apply_no_draw_win_silver(game, player):
    game.effects[player]["anti_draw_win"] = True
    spawn_bonus_pawns(game, enemy_of(player), 2)


def apply_no_draw_win_gold(game, player):
    game.effects[player]["anti_draw_win"] = True
    spawn_bonus_pawns(game, enemy_of(player), 1)


def apply_no_draw_win_diamond(game, player):
    game.effects[player]["anti_draw_win"] = True


def apply_king_breeding(game, player):
    return


def apply_true_gambler(game, player):
    return


def apply_augment_upgrade(game, player):
    game.effects[player]["augment_upgrade"] = game.effects[player].get("augment_upgrade", 0) + 1


def apply_ambush_setup(game, player):
    return


def apply_emergency_escape(game, player):
    return


def apply_king_copy(game, player):
    kings = game.find_kings(player)
    if not kings:
        return
    candidates = []
    forward = -1 if player == "W" else 1
    for y in range(8):
        for x in range(8):
            piece = game.grid[y][x]
            if piece is None or piece.color != player or piece.name != "P":
                continue
            nx = x
            ny = y + forward
            if game.in_bounds(nx, ny) and game.grid[ny][nx] is None:
                candidates.append((nx, ny))
    if not candidates:
        x, y = kings[0]
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx = x + dx
                ny = y + dy
                if game.in_bounds(nx, ny) and game.grid[ny][nx] is None:
                    candidates.append((nx, ny))
    if not candidates:
        for yy in range(8):
            for xx in range(8):
                if game.grid[yy][xx] is None:
                    candidates.append((xx, yy))
    if not candidates:
        return
    nx, ny = random.choice(candidates)
    game.grid[ny][nx] = game.create_piece("K", player)
    game.effects[player]["king_copy_active"] = True


SILVER_AUGMENTS = [
    {"id": "bishop_battery", "name": "비숍 배터리", "desc": "내 나이트 1개를 비숍으로 바꿉니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_bishop_battery.png", "apply": apply_bishop_battery},
    {"id": "countdown", "name": "죽음의 카운트다운", "desc": "내 45턴 안에 끝내면 즉시 승리합니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_countdown.png", "apply": apply_countdown},
    {"id": "guardian_of_balance", "name": "균형의 수호자", "desc": "내 기물 1개와 같은 점수 이하의 상대 기물을 제거합니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_guardian_of_balance.png", "type": "interactive"},
    {"id": "no_castling", "name": "캐슬링 금지", "desc": "상대는 캐슬링할 수 없습니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_no_castling.png", "apply": apply_no_castling},
    {"id": "pawn_supply", "name": "폰 보급", "desc": "내 진영에 폰 1개를 생성합니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_pawn_supply.png", "apply": apply_pawn_supply},
    {"id": "king_buff", "name": "킹 강화", "desc": "킹이 상하좌우로 2칸 이동할 수 있지만 캐슬링은 불가능합니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_king_buff.png", "apply": apply_king_buff},
    {"id": "pawn_slow", "name": "달팽이 폰", "desc": "상대의 처음 2개 폰은 2칸 전진할 수 없습니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_pawn_slow.png", "apply": apply_pawn_slow},
    {"id": "bishop_to_knight", "name": "몽골리안 갬빗", "desc": "내 모든 비숍을 나이트로 바꿉니다.", "tier": "silver", "timing": ["start"], "icon": "static/Augment_icon/Augment_bishop_to_knight.png", "apply": apply_bishop_to_knight},
    {"id": "pawn_retreat", "name": "후퇴하라!", "desc": "내 폰이 뒤로 1칸 이동할 수 있습니다.", "tier": "silver", "timing": ["start", "20"], "icon": "static/Augment_icon/Augment_pawn_retreat.png", "apply": apply_pawn_retreat},
    {"id": "reorganize", "name": "재정비", "desc": "내 비숍이나 나이트가 잡히면 빈 칸에 폰을 생성합니다.", "tier": "silver", "timing": ["start", "20"], "icon": "static/Augment_icon/Augment_reorganize.png", "apply": apply_reorganize},
    {"id": "pawn_vs_pawn", "name": "폰 vs 폰", "desc": "내 무작위 폰 1개는 상대 폰에게 잡히지 않습니다.", "tier": "silver", "timing": ["start"], "icon": "", "apply": apply_pawn_vs_pawn},
    {"id": "weak_infection", "name": "약한 감염", "desc": "킹이 기물을 잡을 때 그 칸의 기물을 내 폰으로 바꾸고 킹은 이동하지 않습니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "", "apply": apply_weak_infection},
    {"id": "gambit_brain", "name": "갬빗 두뇌", "desc": "내 폰 최대 2개 제거, 상대 마이너 피스 1개 제거.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_gambit_brain.png", "apply": apply_gambit_brain},
    {"id": "augment_upgrade", "name": "증강 업~ 증강 업~", "desc": "다음 증강의 티어가 한 단계 상승합니다. 플레에서 더 올라가면 폰 2개를 얻습니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "", "apply": apply_augment_upgrade},
    {"id": "ambush_setup", "name": "기습 전개", "desc": "게임 시작 전 1회, 기물 1개를 선택해 한 번 이동한 상태로 시작합니다.", "tier": "silver", "timing": ["start"], "icon": "", "apply": apply_ambush_setup, "activatable": True},
    {"id": "emergency_escape", "name": "긴급 탈출", "desc": "체크 상태일 때 1회, 내 왕을 안전한 빈 칸으로 이동시킵니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "", "apply": apply_emergency_escape, "activatable": True},
    {"id": "random_augment_silver", "name": "무작위 증강", "desc": "실버 무작위 증강을 획득합니다.", "tier": "silver", "timing": ["start", "20", "40"], "icon": "", "apply": apply_random_augment_silver},
    {"id": "no_draw_win_silver", "name": "무승부하지 않을래?", "desc": "상대에게 폰 2개를 생성합니다. 무승부가 나면 승리로 처리됩니다.", "tier": "silver", "timing": ["start"], "icon": "", "apply": apply_no_draw_win_silver},
]


GOLD_AUGMENTS = [
    {"id": "blitz_game", "name": "블리츠 게임", "desc": "상대 시간 7분 제거, 상대는 자신의 턴마다 5초 증가하며 최대 시간은 3분입니다.", "tier": "gold", "timing": ["start"], "icon": "static/Augment_icon/Augment_blitz_game.png", "apply": apply_blitz_game},
    {"id": "underpromotion_lock", "name": "언더 프로모션!!", "desc": "상대는 퀸으로 프로모션할 수 없습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_sealed_queen.png", "apply": apply_underpromotion_enemy},
    {"id": "death_mark", "name": "죽음의 표시", "desc": "상대의 킹, 퀸, 폰을 제외한 랜덤 기물 1개를 표시하고 3턴 뒤 제거합니다.", "tier": "gold", "timing": ["20", "40"], "icon": "static/Augment_icon/Augment_death_mark.png", "apply": apply_death_mark},
    {"id": "fast_promotion", "name": "빠른 승급", "desc": "내 폰의 프로모션 칸이 2칸 앞당겨집니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_fast_promotion.png", "apply": apply_fast_promotion},
    {"id": "hill_king", "name": "언덕의 왕", "desc": "내 왕이 중앙 4칸에 들어가면 즉시 승리합니다.", "tier": "gold", "timing": ["start"], "icon": "", "apply": apply_hill_king},
    {"id": "bishop_weaken", "name": "비숍 약화", "desc": "상대 무작위 비숍 1개의 이동 거리를 최대 2칸으로 제한합니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_weaken_enemy_bishop},
    {"id": "rook_weaken", "name": "룩 약화", "desc": "상대 무작위 룩 1개의 이동 거리를 최대 3칸으로 제한합니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_weaken_enemy_rook},
    {"id": "twin_bishops", "name": "쌍 비숍", "desc": "비숍 하나를 이동하면 다른 비숍도 추가로 한 번 이동할 수 있으며, 한 비숍이 잡히면 다른 비숍도 함께 제거됩니다.", "tier": "gold", "timing": ["start"], "icon": "", "apply": apply_twin_bishops},
    {"id": "bishop_awakening", "name": "비숍 각성", "desc": "내 비숍은 추가로 주변 1칸을 킹처럼 이동할 수 있습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_bishop_awakening},
    {"id": "rook_awakening", "name": "룩 각성", "desc": "내 룩은 추가로 주변 1칸을 킹처럼 이동할 수 있습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_rook_awakening},
    {"id": "infection", "name": "감염", "desc": "킹이 기물을 잡을 때 그 기물을 같은 팀 기물로 바꾸고 킹은 이동하지 않습니다.", "tier": "gold", "timing": ["start"], "icon": "", "apply": apply_infection},
    {"id": "pawn_evolution", "name": "폰 진화", "desc": "한 턴을 소모해 폰 1개를 나이트 또는 비숍으로 진화시킵니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_pawn_evolution, "activatable": True},
    {"id": "random_augment_gold", "name": "무작위 증강", "desc": "골드 무작위 증강을 획득하고, 폰 1개를 얻습니다.", "tier": "gold", "timing": ["start", "20", "40"], "icon": "", "apply": apply_random_augment_gold},
    {"id": "no_draw_win_gold", "name": "무승부하지 않을래?", "desc": "상대에게 폰 1개를 생성합니다. 무승부가 나면 승리로 처리됩니다.", "tier": "gold", "timing": ["start"], "icon": "", "apply": apply_no_draw_win_gold},
]


DIAMOND_AUGMENTS = [
    {"id": "bullet_game", "name": "불릿 게임", "desc": "상대 시간 9분 제거, 상대는 자신의 턴마다 2초 증가하며 최대 시간은 1분입니다.", "tier": "diamond", "timing": ["start"], "icon": "static/Augment_icon/Augment_bullet_game.png", "apply": apply_bullet_game},
    {"id": "thanos", "name": "타노스", "desc": "내 폰과 양쪽 킹을 제외한 모든 기물을 25% 확률로 제거합니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "static/Augment_icon/Augment_thanos.png", "apply": apply_thanos},
    {"id": "fast_pawn", "name": "fast 폰", "desc": "내 폰은 항상 2칸 전진할 수 있으며 상대는 앙파상이 가능합니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_fast_pawn},
    {"id": "forward_attack", "name": "전진 공격", "desc": "내 폰은 정면으로도 공격할 수 있습니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_forward_attack},
    {"id": "night_queen", "name": "밤의 여왕", "desc": "내 모든 퀸은 나이트 이동을 추가로 가집니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_night_queen},
    {"id": "bishop_missile", "name": "비숍 탄도 미사일", "desc": "내 무작위 비숍 1개는 포획 시 3x3 범위의 폰이 아닌 기물이 제거 됩니다. 이때 비숍도 함께 제거 됩니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_bishop_missile},
    {"id": "checkmate_colossus", "name": "체크메이트의 거신병", "desc": "자신의 무작위 폰 1개가 봉인된 체크메이트의 거신병으로 변합니다. 5턴 후부터 움직일 수 있습니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_checkmate_colossus},
    {"id": "king_breeding", "name": "왕의 번식", "desc": "왕을 선택한 뒤 인접한 내 퀸을 선택하면 퀸 주변 빈칸 8칸 중 랜덤 위치에 폰 1개를 생성합니다. 턴을 소모합니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_king_breeding},
    {"id": "random_augment_diamond", "name": "무작위 증강", "desc": "플레 무작위 증강을 획득하고, 폰 2개를 얻습니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_random_augment_diamond},
    {"id": "no_draw_win_diamond", "name": "무승부하지 않을래?", "desc": "무승부가 나면 승리로 처리됩니다.", "tier": "diamond", "timing": ["start"], "icon": "", "apply": apply_no_draw_win_diamond},
    {"id": "king_copy", "name": "왕의 복제", "desc": "내 킹을 1개 더 생성합니다. 이 증강을 먹은 쪽은 킹이 보드에 모두 없어질 때 패배합니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_king_copy},
    {"id": "true_gambler", "name": "진정한 도박사", "desc": "현재 시점에 등장 가능한 골드 증강 2개를 즉시 획득합니다.", "tier": "diamond", "timing": ["start", "20", "40"], "icon": "", "apply": apply_true_gambler},
]
