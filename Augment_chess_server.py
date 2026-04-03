import time
import random
from fastapi import WebSocket, WebSocketDisconnect, Body
import json

from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from Augment_chess_main import Board
from augment_catalog import SILVER_AUGMENTS, GOLD_AUGMENTS, DIAMOND_AUGMENTS

ALL_AUGMENTS = (
    SILVER_AUGMENTS +
    GOLD_AUGMENTS +
    DIAMOND_AUGMENTS
)


GUARDIAN_DURATION = 25

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms = {}
connections = {}


class AugmentSelectRequest(BaseModel):
    player_id: str
    augment_id: str


class AugmentActivateRequest(BaseModel):
    player_id: str
    augment_id: str
    x: int
    y: int
    x2: int | None = None
    y2: int | None = None
    choice: str | None = None


class DebugGrantAugmentRequest(BaseModel):
    player_id: str
    target_color: str
    augment_id: str


def create_room_data():
    tiers = ["silver", "gold", "diamond"]

    random_two = [
        random.choice(tiers),
        random.choice(tiers),
    ]

    augment_plan = random_two + ["gold"]
    random.shuffle(augment_plan)

    return {
        "board": Board(),
        "players": {"W": None, "B": None},
        "time": {
            "W": 600,
            "B": 600,
            "last_update": time.time(),
            "running": None,
            "ended": False,
            "winner": None,
        },
        "rematch": {
            "votes": {"W": False, "B": False},
            "count": 0,
        },
        
        "augment": {
            "active": False,
            "plan": augment_plan,
            "current_index": 0,
            "tier": None,
            "choices": {"W": [], "B": []},
            "selected": {"W": None, "B": None},
            "start_time": None,
            "duration_ms": 25000,
        },
        "owned": {
            "W": [],
            "B": [],
        },
        "move_count": 0,
        "guardian": {
            "active": False,
            "queue": [],
            "current": None,
            "selected_self": None,
            "selected_self_group": [],
            "selected_enemy": [],
            "selected_enemy_groups": [],
            "score": 0,
            "max_score": 0,
            "start_time": None,
        },
        "death_marks": [],
        "debug": False,
    }


def build_state(room):
    data = room["board"].to_dict()
    data["clock"] = room["time"]
    data["rematch"] = room["rematch"]
    data["players"] = room["players"]
    data["move_count"] = room["move_count"]

    augment_state = dict(room["augment"])
    if augment_state.get("active") and augment_state.get("start_time") is not None:
        remain = int(augment_state.get("duration_ms", 25000) - max(0, (time.time() - augment_state["start_time"]) * 1000))
        augment_state["remaining_ms"] = max(0, remain)
    else:
        augment_state["remaining_ms"] = 0
    augment_state["owned"] = room["owned"]
    data["augment"] = augment_state

    guardian_state = dict(room["guardian"])
    if guardian_state["active"] and guardian_state["start_time"] is not None:
        remain = GUARDIAN_DURATION - (time.time() - guardian_state["start_time"])
        guardian_state["remaining_ms"] = max(0, int(remain * 1000))
    else:
        guardian_state["remaining_ms"] = 0

    data["guardian"] = guardian_state
    data["death_marks"] = serialize_death_marks(room)
    return data


def update_clock(room):
    clock = room["time"]

    if room["players"]["W"] is None or room["players"]["B"] is None:
        clock["last_update"] = time.time()
        return

    if clock["ended"]:
        return

    if clock["running"] is None:
        clock["last_update"] = time.time()
        return

    now = time.time()
    elapsed = now - clock["last_update"]
    current = clock["running"]
    clock[current] -= elapsed
    clock["last_update"] = now

    if clock[current] <= 0:
        clock[current] = 0
        clock["ended"] = True
        clock["winner"] = "B" if current == "W" else "W"


def get_player_color(room, player_id):
    if room["players"]["W"] == player_id:
        return "W"
    if room["players"]["B"] == player_id:
        return "B"
    return None


def find_augment_by_id(augment_id: str):
    for augment in ALL_AUGMENTS:
        if augment["id"] == augment_id:
            return augment
    return None


def find_owned_augment(room, color, augment_id: str):
    for augment in room["owned"][color]:
        if augment.get("id") == augment_id:
            return augment
    return None


def advance_room_after_turn(room, room_id: str, player_color: str):
    board = room["board"]
    room["move_count"] += 1

    if room["move_count"] % 2 == 0:
        tick_death_marks(room)

    increment = board.effects[player_color].get("increment", 0)
    if increment > 0:
        room["time"][player_color] += increment
        time_cap = board.effects[player_color].get("time_cap")
        if time_cap is not None:
            room["time"][player_color] = min(room["time"][player_color], time_cap)

    if room["move_count"] in (20, 40):
        room["time"]["running"] = None
        room["time"]["last_update"] = time.time()

        room["augment"]["active"] = True
        room["augment"]["start_time"] = time.time()
        room["augment"]["selected"]["W"] = None
        room["augment"]["selected"]["B"] = None

        phase = str(room["move_count"])
        tier_index = room["augment"]["current_index"]
        tier = room["augment"]["plan"][tier_index]
        room["augment"]["tier"] = tier
        room["augment"]["current_index"] += 1

        w_choices, b_choices = get_player_specific_augment_choices(room, tier, phase, 3)
        room["augment"]["choices"]["W"] = w_choices
        room["augment"]["choices"]["B"] = b_choices
    else:
        room["time"]["running"] = board.turn
        room["time"]["last_update"] = time.time()


