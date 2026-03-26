from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random


@dataclass
class Piece:
    name: str
    color: str


class Board:
    def __init__(self):
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.turn = "W"
        self.last_move: Optional[Tuple[int, int, int, int]] = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.position_history: Dict[str, int] = {}
        self.en_passant_target: Optional[Tuple[int, int]] = None
        self.king_moved = {"W": False, "B": False}
        self.rook_moved = {
            "W": {"left": False, "right": False},
            "B": {"left": False, "right": False},
        }
        self.effects = {
            "W": {},
            "B": {}
        }
        self.setup()
        self._record_position()

    def setup(self):
        for i in range(8):
            self.grid[1][i] = Piece("P", "B")
            self.grid[6][i] = Piece("P", "W")

        order = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        for i, name in enumerate(order):
            self.grid[0][i] = Piece(name, "B")
            self.grid[7][i] = Piece(name, "W")

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < 8 and 0 <= y < 8
    def spawn_pawn(self, color, x, y):
        self.grid[y][x] = Piece("P", color)

    def create_piece(self, piece_type, color):
        return Piece(piece_type, color)

    def move_piece_web(self, x1: int, y1: int, x2: int, y2: int, promotion: str = "Q"):
        if not all(isinstance(v, int) for v in [x1, y1, x2, y2]):
            return {"success": False, "message": "좌표 오류"}
        if not all(self.in_bounds(vx, vy) for vx, vy in [(x1, y1), (x2, y2)]):
            return {"success": False, "message": "보드 밖 좌표"}

        piece = self.grid[y1][x1]
        if piece is None:
            return {"success": False, "message": "기물 없음"}
        if piece.color != self.turn:
            return {"success": False, "message": "턴 아님"}
        if (x1, y1) == (x2, y2):
            return {"success": False, "message": "같은 칸으로 이동 불가"}

        legal_moves = self.get_legal_moves(x1, y1)
        if (x2, y2) not in legal_moves:
            return {"success": False, "message": "불가능한 이동"}

        promotion = (promotion or "Q").upper()
        if promotion not in {"Q", "R", "B", "N"}:
            promotion = "Q"

        consume_pawn_slow = False

        if piece.name == "P":
            start_row = 6 if piece.color == "W" else 1
            weaken_count = self.effects[piece.color].get("pawn_slow", 0)

            if y1 == start_row and weaken_count > 0:
                if x1 == x2 and abs(y2 - y1) == 2:
                    return {
                        "success": False,
                        "message": "달팽이 폰: 처음 2개의 폰은 2칸 전진 불가"
                    }
                consume_pawn_slow = True

        self._apply_move(x1, y1, x2, y2, promotion)

        if consume_pawn_slow:
            self.effects[piece.color]["pawn_slow"] -= 1
            if self.effects[piece.color]["pawn_slow"] <= 0:
                self.effects[piece.color].pop("pawn_slow", None)

        self.turn = "B" if self.turn == "W" else "W"
        if self.turn == "W":
            self.fullmove_number += 1
        self._record_position()
        return {"success": True}

    def _apply_move(self, x1: int, y1: int, x2: int, y2: int, promotion: str = "Q"):
        piece = self.grid[y1][x1]
        target = self.grid[y2][x2]
        
        if piece is None:
            return

        is_en_passant = (
            piece.name == "P"
            and x1 != x2
            and target is None
            and self.en_passant_target == (x2, y2)
        )
        captured_piece = target

        if is_en_passant:
            capture_y = y2 + 1 if piece.color == "W" else y2 - 1
            captured_piece = self.grid[capture_y][x2]
            self.grid[capture_y][x2] = None


        if piece.name == "K" and abs(x2 - x1) == 2:
            if x2 > x1:
                rook_from_x, rook_to_x = 7, 5
                self.rook_moved[piece.color]["right"] = True
            else:
                rook_from_x, rook_to_x = 0, 3
                self.rook_moved[piece.color]["left"] = True
            self.grid[y1][rook_to_x] = self.grid[y1][rook_from_x]
            self.grid[y1][rook_from_x] = None
            self.king_moved[piece.color] = True

        if piece.name == "K":
            self.king_moved[piece.color] = True

        if piece.name == "R":
            if piece.color == "W" and y1 == 7:
                if x1 == 0:
                    self.rook_moved["W"]["left"] = True
                elif x1 == 7:
                    self.rook_moved["W"]["right"] = True
            if piece.color == "B" and y1 == 0:
                if x1 == 0:
                    self.rook_moved["B"]["left"] = True
                elif x1 == 7:
                    self.rook_moved["B"]["right"] = True

        if captured_piece and captured_piece.name == "R":
            if captured_piece.color == "W" and y2 == 7:
                if x2 == 0:
                    self.rook_moved["W"]["left"] = True
                elif x2 == 7:
                    self.rook_moved["W"]["right"] = True
            if captured_piece.color == "B" and y2 == 0:
                if x2 == 0:
                    self.rook_moved["B"]["left"] = True
                elif x2 == 7:
                    self.rook_moved["B"]["right"] = True

        self.grid[y2][x2] = piece
        self.grid[y1][x1] = None
        if captured_piece is not None and captured_piece.name in {"B", "N"}:
            owner = captured_piece.color
            if self.effects[owner].get("reorganize", 0) > 0:
                empty_cells = []

                for yy in range(8):
                    for xx in range(8):
                        if self.grid[yy][xx] is None:
                            empty_cells.append((xx, yy))

                if empty_cells:
                    spawn_x, spawn_y = random.choice(empty_cells)
                    self.spawn_pawn(owner, spawn_x, spawn_y)

                self.effects[owner]["reorganize"] -= 1

        if piece.name == "P" and ((piece.color == "W" and y2 == 0) or (piece.color == "B" and y2 == 7)):
            promotion = (promotion or "Q").upper()
            if promotion not in {"Q", "R", "B", "N"}:
                promotion = "Q"
            self.grid[y2][x2] = Piece(promotion, piece.color)

        self.en_passant_target = None
        if piece.name == "P" and abs(y2 - y1) == 2:
            self.en_passant_target = (x1, (y1 + y2) // 2)

        self.last_move = (x1, y1, x2, y2)

        if piece.name == "P" or captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

    def is_valid_move(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        if not self.in_bounds(x1, y1) or not self.in_bounds(x2, y2):
            return False
        if (x1, y1) == (x2, y2):
            return False

        piece = self.grid[y1][x1]
        target = self.grid[y2][x2]
        if piece is None:
            return False
        if target and target.color == piece.color:
            return False

        dx = x2 - x1
        dy = y2 - y1
        adx = abs(dx)
        ady = abs(dy)

        if piece.name == "P":
            direction = -1 if piece.color == "W" else 1
            start_row = 6 if piece.color == "W" else 1

            if dx == 0 and dy == direction and target is None:
                return True
            if self.effects[piece.color].get("pawn_retreat"):
                if dx == 0 and dy == -direction and target is None:
                    return True

            if (
                dx == 0
                and y1 == start_row
                and dy == 2 * direction
                and target is None
                and self.grid[y1 + direction][x1] is None
            ):
                return True

            if adx == 1 and dy == direction:
                if target is not None and target.color != piece.color:
                    return True
                if target is None and self.en_passant_target == (x2, y2):
                    adjacent = self.grid[y1][x2]
                    return adjacent is not None and adjacent.name == "P" and adjacent.color != piece.color
            return False

        if piece.name == "N":
            return (adx, ady) in [(1, 2), (2, 1)]

        if piece.name == "B":
            return adx == ady and self._clear(x1, y1, x2, y2)

        if piece.name == "R":
            return (x1 == x2 or y1 == y2) and self._clear(x1, y1, x2, y2)

        if piece.name == "Q":
            return (adx == ady or x1 == x2 or y1 == y2) and self._clear(x1, y1, x2, y2)

        if piece.name == "K":
    # 원래 1칸 이동
            if adx <= 1 and ady <= 1:
                return True

            # 캐슬링 형태의 가로 2칸은 먼저 처리
            if ady == 0 and adx == 2:
                row = 7 if piece.color == "W" else 0

                # 시작 위치(왕 자리)에서의 가로 2칸은 무조건 캐슬링 판정으로만 처리
                if (x1, y1) == (4, row):
                    return self._can_castle(piece.color, x1, y1, x2)

            # 왕권 강화: 상하좌우로 정확히 2칸
            if self.effects[piece.color].get("king_buff"):
                if (adx == 2 and ady == 0) or (adx == 0 and ady == 2):
                    mid_x = x1 + (dx // 2)
                    mid_y = y1 + (dy // 2)

                    if self.grid[mid_y][mid_x] is not None:
                        return False

                    return True

            return False

    def _clear(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        step_x = 0 if x1 == x2 else (1 if x2 > x1 else -1)
        step_y = 0 if y1 == y2 else (1 if y2 > y1 else -1)
        x, y = x1 + step_x, y1 + step_y
        while (x, y) != (x2, y2):
            if self.grid[y][x] is not None:
                return False
            x += step_x
            y += step_y
        return True

    def _can_castle(self, color: str, x1: int, y1: int, x2: int) -> bool:
        if self.effects[color].get("no_castling"):
            return False
        row = 7 if color == "W" else 0
        if (x1, y1) != (4, row):
            return False
        if self.king_moved[color]:
            return False
        if self.is_in_check(color):
            return False

        kingside = x2 > x1
        side = "right" if kingside else "left"
        rook_x = 7 if kingside else 0
        rook = self.grid[row][rook_x]
        if rook is None or rook.name != "R" or rook.color != color:
            return False
        if self.rook_moved[color][side]:
            return False

        between = [5, 6] if kingside else [1, 2, 3]
        for x in between:
            if self.grid[row][x] is not None:
                return False

        king_path = [5, 6] if kingside else [3, 2]
        for x in king_path:
            temp = deepcopy(self)
            temp.grid[row][x] = temp.grid[row][4]
            temp.grid[row][4] = None
            if temp.is_in_check(color):
                return False
        return True

    def get_legal_moves(self, x: int, y: int):
        piece = self.grid[y][x]
        if piece is None:
            return []

        moves = []

        for yy in range(8):
            for xx in range(8):
                if not self.is_valid_move(x, y, xx, yy):
                    continue

                if piece.name == "P" and (yy == 0 or yy == 7):
                    legal_promotion_found = False
                    for promo in ("Q", "R", "B", "N"):
                        temp = deepcopy(self)
                        temp._apply_move(x, y, xx, yy, promo)
                        if not temp.is_in_check(piece.color):
                            legal_promotion_found = True
                            break
                    if legal_promotion_found:
                        moves.append((xx, yy))
                else:
                    temp = deepcopy(self)
                    temp._apply_move(x, y, xx, yy)
                    if not temp.is_in_check(piece.color):
                        moves.append((xx, yy))

        return moves

    def is_in_check(self, color: str) -> bool:
        king_pos = None
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p and p.name == "K" and p.color == color:
                    king_pos = (x, y)
                    break
            if king_pos:
                break
        if king_pos is None:
            return False

        enemy = "B" if color == "W" else "W"
        kx, ky = king_pos
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p is None or p.color != enemy:
                    continue
                if p.name == "P":
                    direction = -1 if p.color == "W" else 1
                    if (kx, ky) in [(x - 1, y + direction), (x + 1, y + direction)]:
                        return True
                    continue
                if p.name == "K":
                    if max(abs(kx - x), abs(ky - y)) == 1:
                        return True
                    continue
                if self.is_valid_move(x, y, kx, ky):
                    return True
        return False

    def _has_any_legal_move(self, color: str) -> bool:
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p and p.color == color and self.get_legal_moves(x, y):
                    return True
        return False

    def _insufficient_material(self) -> bool:
        pieces = []
        bishops = []
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p is None:
                    continue
                if p.name == "K":
                    continue
                pieces.append((p, x, y))
                if p.name == "B":
                    bishops.append((p.color, (x + y) % 2))

        if not pieces:
            return True
        if len(pieces) == 1 and pieces[0][0].name in {"B", "N"}:
            return True
        if len(pieces) == 2:
            names = sorted([pieces[0][0].name, pieces[1][0].name])
            if names == ["B", "B"]:
                return bishops[0][1] == bishops[1][1]
        return False

    def get_game_state(self):
        check = self.is_in_check(self.turn)
        moves_exist = self._has_any_legal_move(self.turn)

        result = {
            "check": check,
            "checkmate": False,
            "draw": False,
            "draw_reason": None,
            "winner": None,
        }

        if check and not moves_exist:
            result["checkmate"] = True
            result["winner"] = "B" if self.turn == "W" else "W"
            return result

        if not check and not moves_exist:
            result["draw"] = True
            result["draw_reason"] = "stalemate"
            return result

        if self.halfmove_clock >= 100:
            result["draw"] = True
            result["draw_reason"] = "fifty_move"
            return result

        current_key = self._position_key()
        if self.position_history.get(current_key, 0) >= 3:
            result["draw"] = True
            result["draw_reason"] = "threefold_repetition"
            return result

        if self._insufficient_material():
            result["draw"] = True
            result["draw_reason"] = "insufficient_material"
            return result

        return result

    def _castling_key(self) -> str:
        rights = []
        if not self.king_moved["W"] and not self.rook_moved["W"]["right"] and self.grid[7][7] and self.grid[7][7].name == "R" and self.grid[7][7].color == "W":
            rights.append("K")
        if not self.king_moved["W"] and not self.rook_moved["W"]["left"] and self.grid[7][0] and self.grid[7][0].name == "R" and self.grid[7][0].color == "W":
            rights.append("Q")
        if not self.king_moved["B"] and not self.rook_moved["B"]["right"] and self.grid[0][7] and self.grid[0][7].name == "R" and self.grid[0][7].color == "B":
            rights.append("k")
        if not self.king_moved["B"] and not self.rook_moved["B"]["left"] and self.grid[0][0] and self.grid[0][0].name == "R" and self.grid[0][0].color == "B":
            rights.append("q")
        return "".join(rights) or "-"

    def _position_key(self) -> str:
        rows = []
        for y in range(8):
            row = []
            empty = 0
            for x in range(8):
                p = self.grid[y][x]
                if p is None:
                    empty += 1
                    continue
                if empty:
                    row.append(str(empty))
                    empty = 0
                char = p.name.upper() if p.color == "W" else p.name.lower()
                row.append(char)
            if empty:
                row.append(str(empty))
            rows.append("".join(row))
        ep = "-"
        if self.en_passant_target is not None:
            file_char = chr(ord("a") + self.en_passant_target[0])
            rank_char = str(8 - self.en_passant_target[1])
            ep = f"{file_char}{rank_char}"
        return f"{'/'.join(rows)} {self.turn} {self._castling_key()} {ep}"

    def _record_position(self):
        key = self._position_key()
        self.position_history[key] = self.position_history.get(key, 0) + 1

    def to_dict(self):
        return {
            "board": [
                [
                    {"name": p.name, "color": p.color} if p else None
                    for p in row
                ]
                for row in self.grid
            ],
            "turn": self.turn,
            "game_state": self.get_game_state(),
            "last_move": self.last_move,
            "winner": self.get_game_state().get("winner"),
            "effects": self.effects,
        }
