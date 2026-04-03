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
        self.forced_winner = None
        self.special_win_reason = None

    def _effect_piece_is(self, color: str, key: str, piece: Optional[Piece]) -> bool:
        return piece is not None and self.effects[color].get(key) is piece

    def _piece_skin_code(self, piece: Piece) -> Optional[str]:
        effects = self.effects[piece.color]

        if (
            piece.name == "B"
            and any(p is piece for p in effects.get("twin_bishops", []))
            and self._effect_piece_is(piece.color, "weakened_bishop_piece", piece)
        ):
            return "wtb"
        if piece.name == "B" and any(p is piece for p in effects.get("twin_bishops", [])):
            return "tb"
        if (
            piece.name == "B"
            and effects.get("bishop_awakened")
            and self._effect_piece_is(piece.color, "weakened_bishop_piece", piece)
        ):
            return "swb"
        if (
            piece.name == "R"
            and effects.get("rook_awakened")
            and self._effect_piece_is(piece.color, "weakened_rook_piece", piece)
        ):
            return "swr"
        if piece.name == "B" and effects.get("bishop_awakened"):
            return "sb"
        if piece.name == "R" and effects.get("rook_awakened"):
            return "sr"
        if piece.name == "Q" and effects.get("night_queen"):
            return "nq"
        if self._effect_piece_is(piece.color, "pawn_vs_pawn_piece", piece):
            return "sp"
        if self._effect_piece_is(piece.color, "weakened_bishop_piece", piece):
            return "wb"
        if self._effect_piece_is(piece.color, "weakened_rook_piece", piece):
            return "wr"
        if self._effect_piece_is(piece.color, "missile_bishop_piece", piece):
            return "mb"
        if self._effect_piece_is(piece.color, "colossus_piece", piece):
            return "cp"
        return None

    def guardian_piece_value(self, piece: Optional[Piece]) -> int:
        if piece is None:
            return 0
        skin = self._piece_skin_code(piece)
        if skin == "sp":
            return 2
        if skin == "wb":
            return 2
        if skin == "wr":
            return 4
        if skin == "sb":
            return 5
        if skin == "swb":
            return 4
        if skin == "sr":
            return 7
        if skin == "swr":
            return 6
        if skin == "tb":
            return 7
        if skin == "wtb":
            return 6
        if skin == "mb":
            return 5
        if skin == "cp":
            return 9
        if skin == "nq":
            return 12
        if piece.name == "P":
            return 1
        if piece.name in {"N", "B"}:
            return 3
        if piece.name == "R":
            return 5
        if piece.name == "Q":
            return 9
        return 0

    def is_minor_piece(self, piece: Optional[Piece]) -> bool:
        if piece is None:
            return False
        skin = self._piece_skin_code(piece)
        if piece.name == "N":
            return True
        return skin in {None, "wb", "sb", "swb"} and piece.name == "B"

    def guardian_linked_positions(self, piece: Optional[Piece]) -> List[Tuple[int, int]]:
        coords = self._find_piece_coords(piece)
        if coords is None:
            return []
        if piece and piece.name == "B":
            twins = self.effects[piece.color].get("twin_bishops", [])
            if any(p is piece for p in twins):
                positions = []
                for twin in twins:
                    twin_coords = self._find_piece_coords(twin)
                    if twin_coords is not None:
                        positions.append(twin_coords)
                if positions:
                    return positions
        return [coords]

    def _center_squares(self):
        return {(3, 3), (4, 3), (3, 4), (4, 4)}

    def _winner_for_removed_king(self, removed_color: str) -> str:
        return "B" if removed_color == "W" else "W"

    def _piece_on_board(self, piece: Optional[Piece]) -> bool:
        if piece is None:
            return False
        for row in self.grid:
            for cell in row:
                if cell is piece:
                    return True
        return False

    def _remove_piece_ref(self, piece: Optional[Piece]):
        if piece is None:
            return
        for y in range(8):
            for x in range(8):
                if self.grid[y][x] is piece:
                    self.grid[y][x] = None
                    return

    def _find_piece_coords(self, piece: Optional[Piece]) -> Optional[Tuple[int, int]]:
        if piece is None:
            return None
        for y in range(8):
            for x in range(8):
                if self.grid[y][x] is piece:
                    return (x, y)
        return None

    def _sync_twin_bishops(self, color: str):
        twins = self.effects[color].get("twin_bishops")
        if not twins:
            return
        alive = [piece for piece in twins if self._piece_on_board(piece)]
        if len(alive) == 1:
            self._remove_piece_ref(alive[0])
            alive = []
        if alive:
            self.effects[color]["twin_bishops"] = alive
        else:
            self.effects[color].pop("twin_bishops", None)

    def _sync_all_special_links(self):
        self._sync_twin_bishops("W")
        self._sync_twin_bishops("B")

    def _explode_missile_bishop(self, x: int, y: int, owner_color: str):
        removed_king_colors = []

        for yy in range(max(0, y - 1), min(8, y + 2)):
            for xx in range(max(0, x - 1), min(8, x + 2)):
                piece = self.grid[yy][xx]
                if piece is None or piece.name == "P":
                    continue
                if piece.name == "K":
                    removed_king_colors.append(piece.color)
                self.grid[yy][xx] = None

        if not removed_king_colors:
            return

        if len(removed_king_colors) == 1:
            self.forced_winner = self._winner_for_removed_king(removed_king_colors[0])
            self.special_win_reason = "bishop_missile"
            return

        enemy = "B" if owner_color == "W" else "W"
        if enemy in removed_king_colors:
            self.forced_winner = owner_color
        else:
            self.forced_winner = enemy
        self.special_win_reason = "bishop_missile"

    def _activate_king_infection(self, x1: int, y1: int, x2: int, y2: int, piece: Piece, target: Piece):
        def create_infected_piece() -> Piece:
            infected_piece = Piece(target.name, piece.color)
            if self._effect_piece_is(target.color, "colossus_piece", target):
                self.effects[target.color].pop("colossus_piece", None)
                colossus_wait = self.effects[target.color].pop("colossus_wait", None)
                self.effects[piece.color]["colossus_piece"] = infected_piece
                if colossus_wait is not None:
                    self.effects[piece.color]["colossus_wait"] = colossus_wait
            return infected_piece

        if target.name == "K":
            if self.effects[piece.color].get("infection"):
                self.grid[y2][x2] = create_infected_piece()
                self.last_move = (x1, y1, x1, y1)
                self.halfmove_clock = 0
                self.en_passant_target = None
                self._sync_all_special_links()
                return True
            return False

        if self.effects[piece.color].get("infection"):
            self.grid[y2][x2] = create_infected_piece()
            self.last_move = (x1, y1, x1, y1)
            self.halfmove_clock = 0
            self.en_passant_target = None
            self._sync_all_special_links()
            return True

        if self.effects[piece.color].get("weak_infection"):
            self.grid[y2][x2] = Piece("P", piece.color)
            self.last_move = (x1, y1, x1, y1)
            self.halfmove_clock = 0
            self.en_passant_target = None
            self._sync_all_special_links()
            return True

        return False

    def _check_special_win_after_move(self, moved_color: str):
        king_pos = self.find_king(moved_color)
        if king_pos and self.effects[moved_color].get("hill_king") and king_pos in self._center_squares():
            self.forced_winner = moved_color
            self.special_win_reason = "hill_king"

    def finish_turn(self, player_color: str, apply_special_check: bool = True):
        if apply_special_check:
            self._check_special_win_after_move(player_color)

        self.tick_countdown(player_color)

        if self.forced_winner is not None:
            self._record_position()
            return

        self.turn = "B" if self.turn == "W" else "W"
        if self.turn == "W":
            self.fullmove_number += 1
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
        if piece.name == "P" and self.effects[piece.color].get("no_queen_promotion") and promotion == "Q":
            promotion = "R"

        consume_pawn_slow = False

        if piece.name == "P":
            start_row = 6 if piece.color == "W" else 1
            slow_count = self.effects[piece.color].get("pawn_slow", 0)

            if y1 == start_row and slow_count > 0:
                if x1 == x2 and abs(y2 - y1) == 2:
                    return {
                        "success": False,
                        "message": "달팽이 폰: 처음 2개의 폰은 2칸 전진 불가"
                    }
                consume_pawn_slow = True

        moved_color = piece.color

        self._apply_move(x1, y1, x2, y2, promotion)

        if consume_pawn_slow:
            self.effects[piece.color]["pawn_slow"] -= 1
            if self.effects[piece.color]["pawn_slow"] <= 0:
                self.effects[piece.color].pop("pawn_slow", None)

        twin_pending = self.effects[moved_color].get("twin_bishop_extra")
        if twin_pending is not None:
            coords = self._find_piece_coords(twin_pending)
            if coords is not None and self.get_legal_moves(coords[0], coords[1]):
                return {"success": True, "extra_turn": "twin_bishop"}
            self.effects[moved_color].pop("twin_bishop_extra", None)

        self.finish_turn(moved_color, apply_special_check=True)
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

        if (
            piece.name == "K"
            and target is not None
            and target.color != piece.color
            and self._activate_king_infection(x1, y1, x2, y2, piece, target)
        ):
            return

        if is_en_passant:
            capture_y = y2 + 1 if piece.color == "W" else y2 - 1
            captured_piece = self.grid[capture_y][x2]
            self.grid[capture_y][x2] = None

        is_castling_move = (
            piece.name == "K"
            and abs(x2 - x1) == 2
            and y1 == y2
            and self._can_castle(piece.color, x1, y1, x2)
        )

        if is_castling_move:
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
        twins = self.effects[piece.color].get("twin_bishops")
        if piece.name == "B" and twins and any(p is piece for p in twins):
            if self.effects[piece.color].get("twin_bishop_extra") is piece:
                self.effects[piece.color].pop("twin_bishop_extra", None)
            else:
                others = [p for p in twins if p is not piece and self._piece_on_board(p)]
                if others:
                    self.effects[piece.color]["twin_bishop_extra"] = others[0]
                else:
                    self.effects[piece.color].pop("twin_bishop_extra", None)
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

        promotion_row = 0 if piece.color == "W" else 7
        if self.effects[piece.color].get("fast_promotion"):
            promotion_row = 2 if piece.color == "W" else 5

        if piece.name == "P" and y2 == promotion_row:
            promotion = (promotion or "Q").upper()
            if promotion not in {"Q", "R", "B", "N"}:
                promotion = "Q"
            if self.effects[piece.color].get("no_queen_promotion") and promotion == "Q":
                promotion = "R"
            self.grid[y2][x2] = Piece(promotion, piece.color)

        if (
            piece.name == "B"
            and self.effects[piece.color].get("missile_bishop_piece") is piece
            and captured_piece is not None
        ):
            self._explode_missile_bishop(x2, y2, piece.color)

        self.en_passant_target = None
        if piece.name == "P" and abs(y2 - y1) == 2:
            self.en_passant_target = (x1, (y1 + y2) // 2)

        self.last_move = (x1, y1, x2, y2)

        if piece.name == "P" or captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        self._sync_all_special_links()

    def is_valid_move(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        if not self.in_bounds(x1, y1) or not self.in_bounds(x2, y2):
            return False
        if (x1, y1) == (x2, y2):
            return False

        piece = self.grid[y1][x1]
        target = self.grid[y2][x2]
        if piece is None:
            return False
        twin_pending = self.effects[piece.color].get("twin_bishop_extra")
        if twin_pending is not None and piece is not twin_pending:
            return False
        if target and target.color == piece.color:
            return False
        if (
            target
            and target.color != piece.color
            and self.effects[target.color].get("colossus_piece") is target
            and self.effects[target.color].get("colossus_wait", 0) > 0
        ):
            return False

        dx = x2 - x1
        dy = y2 - y1
        adx = abs(dx)
        ady = abs(dy)

        if piece.name == "P":
            direction = -1 if piece.color == "W" else 1
            start_row = 6 if piece.color == "W" else 1
            enemy = "B" if piece.color == "W" else "W"
            immune_enemy_pawn = (
                target is not None
                and target.name == "P"
                and self.effects[enemy].get("pawn_vs_pawn_piece") is target
            )

            if dx == 0 and dy == direction and target is None:
                return True
            if dx == 0 and dy == direction and target is not None and target.color != piece.color:
                if self.effects[piece.color].get("forward_attack"):
                    return True
                return False
            if self.effects[piece.color].get("pawn_retreat"):
                if dx == 0 and dy == -direction and target is None:
                    return True

            if (
                dx == 0
                and dy == 2 * direction
                and target is None
                and self.grid[y1 + direction][x1] is None
            ):
                slow_count = self.effects[piece.color].get("pawn_slow", 0)
                if y1 == start_row and slow_count > 0:
                    return False
                if self.effects[piece.color].get("fast_pawn"):
                    return True
                if y1 == start_row:
                    return True

            if adx == 1 and dy == direction:
                if target is not None and target.color != piece.color:
                    if immune_enemy_pawn:
                        return False
                    return True
                if target is None and self.en_passant_target == (x2, y2):
                    adjacent = self.grid[y1][x2]
                    return adjacent is not None and adjacent.name == "P" and adjacent.color != piece.color
            return False

        if piece.name == "N":
            return (adx, ady) in [(1, 2), (2, 1)]

        if piece.name == "B":
            if self.effects[piece.color].get("bishop_awakened") and max(adx, ady) == 1:
                return True
            if self.effects[piece.color].get("weakened_bishop_piece") is piece:
                return adx == ady and 0 < adx <= 2 and self._clear(x1, y1, x2, y2)
            return adx == ady and self._clear(x1, y1, x2, y2)

        if piece.name == "R":
            if self.effects[piece.color].get("rook_awakened") and max(adx, ady) == 1:
                return True
            if self.effects[piece.color].get("weakened_rook_piece") is piece:
                return (x1 == x2 or y1 == y2) and max(adx, ady) <= 3 and self._clear(x1, y1, x2, y2)
            return (x1 == x2 or y1 == y2) and self._clear(x1, y1, x2, y2)

        if piece.name == "Q":
            if self.effects[piece.color].get("sealed_queen"):
                return False
            if self.effects[piece.color].get("colossus_piece") is piece and self.effects[piece.color].get("colossus_wait", 0) > 0:
                return False
            if self.effects[piece.color].get("night_queen") and (adx, ady) in [(1, 2), (2, 1)]:
                return True
            return (adx == ady or x1 == x2 or y1 == y2) and self._clear(x1, y1, x2, y2)

        if piece.name == "K":
            # 기본 1칸 이동
            if adx <= 1 and ady <= 1:
                return True

            # 가로 2칸 / 세로 2칸은 왕권 강화 이동 후보
            if self.effects[piece.color].get("king_buff"):
                if (adx == 2 and ady == 0) or (adx == 0 and ady == 2):
                    mid_x = x1 + (dx // 2)
                    mid_y = y1 + (dy // 2)

                    if self.grid[mid_y][mid_x] is not None:
                        return False

                    return True

            # 왕권 강화가 없을 때만 캐슬링 허용
            if ady == 0 and adx == 2:
                return self._can_castle(piece.color, x1, y1, x2)

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

                promotion_row = 0 if piece.color == "W" else 7
                if self.effects[piece.color].get("fast_promotion"):
                    promotion_row = 2 if piece.color == "W" else 5

                if piece.name == "P" and yy == promotion_row:
                    legal_promotion_found = False
                    for promo in ("Q", "R", "B", "N"):
                        temp = deepcopy(self)
                        temp._apply_move(x, y, xx, yy, promo)
                        if self._ignore_check_rules(piece.color) or not temp.is_in_check(piece.color):
                            legal_promotion_found = True
                            break
                    if legal_promotion_found:
                        moves.append((xx, yy))
                else:
                    temp = deepcopy(self)
                    temp._apply_move(x, y, xx, yy)
                    if self._ignore_check_rules(piece.color) or not temp.is_in_check(piece.color):
                        moves.append((xx, yy))

        return moves
    def find_kings(self, color: str):
        kings = []
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p is not None and p.name == "K" and p.color == color:
                    kings.append((x, y))
        return kings

    def find_king(self, color: str):
        kings = self.find_kings(color)
        if kings:
            return kings[0]
        return None

    def _ignore_check_rules(self, color: str) -> bool:
        return bool(self.effects[color].get("king_copy_active")) and len(self.find_kings(color)) >= 2

    def attacked_king_positions(self, color: str):
        king_positions = self.find_kings(color)
        if not king_positions:
            return []

        attacked = []
        enemy = "B" if color == "W" else "W"
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p is None or p.color != enemy:
                    continue
                if p.name == "P":
                    direction = -1 if p.color == "W" else 1
                    pawn_attacks = {(x - 1, y + direction), (x + 1, y + direction)}
                    for pos in king_positions:
                        if pos in pawn_attacks and pos not in attacked:
                            attacked.append(pos)
                    continue
                if p.name == "K":
                    for kx, ky in king_positions:
                        if max(abs(kx - x), abs(ky - y)) == 1 and (kx, ky) not in attacked:
                            attacked.append((kx, ky))
                    continue
                for kx, ky in king_positions:
                    if self.is_valid_move(x, y, kx, ky) and (kx, ky) not in attacked:
                        attacked.append((kx, ky))
        return attacked
    
    def is_in_check(self, color: str) -> bool:
        if self._ignore_check_rules(color):
            return False
        return bool(self.attacked_king_positions(color))

    def _has_any_legal_move(self, color: str) -> bool:
        for y in range(8):
            for x in range(8):
                p = self.grid[y][x]
                if p and p.color == color and self.get_legal_moves(x, y):
                    return True
        return False

    def _has_multi_king_state(self) -> bool:
        return len(self.find_kings("W")) > 1 or len(self.find_kings("B")) > 1

    def _insufficient_material(self) -> bool:
        if self._has_multi_king_state():
            return False
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

    def _anti_draw_winner(self) -> Optional[str]:
        white = bool(self.effects["W"].get("anti_draw_win"))
        black = bool(self.effects["B"].get("anti_draw_win"))
        if white == black:
            return None
        return "W" if white else "B"

    def get_game_state(self):
        self._sync_all_special_links()
        white_kings = self.find_kings("W")
        black_kings = self.find_kings("B")
        if not white_kings and black_kings:
            return {
                "check": False,
                "checkmate": False,
                "draw": False,
                "draw_reason": None,
                "winner": "B",
                "special_win": "king_capture",
            }
        if not black_kings and white_kings:
            return {
                "check": False,
                "checkmate": False,
                "draw": False,
                "draw_reason": None,
                "winner": "W",
                "special_win": "king_capture",
            }
        if self.forced_winner is not None:
            return {
                "check": False,
                "checkmate": False,
                "draw": False,
                "draw_reason": None,
                "winner": self.forced_winner,
                "special_win": self.special_win_reason,
            }
        check = self.is_in_check(self.turn)
        moves_exist = self._has_any_legal_move(self.turn)

        result = {
            "check": check,
            "checkmate": False,
            "draw": False,
            "draw_reason": None,
            "winner": None,
            "special_win": None,
            "attacked_kings": {
                "W": self.attacked_king_positions("W"),
                "B": self.attacked_king_positions("B"),
            },
        }

        if check and not moves_exist:
            if self.effects[self.turn].get("king_copy_active"):
                return result
            result["checkmate"] = True
            result["winner"] = "B" if self.turn == "W" else "W"
            return result

        if not check and not moves_exist:
            anti_draw_winner = self._anti_draw_winner()
            if anti_draw_winner is not None:
                result["winner"] = anti_draw_winner
                result["special_win"] = "no_draw_win"
            else:
                result["draw"] = True
                result["draw_reason"] = "stalemate"
            return result

        if self.halfmove_clock >= 100:
            anti_draw_winner = self._anti_draw_winner()
            if anti_draw_winner is not None:
                result["winner"] = anti_draw_winner
                result["special_win"] = "no_draw_win"
            else:
                result["draw"] = True
                result["draw_reason"] = "fifty_move"
            return result

        current_key = self._position_key()
        if self.position_history.get(current_key, 0) >= 3:
            anti_draw_winner = self._anti_draw_winner()
            if anti_draw_winner is not None:
                result["winner"] = anti_draw_winner
                result["special_win"] = "no_draw_win"
            else:
                result["draw"] = True
                result["draw_reason"] = "threefold_repetition"
            return result

        if self._insufficient_material():
            anti_draw_winner = self._anti_draw_winner()
            if anti_draw_winner is not None:
                result["winner"] = anti_draw_winner
                result["special_win"] = "no_draw_win"
            else:
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
                    (
                        {
                            "name": p.name,
                            "color": p.color,
                            **({"skin": self._piece_skin_code(p)} if self._piece_skin_code(p) else {}),
                        }
                        if p
                        else None
                    )
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
        
    def tick_countdown(self, player):
        countdown = self.effects[player].get("countdown")
        if countdown is not None:
            countdown -= 1
            self.effects[player]["countdown"] = countdown

            if countdown <= 0:
                self.forced_winner = player
                self.special_win_reason = "countdown"

        colossus_wait = self.effects[player].get("colossus_wait")
        if colossus_wait is not None:
            colossus_wait -= 1
            if colossus_wait <= 0:
                for y in range(8):
                    for x in range(8):
                        piece = self.grid[y][x]
                        if piece and piece.color == player and piece.name == "P":
                            self.grid[y][x] = None
                self.effects[player].pop("colossus_wait", None)
            else:
                self.effects[player]["colossus_wait"] = colossus_wait