def piece_value(board, piece) -> int:
    return board.guardian_piece_value(piece)


def guardian_linked_positions(board, piece):
    return [[x, y] for x, y in board.guardian_linked_positions(piece)]


def flatten_guardian_groups(groups):
    positions = []
    for group in groups or []:
        for pos in group.get("positions", []):
            if pos not in positions:
                positions.append(pos)
    return positions




def find_piece_position_by_ref(board, piece_ref):
    for y in range(8):
        for x in range(8):
            if board.grid[y][x] is piece_ref:
                return (x, y)
    return None


def get_death_mark_candidates(board, target_color):
    candidates = []
    for y in range(8):
        for x in range(8):
            piece = board.grid[y][x]
            if piece is None:
                continue
            if piece.color != target_color:
                continue
            if piece.name in ("K", "Q", "P"):
                continue
            candidates.append(piece)
    return candidates


def apply_death_mark_to_enemy(room, player_color):
    board = room["board"]
    enemy_color = "B" if player_color == "W" else "W"
    candidates = get_death_mark_candidates(board, enemy_color)

    if not candidates:
        return False

    target_piece = random.choice(candidates)
    room["death_marks"].append({
        "piece": target_piece,
        "remaining_turns": 3,
        "source": player_color,
    })
    return True


def tick_death_marks(room):
    board = room["board"]
    next_marks = []

    for mark in room.get("death_marks", []):
        piece_ref = mark.get("piece")
        if piece_ref is None:
            continue

        pos = find_piece_position_by_ref(board, piece_ref)
        if pos is None:
            continue

        remaining = int(mark.get("remaining_turns", 0)) - 1
        if remaining <= 0:
            x, y = pos
            board.grid[y][x] = None
            continue

        mark["remaining_turns"] = remaining
        next_marks.append(mark)

    room["death_marks"] = next_marks


def serialize_death_marks(room):
    board = room["board"]
    result = []

    for mark in room.get("death_marks", []):
        piece_ref = mark.get("piece")
        if piece_ref is None:
            continue

        pos = find_piece_position_by_ref(board, piece_ref)
        if pos is None:
            continue

        x, y = pos
        result.append({
            "x": x,
            "y": y,
            "remaining_turns": int(mark.get("remaining_turns", 0)),
            "color": getattr(piece_ref, "color", None),
            "piece": getattr(piece_ref, "name", None),
        })

    return result

def guardian_selection_causes_illegal_check(board, color, self_positions, enemy_positions):
    removed = []

    for sx, sy in self_positions:
        if board.in_bounds(sx, sy):
            removed.append((sx, sy, board.grid[sy][sx]))
            board.grid[sy][sx] = None

    for ex, ey in enemy_positions:
        if board.in_bounds(ex, ey):
            removed.append((ex, ey, board.grid[ey][ex]))
            board.grid[ey][ex] = None

    try:
        enemy_color = "B" if color == "W" else "W"

        my_king_missing = board.find_king(color) is None
        enemy_king_missing = board.find_king(enemy_color) is None
        if my_king_missing or enemy_king_missing:
            return True

        # 양쪽 모두 체크 상태가 되면 선택 불가
        if board.is_in_check(color):
            return True
        if board.is_in_check(enemy_color):
            return True

        return False
    finally:
        for x, y, piece in removed:
            board.grid[y][x] = piece


def serialize_augment(augment):
    return {
        "id": augment["id"],
        "tier": augment["tier"],
        "title": augment["name"],
        "description": augment["desc"],
        "icon": augment.get("icon", ""),
        "activatable": bool(augment.get("activatable")),
        "used": False,
    }
    
def get_augments_by_tier(tier: str):
    if tier == "silver":
        return SILVER_AUGMENTS
    if tier == "gold":
        return GOLD_AUGMENTS
    if tier == "diamond":
        return DIAMOND_AUGMENTS
    return []


def expand_conflicting_augment_ids(ids):
    expanded = set(ids)
    if "bishop_awakening" in expanded:
        expanded.add("twin_bishops")
    if "twin_bishops" in expanded:
        expanded.add("bishop_awakening")
    return expanded


