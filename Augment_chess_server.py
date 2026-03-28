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
from Augment_silver import SILVER_AUGMENTS
from Augment_gold import GOLD_AUGMENTS
from Augment_diamond import DIAMOND_AUGMENTS

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


def create_room_data():
    tiers = ["silver", "gold", "diamond"]

    augment_tiers = [
        random.choice(tiers),
        random.choice(tiers)
    ]
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
            "tier_queue": augment_tiers,
            "current_index": 0,
            "choices": {"W": [], "B": []},
            "selected": {"W": None, "B": None},
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
            "selected_enemy": [],
            "score": 0,
            "max_score": 0,
            "start_time": None,
        },
    }


def build_state(room):
    data = room["board"].to_dict()
    data["clock"] = room["time"]
    data["rematch"] = room["rematch"]
    data["players"] = room["players"]
    data["move_count"] = room["move_count"]

    augment_state = dict(room["augment"])
    augment_state["owned"] = room["owned"]
    data["augment"] = augment_state

    guardian_state = dict(room["guardian"])
    if guardian_state["active"] and guardian_state["start_time"] is not None:
        remain = GUARDIAN_DURATION - (time.time() - guardian_state["start_time"])
        guardian_state["remaining_ms"] = max(0, int(remain * 1000))
    else:
        guardian_state["remaining_ms"] = 0

    data["guardian"] = guardian_state
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


def piece_value(name: str) -> int:
    if name == "P":
        return 1
    if name in ("N", "B"):
        return 3
    if name == "R":
        return 5
    if name == "Q":
        return 9
    return 0


def guardian_selection_causes_illegal_check(board, color, self_pos, enemy_positions):
    removed = []

    sx, sy = self_pos
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
    }
    
def get_augments_by_tier(tier: str):
    if tier == "silver":
        return SILVER_AUGMENTS
    if tier == "gold":
        return GOLD_AUGMENTS
    if tier == "diamond":
        return DIAMOND_AUGMENTS
    return []


def get_random_augments_by_tier(tier: str, phase: str, count: int = 3):
    pool = get_augments_by_tier(tier)

    candidates = []
    for augment in pool:
        timing = augment.get("timing", [])

        if isinstance(timing, str):
            timing = [timing]

        if phase in timing:
            candidates.append(augment)

    if len(candidates) <= count:
        return [serialize_augment(a) for a in candidates]

    picked = random.sample(candidates, count)
    return [serialize_augment(a) for a in picked]


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


@app.post("/rooms/{room_id}/join")
async def join_room(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    room = rooms[room_id]
    players = room["players"]

    if players["W"] == player_id:
        return {"color": "W"}
    if players["B"] == player_id:
        return {"color": "B"}

    if players["W"] is None:
        players["W"] = player_id
        return {"color": "W"}

    if players["B"] is None:
        players["B"] = player_id

        room["time"]["last_update"] = time.time()
        room["time"]["running"] = None
        room["augment"]["active"] = True

        tier = "silver"

        room["augment"]["choices"]["W"] = get_random_augments_by_tier(tier, "start", 3)
        room["augment"]["choices"]["B"] = get_random_augments_by_tier(tier, "start", 3)

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
        room["move_count"] += 1

        if room["move_count"] in (20, 40):
            room["time"]["running"] = None
            room["time"]["last_update"] = time.time()

            room["augment"]["active"] = True
            room["augment"]["selected"]["W"] = None
            room["augment"]["selected"]["B"] = None

            room["augment"]["choices"]["W"] = [
                {"id": "a1", "tier": "gold", "title": "캐슬링 금지", "description": "..."},
                {"id": "a2", "tier": "gold", "title": "언더 프로모션!!", "description": "..."},
                {"id": "a3", "tier": "gold", "title": "폰 둔화", "description": "..."},
            ]
            room["augment"]["choices"]["B"] = [
                {"id": "b1", "tier": "gold", "title": "룩 약화", "description": "..."},
                {"id": "b2", "tier": "gold", "title": "비숍 약화", "description": "..."},
                {"id": "b3", "tier": "gold", "title": "전장의 안개", "description": "..."},
            ]
        else:
            room["time"]["running"] = board.turn
            room["time"]["last_update"] = time.time()

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })

    return {"result": result, "state": build_state(room)}


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

    if guardian["selected_self"]:
        sx, sy = guardian["selected_self"]
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
    guardian["selected_enemy"] = []
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
    new_room["players"] = {
        "W": old_players["B"],
        "B": old_players["W"],
    }

    if new_room["players"]["W"] is not None and new_room["players"]["B"] is not None:
        new_room["time"]["last_update"] = time.time()
        new_room["time"]["running"] = None

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

    room["augment"]["selected"][color] = req.augment_id
    picked_augment = find_augment_by_id(req.augment_id)
    if picked_augment is not None:
        room["owned"][color].append(serialize_augment(picked_augment))

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

        for apply_color in ["W", "B"]:
            augment_id = room["augment"]["selected"][apply_color]

            if augment_id == "guardian_of_balance":
                guardian_players.append(apply_color)
            else:
                augment = find_augment_by_id(augment_id)
                if augment is not None:
                    augment["apply"](board, apply_color)

        room["guardian"] = {
            "active": len(guardian_players) > 0,
            "queue": guardian_players,
            "current": guardian_players[0] if guardian_players else None,
            "selected_self": None,
            "selected_enemy": [],
            "score": 0,
            "max_score": 0,
            "start_time": time.time() if guardian_players else None,
        }

        room["augment"]["active"] = False
        room["time"]["last_update"] = time.time()

        if room["guardian"]["active"]:
            room["time"]["running"] = None
        else:
            room["time"]["running"] = room["board"].turn

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })


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

    if guardian["selected_self"] == [x, y]:
        if guardian["selected_enemy"]:
            raise HTTPException(status_code=400, detail="enemy pieces already selected")

        guardian["selected_self"] = None
        guardian["selected_enemy"] = []
        guardian["max_score"] = 0
        guardian["score"] = 0

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room),
        })
        return {"success": True, "state": build_state(room)}

    guardian["selected_self"] = [x, y]
    guardian["selected_enemy"] = []
    guardian["max_score"] = piece_value(piece.name)
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
    value = piece_value(piece.name)

    # 이미 선택된 상대 기물이면 취소
    if pos in guardian["selected_enemy"]:
        guardian["selected_enemy"].remove(pos)
        guardian["score"] -= value
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

    test_enemy = guardian["selected_enemy"] + [pos]

    if guardian_selection_causes_illegal_check(
        board,
        color,
        guardian["selected_self"],
        test_enemy,
    ):
        raise HTTPException(status_code=400, detail="illegal guardian selection")

    guardian["selected_enemy"].append(pos)
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

    sx, sy = guardian["selected_self"]
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
    guardian["selected_enemy"] = []
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