def get_random_augments_by_tier(tier: str, phase: str, count: int = 3, exclude_ids=None):
    pool = get_augments_by_tier(tier)
    exclude_ids = expand_conflicting_augment_ids(exclude_ids or set())

    candidates = []
    for augment in pool:
        timing = augment.get("timing", [])

        if isinstance(timing, str):
            timing = [timing]

        if phase in timing and augment["id"] not in exclude_ids:
            candidates.append(augment)

    if len(candidates) <= count:
        return [serialize_augment(a) for a in candidates]

    picked = random.sample(candidates, count)
    return [serialize_augment(a) for a in picked]

def get_random_augment_choices_for_both_players(tier: str, phase: str, owned, count: int = 3):
    owned_w = expand_conflicting_augment_ids({aug["id"] for aug in owned["W"]})
    owned_b = expand_conflicting_augment_ids({aug["id"] for aug in owned["B"]})
    w_choices = get_random_augments_by_tier(tier, phase, count, owned_w)

    banned_ids_for_b = set()

    # countdown이 W에 있으면 B에서는 금지
    if any(aug["id"] == "countdown" for aug in w_choices):
        banned_ids_for_b.add("countdown")

    pool = get_augments_by_tier(tier)

    candidates = []
    for augment in pool:
        timing = augment.get("timing", [])

        if isinstance(timing, str):
            timing = [timing]

        if phase not in timing:
            continue

        if augment["id"] in banned_ids_for_b or augment["id"] in owned_b:
            continue

        candidates.append(augment)

    if len(candidates) <= count:
        b_choices = [serialize_augment(a) for a in candidates]
    else:
        picked = random.sample(candidates, count)
        b_choices = [serialize_augment(a) for a in picked]

    return w_choices, b_choices


def get_player_specific_augment_choices(room, base_tier: str, phase: str, count: int = 3):
    owned = room["owned"]
    tier_w = tier_for_player(room, "W", base_tier)
    tier_b = tier_for_player(room, "B", base_tier)
    owned_w = expand_conflicting_augment_ids({aug["id"] for aug in owned["W"]})
    owned_b = expand_conflicting_augment_ids({aug["id"] for aug in owned["B"]})
    w_choices = get_random_augments_by_tier(tier_w, phase, count, owned_w)
    b_choices = get_random_augments_by_tier(tier_b, phase, count, owned_b)
    return w_choices, b_choices


def current_augment_phase(room) -> str:
    return "start" if room.get("move_count", 0) == 0 else str(room.get("move_count", 0))


def upgraded_tier(base_tier: str):
    if base_tier == "silver":
        return "gold"
    if base_tier == "gold":
        return "diamond"
    return None


def spawn_home_pawns(board, color: str, count: int):
    row = 5 if color == "W" else 2
    empty = [(x, row) for x in range(8) if board.grid[row][x] is None]
    random.shuffle(empty)
    for x, y in empty[:count]:
        board.spawn_pawn(color, x, y)


def tier_for_player(room, color: str, base_tier: str):
    board = room["board"]
    upgrades = int(board.effects[color].get("augment_upgrade", 0) or 0)
    if upgrades <= 0:
        return base_tier
    board.effects[color]["augment_upgrade"] = max(0, upgrades - 1)
    bumped = upgraded_tier(base_tier)
    if bumped is None:
        spawn_home_pawns(board, color, 2)
        return base_tier
    return bumped


def grant_random_augment(room, color: str, tier: str, guardian_players, count: int = 1):
    phase = current_augment_phase(room)
    exclude_ids = {aug["id"] for aug in room["owned"][color]}
    exclude_ids.update({
        "random_augment_silver",
        "random_augment_gold",
        "random_augment_diamond",
    })
    granted_choices = get_random_augments_by_tier(tier, phase, count, exclude_ids)
    for choice in granted_choices:
        granted = find_augment_by_id(choice["id"])
        if granted is None:
            continue
        if find_owned_augment(room, color, granted["id"]) is not None:
            continue
        room["owned"][color].append(serialize_augment(granted))
        apply_augment_effect(room, color, granted["id"], guardian_players)


def apply_augment_effect(room, apply_color: str, augment_id: str, guardian_players):
    board = room["board"]
    enemy_color = "B" if apply_color == "W" else "W"

    if augment_id == "guardian_of_balance":
        guardian_players.append(apply_color)
        return

    if augment_id == "blitz_game":
        room["time"][enemy_color] = max(0, room["time"][enemy_color] - 420)
        if room["time"][enemy_color] <= 0:
            room["time"][enemy_color] = 0
            room["time"]["ended"] = True
            room["time"]["winner"] = apply_color

    elif augment_id == "bullet_game":
        room["time"][enemy_color] = max(0, room["time"][enemy_color] - 540)
        if room["time"][enemy_color] <= 0:
            room["time"][enemy_color] = 0
            room["time"]["ended"] = True
            room["time"]["winner"] = apply_color

    elif augment_id == "death_mark":
        if not apply_death_mark_to_enemy(room, apply_color):
            return

    augment = find_augment_by_id(augment_id)
    if augment is not None:
        augment["apply"](board, apply_color)

    if augment_id == "random_augment_silver":
        grant_random_augment(room, apply_color, "silver", guardian_players)
    elif augment_id == "random_augment_gold":
        grant_random_augment(room, apply_color, "gold", guardian_players)
    elif augment_id == "random_augment_diamond":
        grant_random_augment(room, apply_color, "diamond", guardian_players)
    elif augment_id == "true_gambler":
        grant_random_augment(room, apply_color, "gold", guardian_players, count=2)


def augment_apply_priority(augment_id: str) -> int:
    if augment_id == "twin_bishops":
        return 0
    return 1


def debug_serialize_augment_catalog():
    return [
        {
            "id": augment["id"],
            "title": augment["name"],
            "tier": augment["tier"],
        }
        for augment in ALL_AUGMENTS
    ]

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    pieces_dir = STATIC_DIR / "pieces"
    if pieces_dir.exists():
        app.mount("/pieces", StaticFiles(directory=pieces_dir), name="pieces")


@app.post("/create_room")
def create_room():
    room_id = uuid4().hex[:6].upper()
    rooms[room_id] = create_room_data()
    return {"room_id": room_id}


# DEBUG AUGMENT PANEL START
@app.get("/debug/augments")
def debug_augments():
    return {"augments": debug_serialize_augment_catalog()}


@app.post("/rooms/{room_id}/debug/grant_augment")
async def debug_grant_augment(room_id: str, req: DebugGrantAugmentRequest):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="room not found")

    requester_color = get_player_color(room, req.player_id)
    if requester_color is None:
        raise HTTPException(status_code=403, detail="only players can use debug augment grant")

    target_color = (req.target_color or "").upper()
    if target_color not in {"W", "B"}:
        raise HTTPException(status_code=400, detail="target_color must be W or B")

    augment = find_augment_by_id(req.augment_id)
    if augment is None:
        raise HTTPException(status_code=404, detail="augment not found")

    if find_owned_augment(room, target_color, req.augment_id) is not None:
        raise HTTPException(status_code=400, detail="augment already owned")

    guardian_players = []
    room["owned"][target_color].append(serialize_augment(augment))
    apply_augment_effect(room, target_color, req.augment_id, guardian_players)

    if guardian_players:
        room["guardian"]["active"] = True
        room["guardian"]["queue"].extend([color for color in guardian_players if color not in room["guardian"]["queue"]])
        if room["guardian"]["current"] is None and room["guardian"]["queue"]:
            room["guardian"]["current"] = room["guardian"]["queue"][0]
            room["guardian"]["start_time"] = time.time()
            room["time"]["running"] = None

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })
    return {"success": True, "state": build_state(room)}
# DEBUG AUGMENT PANEL END


@app.post("/rooms/{room_id}/join")
async def join_room(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    room = rooms[room_id]
    players = room["players"]
    debug_mode = bool(data.get("debug"))

    if players["W"] == player_id:
        if debug_mode:
            room["debug"] = True
        return {"color": "W"}
    if players["B"] == player_id:
        if debug_mode:
            room["debug"] = True
        return {"color": "B"}

    if players["W"] is None:
        players["W"] = player_id
        if debug_mode:
            room["debug"] = True
        return {"color": "W"}

    if players["B"] is None:
        players["B"] = player_id
        if debug_mode:
            room["debug"] = True

        room["time"]["last_update"] = time.time()
        if room.get("debug"):
            room["time"]["running"] = room["board"].turn
            room["augment"]["active"] = False
            room["augment"]["start_time"] = None
            room["augment"]["tier"] = None
            room["augment"]["choices"]["W"] = []
            room["augment"]["choices"]["B"] = []
            room["augment"]["selected"]["W"] = None
            room["augment"]["selected"]["B"] = None
        else:
            room["time"]["running"] = None
            room["augment"]["active"] = True
            room["augment"]["start_time"] = time.time()

            tier_index = room["augment"]["current_index"]
            tier = room["augment"]["plan"][tier_index]
            room["augment"]["tier"] = tier
            room["augment"]["current_index"] += 1

            w_choices, b_choices = get_player_specific_augment_choices(room, tier, "start", 3)
            room["augment"]["choices"]["W"] = w_choices
            room["augment"]["choices"]["B"] = b_choices

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })

        return {"color": "B"}

    return {"color": "S"}


@app.get("/rooms/{room_id}/state")
async def get_state(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room = rooms[room_id]
    update_clock(room)
    await resolve_guardian_timeout(room_id)
    return build_state(room)


@app.post("/rooms/{room_id}/move")
async def move(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room = rooms[room_id]
    board = room["board"]
    update_clock(room)

    if room["time"]["ended"]:
        return {
            "result": {"success": False, "message": "시간 종료"},
            "state": build_state(room),
        }

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    if room["players"]["W"] == player_id:
        player_color = "W"
    elif room["players"]["B"] == player_id:
        player_color = "B"
    else:
        return {
            "result": {"success": False, "message": "관전자는 움직일 수 없음"},
            "state": build_state(room),
        }

    game_state = board.get_game_state()
    if game_state["checkmate"] or game_state["draw"]:
        return {
            "result": {"success": False, "message": "이미 끝난 게임임"},
            "state": build_state(room),
        }

    if board.turn != player_color:
        return {
            "result": {"success": False, "message": "지금 네 턴이 아님"},
            "state": build_state(room),
        }

    x1, y1, x2, y2 = data["x1"], data["y1"], data["x2"], data["y2"]
    promotion = data.get("promotion", "Q")
    piece = board.grid[y1][x1]

    if piece is None:
        return {
            "result": {"success": False, "message": "거기에 기물이 없음"},
            "state": build_state(room),
        }

    if piece.color != player_color:
        return {
            "result": {"success": False, "message": "네 기물만 움직일 수 있음"},
            "state": build_state(room),
        }

    result = board.move_piece_web(x1, y1, x2, y2, promotion)
    if result["success"]:
        if result.get("extra_turn") != "twin_bishop":
            advance_room_after_turn(room, room_id, player_color)
        else:
            room["time"]["running"] = board.turn
            room["time"]["last_update"] = time.time()
             
        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })

    return {"result": result, "state": build_state(room)}


@app.get("/rooms/{room_id}/legal_moves")
def legal_moves(room_id: str, x: int, y: int):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404)

    board = room["board"]
    if not board.in_bounds(x, y):
        return {"moves": []}

    piece = board.grid[y][x]
    if piece is None:
        return {"moves": []}

    return {"moves": board.get_legal_moves(x, y)}


@app.post("/rooms/{room_id}/augment/activate")
async def activate_augment(room_id: str, req: AugmentActivateRequest):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404)

    color = get_player_color(room, req.player_id)
    if color is None:
        raise HTTPException(status_code=403, detail="only players can activate augment")

    owned = find_owned_augment(room, color, req.augment_id)
    if owned is None:
        raise HTTPException(status_code=404, detail="augment not owned")
    if owned.get("used"):
        raise HTTPException(status_code=400, detail="augment already used")

    board = room["board"]
    if not board.in_bounds(req.x, req.y):
        raise HTTPException(status_code=400, detail="invalid target")

    if req.augment_id == "pawn_evolution":
        piece = board.grid[req.y][req.x]
        if piece is None or piece.color != color or piece.name != "P":
            raise HTTPException(status_code=400, detail="target must be your pawn")
        if board.turn != color:
            raise HTTPException(status_code=400, detail="not your turn")

        choice = (req.choice or "N").upper()
        if choice not in {"N", "B"}:
            raise HTTPException(status_code=400, detail="choice must be N or B")

        board.grid[req.y][req.x] = board.create_piece(choice, color)
        owned["used"] = True
        board.finish_turn(color, apply_special_check=False)
        advance_room_after_turn(room, room_id, color)
    elif req.augment_id == "emergency_escape":
        if req.x2 is None or req.y2 is None:
            raise HTTPException(status_code=400, detail="destination required")
        if not board.in_bounds(req.x2, req.y2):
            raise HTTPException(status_code=400, detail="invalid destination")
        piece = board.grid[req.y][req.x]
        if piece is None or piece.color != color or piece.name != "K":
            raise HTTPException(status_code=400, detail="target must be your king")
        if board.turn != color:
            raise HTTPException(status_code=400, detail="not your turn")
        if not board.is_in_check(color):
            raise HTTPException(status_code=400, detail="not in check")
        if board.grid[req.y2][req.x2] is not None:
            raise HTTPException(status_code=400, detail="destination must be empty")
        if (req.x2, req.y2) not in board.get_legal_moves(req.x, req.y):
            raise HTTPException(status_code=400, detail="destination is not safe")
        board._apply_move(req.x, req.y, req.x2, req.y2)
        owned["used"] = True
        board.finish_turn(color, apply_special_check=False)
        advance_room_after_turn(room, room_id, color)
    elif req.augment_id == "ambush_setup":
        if req.x2 is None or req.y2 is None:
            raise HTTPException(status_code=400, detail="destination required")
        if not board.in_bounds(req.x2, req.y2):
            raise HTTPException(status_code=400, detail="invalid destination")
        piece = board.grid[req.y][req.x]
        if piece is None or piece.color != color:
            raise HTTPException(status_code=400, detail="target must be your piece")
        if room["move_count"] != 0:
            raise HTTPException(status_code=400, detail="ambush setup is only available before the first move")
        if (req.x2, req.y2) not in board.get_legal_moves(req.x, req.y):
            raise HTTPException(status_code=400, detail="invalid setup move")
        board._apply_move(req.x, req.y, req.x2, req.y2)
        owned["used"] = True
    elif req.augment_id == "king_breeding":
        if req.x2 is None or req.y2 is None:
            raise HTTPException(status_code=400, detail="queen target required")
        if not board.in_bounds(req.x2, req.y2):
            raise HTTPException(status_code=400, detail="invalid queen target")
        if board.turn != color:
            raise HTTPException(status_code=400, detail="not your turn")

        king_piece = board.grid[req.y][req.x]
        queen_piece = board.grid[req.y2][req.x2]
        if king_piece is None or king_piece.color != color or king_piece.name != "K":
            raise HTTPException(status_code=400, detail="target must be your king")
        if queen_piece is None or queen_piece.color != color or queen_piece.name != "Q":
            raise HTTPException(status_code=400, detail="second target must be your queen")
        if max(abs(req.x2 - req.x), abs(req.y2 - req.y)) != 1:
            raise HTTPException(status_code=400, detail="queen must be adjacent to king")

        spawn_cells = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sx = req.x2 + dx
                sy = req.y2 + dy
                if board.in_bounds(sx, sy) and board.grid[sy][sx] is None:
                    spawn_cells.append((sx, sy))
        if not spawn_cells:
            raise HTTPException(status_code=400, detail="no empty cell around queen")

        spawn_x, spawn_y = random.choice(spawn_cells)
        board.spawn_pawn(color, spawn_x, spawn_y)
        board.finish_turn(color, apply_special_check=False)
        advance_room_after_turn(room, room_id, color)
    else:
        raise HTTPException(status_code=400, detail="augment is not activatable")

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })
    return {"success": True, "state": build_state(room)}


@app.post("/rooms/{room_id}/reset")
def reset_room(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    old_players = rooms[room_id]["players"]
    rooms[room_id] = create_room_data()
    rooms[room_id]["players"] = old_players

    if old_players["W"] is not None and old_players["B"] is not None:
        rooms[room_id]["time"]["last_update"] = time.time()
        rooms[room_id]["time"]["running"] = None

    return {"success": True}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if room_id not in connections:
        connections[room_id] = []

    connections[room_id].append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections[room_id].remove(websocket)


async def broadcast(room_id: str, message: dict):
    if room_id not in connections:
        return

    dead = []
    for ws in connections[room_id]:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(ws)

    for ws in dead:
        connections[room_id].remove(ws)


async def resolve_guardian_timeout(room_id: str):
    if room_id not in rooms:
        return

    room = rooms[room_id]
    guardian = room["guardian"]

    if not guardian["active"]:
        return
    if guardian["start_time"] is None:
        return

    elapsed = time.time() - guardian["start_time"]
    if elapsed < GUARDIAN_DURATION:
        return

    board = room["board"]
    color = guardian["current"]

    for sx, sy in guardian.get("selected_self_group") or ([] if guardian["selected_self"] is None else [guardian["selected_self"]]):
        if board.in_bounds(sx, sy):
            board.grid[sy][sx] = None

    for ex, ey in guardian["selected_enemy"]:
        if board.in_bounds(ex, ey):
            board.grid[ey][ex] = None

    if guardian["queue"] and guardian["queue"][0] == color:
        guardian["queue"].pop(0)
    else:
        guardian["queue"] = [c for c in guardian["queue"] if c != color]

    guardian["selected_self"] = None
    guardian["selected_self_group"] = []
    guardian["selected_enemy"] = []
    guardian["selected_enemy_groups"] = []
    guardian["score"] = 0
    guardian["max_score"] = 0

    if guardian["queue"]:
        guardian["current"] = guardian["queue"][0]
        guardian["start_time"] = time.time()
    else:
        guardian["active"] = False
        guardian["current"] = None
        guardian["start_time"] = None
        room["time"]["last_update"] = time.time()
        room["time"]["running"] = room["board"].turn

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })


def reset_room_with_swap(room_id: str):
    old_room = rooms[room_id]
    old_players = old_room["players"]

    new_room = create_room_data()
    new_room["debug"] = old_room.get("debug", False)
    new_room["players"] = {
        "W": old_players["B"],
        "B": old_players["W"],
    }

    if new_room["players"]["W"] is not None and new_room["players"]["B"] is not None:
        new_room["time"]["last_update"] = time.time()
        if new_room.get("debug"):
            new_room["time"]["running"] = new_room["board"].turn
            new_room["augment"]["active"] = False
            new_room["augment"]["start_time"] = None
            new_room["augment"]["tier"] = None
            new_room["augment"]["choices"]["W"] = []
            new_room["augment"]["choices"]["B"] = []
        else:
            new_room["time"]["running"] = None
            new_room["augment"]["active"] = True
            new_room["augment"]["start_time"] = time.time()

            tier_index = new_room["augment"]["current_index"]
            tier = new_room["augment"]["plan"][tier_index]
            new_room["augment"]["tier"] = tier
            new_room["augment"]["current_index"] += 1

            w_choices, b_choices = get_player_specific_augment_choices(new_room, tier, "start", 3)
            new_room["augment"]["choices"]["W"] = w_choices
            new_room["augment"]["choices"]["B"] = b_choices

    rooms[room_id] = new_room


@app.post("/rooms/{room_id}/rematch")
async def rematch_room(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    room = rooms[room_id]
    players = room["players"]

    if players["W"] == player_id:
        player_color = "W"
    elif players["B"] == player_id:
        player_color = "B"
    else:
        raise HTTPException(status_code=403, detail="only players can request rematch")

    rematch = room["rematch"]

    if not rematch["votes"][player_color]:
        rematch["votes"][player_color] = True
        rematch["count"] += 1

    await broadcast(room_id, {
        "type": "rematch_vote",
        "state": build_state(room),
    })

    if rematch["count"] >= 2:
        reset_room_with_swap(room_id)
        await broadcast(room_id, {
            "type": "update",
            "state": build_state(rooms[room_id]),
        })
        return {"success": True, "started": True, "state": build_state(rooms[room_id])}

    return {"success": True, "started": False, "state": build_state(room)}


@app.post("/rooms/{room_id}/augment/select")
async def select_augment(room_id: str, req: AugmentSelectRequest):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404)

    color = get_player_color(room, req.player_id)
    if color is None:
        raise HTTPException(status_code=403, detail="only players can select augment")

    if room["augment"]["selected"][color] is not None:
        raise HTTPException(status_code=400)
    if find_owned_augment(room, color, req.augment_id) is not None:
        raise HTTPException(status_code=400, detail="augment already owned")

    if req.augment_id == "death_mark":
        enemy = "B" if color == "W" else "W"
        if not get_death_mark_candidates(room["board"], enemy):
            raise HTTPException(status_code=400, detail="death_mark has no valid target")

    room["augment"]["selected"][color] = req.augment_id

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })

    both_done = (
        room["augment"]["selected"]["W"] is not None and
        room["augment"]["selected"]["B"] is not None
    )

    if both_done:
        board = room["board"]
        guardian_players = []

        apply_order = sorted(
            ["W", "B"],
            key=lambda color: (augment_apply_priority(room["augment"]["selected"][color]), 0 if color == "W" else 1),
        )

        for apply_color in apply_order:
            board.effects[apply_color].pop("sealed_queen", None)

            augment_id = room["augment"]["selected"][apply_color]
            picked_augment = find_augment_by_id(augment_id)
            if picked_augment is not None and find_owned_augment(room, apply_color, augment_id) is None:
                room["owned"][apply_color].append(serialize_augment(picked_augment))
            apply_augment_effect(room, apply_color, augment_id, guardian_players)

        room["guardian"] = {
            "active": len(guardian_players) > 0,
            "queue": guardian_players,
            "current": guardian_players[0] if guardian_players else None,
            "selected_self": None,
            "selected_self_group": [],
            "selected_enemy": [],
            "selected_enemy_groups": [],
            "score": 0,
            "max_score": 0,
            "start_time": time.time() if guardian_players else None,
        }

        room["augment"]["active"] = False
        room["augment"]["start_time"] = None
        room["time"]["last_update"] = time.time()

        if room["guardian"]["active"]:
            room["time"]["running"] = None
        else:
            room["time"]["running"] = room["board"].turn

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })
        
    return {
        "both_done": both_done,
        "state": build_state(room),
    }


@app.post("/rooms/{room_id}/guardian/select_self")
async def guardian_select_self(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room = rooms[room_id]
    await resolve_guardian_timeout(room_id)
    guardian = room["guardian"]

    if not guardian["active"]:
        return {"success": False, "state": build_state(room)}

    player_id = data.get("player_id")
    x = data.get("x")
    y = data.get("y")

    if player_id is None:
        raise HTTPException(status_code=400, detail="player_id required")
    if x is None or y is None:
        raise HTTPException(status_code=400, detail="x, y required")

    color = get_player_color(room, player_id)
    if color is None:
        raise HTTPException(status_code=403, detail="only players can use guardian")

    if guardian["current"] != color:
        raise HTTPException(status_code=400, detail="not your guardian turn")

    board = room["board"]
    if not board.in_bounds(x, y):
        raise HTTPException(status_code=400, detail="out of bounds")

    piece = board.grid[y][x]
    if piece is None:
        raise HTTPException(status_code=400, detail="piece not found")

    if piece.color != color:
        raise HTTPException(status_code=400, detail="must select your own piece")

    if piece.name == "K":
        raise HTTPException(status_code=400, detail="king cannot be selected")

    selected_self_group = guardian.get("selected_self_group") or []
    linked_positions = guardian_linked_positions(board, piece)

    if [x, y] in selected_self_group:
        if guardian["selected_enemy"]:
            raise HTTPException(status_code=400, detail="enemy pieces already selected")

        guardian["selected_self"] = None
        guardian["selected_self_group"] = []
        guardian["selected_enemy"] = []
        guardian["selected_enemy_groups"] = []
        guardian["max_score"] = 0
        guardian["score"] = 0

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })
        return {"success": True, "state": build_state(room)}

    guardian["selected_self"] = [x, y]
    guardian["selected_self_group"] = linked_positions
    guardian["selected_enemy"] = []
    guardian["selected_enemy_groups"] = []
    guardian["max_score"] = piece_value(board, piece)
    guardian["score"] = 0

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })
    return {"success": True, "state": build_state(room)}


@app.post("/rooms/{room_id}/guardian/toggle_enemy")
async def guardian_toggle_enemy(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room = rooms[room_id]
    await resolve_guardian_timeout(room_id)
    guardian = room["guardian"]

    if not guardian["active"]:
        return {"success": False, "state": build_state(room)}

    player_id = data.get("player_id")
    x = data.get("x")
    y = data.get("y")

    if player_id is None:
        raise HTTPException(status_code=400, detail="player_id required")
    if x is None or y is None:
        raise HTTPException(status_code=400, detail="x, y required")

    color = get_player_color(room, player_id)
    if color is None:
        raise HTTPException(status_code=403, detail="only players can use guardian")

    if guardian["current"] != color:
        raise HTTPException(status_code=400, detail="not your guardian turn")

    if not guardian["selected_self"]:
        raise HTTPException(status_code=400, detail="select self piece first")

    board = room["board"]
    if not board.in_bounds(x, y):
        raise HTTPException(status_code=400, detail="out of bounds")

    piece = board.grid[y][x]
    if piece is None:
        raise HTTPException(status_code=400, detail="piece not found")

    if piece.color == color:
        raise HTTPException(status_code=400, detail="must select enemy piece")

    if piece.name == "K":
        raise HTTPException(status_code=400, detail="king cannot be selected")

    pos = [x, y]
    linked_positions = guardian_linked_positions(board, piece)
    value = piece_value(board, piece)
    selected_enemy_groups = guardian.get("selected_enemy_groups") or []

    existing_group = None
    for group in selected_enemy_groups:
        if pos in group.get("positions", []):
            existing_group = group
            break

    # 이미 선택된 상대 기물이면 취소
    if existing_group is not None:
        selected_enemy_groups.remove(existing_group)
        guardian["selected_enemy_groups"] = selected_enemy_groups
        guardian["selected_enemy"] = flatten_guardian_groups(selected_enemy_groups)
        guardian["score"] -= int(existing_group.get("value", 0))
        if guardian["score"] < 0:
            guardian["score"] = 0

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })
        return {"success": True, "state": build_state(room)}

    # 새로 선택하려는데 점수 초과면 불가
    if guardian["score"] + value > guardian["max_score"]:
        raise HTTPException(status_code=400, detail="score exceeded")

    current_enemy_positions = flatten_guardian_groups(selected_enemy_groups)
    test_enemy = current_enemy_positions + [linked for linked in linked_positions if linked not in current_enemy_positions]
    self_positions = guardian.get("selected_self_group") or ([guardian["selected_self"]] if guardian.get("selected_self") else [])

    if guardian_selection_causes_illegal_check(
        board,
        color,
        self_positions,
        test_enemy,
    ):
        raise HTTPException(status_code=400, detail="illegal guardian selection")

    selected_enemy_groups.append({
        "positions": linked_positions,
        "value": value,
    })
    guardian["selected_enemy_groups"] = selected_enemy_groups
    guardian["selected_enemy"] = flatten_guardian_groups(selected_enemy_groups)
    guardian["score"] += value

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })
    return {"success": True, "state": build_state(room)}


@app.post("/rooms/{room_id}/guardian/confirm")
async def guardian_confirm(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room = rooms[room_id]
    await resolve_guardian_timeout(room_id)
    guardian = room["guardian"]

    if not guardian["active"]:
        return {"success": False, "state": build_state(room)}

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    color = get_player_color(room, player_id)
    if color is None:
        raise HTTPException(status_code=403, detail="only players can confirm guardian")

    if guardian["current"] != color:
        raise HTTPException(status_code=400, detail="not your guardian turn")

    if not guardian["selected_self"]:
        raise HTTPException(status_code=400, detail="must select self piece first")

    board = room["board"]

    for sx, sy in guardian.get("selected_self_group") or ([] if guardian["selected_self"] is None else [guardian["selected_self"]]):
        if board.in_bounds(sx, sy):
            board.grid[sy][sx] = None

    for ex, ey in guardian["selected_enemy"]:
        if board.in_bounds(ex, ey):
            board.grid[ey][ex] = None

    if guardian["queue"] and guardian["queue"][0] == color:
        guardian["queue"].pop(0)
    else:
        guardian["queue"] = [c for c in guardian["queue"] if c != color]

    guardian["selected_self"] = None
    guardian["selected_self_group"] = []
    guardian["selected_enemy"] = []
    guardian["selected_enemy_groups"] = []
    guardian["score"] = 0
    guardian["max_score"] = 0

    if guardian["queue"]:
        guardian["current"] = guardian["queue"][0]
        guardian["start_time"] = time.time()
    else:
        guardian["active"] = False
        guardian["current"] = None
        guardian["start_time"] = None
        room["time"]["last_update"] = time.time()
        room["time"]["running"] = room["board"].turn

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room),
    })
    return {"success": True, "state": build_state(room)}
