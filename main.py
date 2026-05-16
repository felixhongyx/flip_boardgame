import pygame
import sys
import asyncio
from typing import List, Tuple, Optional
from board import GRID_SIZE, Board, FlipRule, ChainFlipHandler
from ai_player import AIPlayer

# 常量定义 - 适配手机
CELL_SIZE = 50
MARGIN = 30
WINDOW_WIDTH = MARGIN * 2 + CELL_SIZE * (GRID_SIZE - 1)
WINDOW_HEIGHT = MARGIN * 2 + CELL_SIZE * (GRID_SIZE - 1) + 80

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PLAYER1_COLOR = (220, 50, 50)  # 红色
PLAYER2_COLOR = (50, 50, 220)  # 蓝色
BOARD_COLOR = (245, 222, 179)
HIGHLIGHT_COLOR = (255, 255, 0)
SELECTED_COLOR = (0, 255, 0)
BUTTON_COLOR = (100, 200, 100)
BUTTON_HOVER = (120, 220, 120)


class GameLogger:
    """简化版日志 - 只输出到控制台"""

    def __init__(self):
        self.turn_count = 0
        print(f"=== 游戏开始 ===")

    def log(self, message: str):
        print(message)

    def log_turn_start(self, player: int):
        self.turn_count += 1
        self.log(f"--- 回合 {self.turn_count} - 玩家{player} ---")

    def log_move(self, player: int, from_pos: Tuple[int, int], to_pos: Tuple[int, int]):
        self.log(f"玩家{player} 走棋: {from_pos} -> {to_pos}")

    def log_flip(self, player: int, flipped_pos: Tuple[int, int], reason: str):
        self.log(f"玩家{player} 翻转 {flipped_pos}")

    def log_chain_flip_start(self):
        self.log("--- 连锁翻转阶段 ---")

    def log_chain_flip_choice(self, player: int, choice: str):
        self.log(f"玩家{player} 选择连锁翻转: {choice}")

    def log_game_over(self, winner: int):
        self.log(f"\n=== 游戏结束 - 玩家{winner}获胜! ===")

    def log_board_state(self, board: List[List[int]]):
        pass  # 网页版不输出棋盘状态


class Game:
    """游戏主逻辑"""

    SELECTING = "selecting"
    MOVING = "moving"
    FLIPPING = "flipping"
    CHAIN_FLIPPING = "chain_flipping"
    GAME_OVER = "game_over"
    MODE_SELECT = "mode_select"
    RULE_INTRO = "rule_intro"
    ANIMATING = "animating"

    def __init__(self, logger: GameLogger):
        self.logger = logger
        self.board = Board()
        self.flip_rule = FlipRule(self.board)
        self.chain_handler = ChainFlipHandler(self.board, self.flip_rule)

        self.current_player = 1
        self.state = Game.MODE_SELECT
        self.selected_pos = None
        self.pending_flips = []
        self.pending_flip_groups = []
        self.selected_flip_group = None

        self.game_mode = None
        self.ai_player = None

        self.after_anim_state = None
        self.after_anim_data = None

    def set_mode(self, mode: str):
        self.game_mode = mode
        if mode == 'pve':
            self.ai_player = AIPlayer(2, depth=2)
        self.state = Game.SELECTING
        self.logger.log_turn_start(1)

    def select_piece(self, pos: Tuple[int, int]) -> bool:
        if self.state != Game.SELECTING:
            return False
        if self.board.get_piece(pos) != self.current_player:
            return False

        self.selected_pos = pos
        self.state = Game.MOVING
        self.logger.log(f"玩家{self.current_player} 选择 {pos}")
        return True

    def move_to(self, pos: Tuple[int, int]) -> bool:
        if self.state != Game.MOVING:
            return False
        if pos not in self.board.get_valid_moves(self.current_player, self.selected_pos):
            return False

        from_pos = self.selected_pos
        self.after_anim_data = {
            "type": "move",
            "from": from_pos,
            "to": pos
        }
        self.after_anim_state = Game.FLIPPING
        self.state = Game.ANIMATING
        return True

    def do_real_move(self, from_pos, to_pos):
        self.board.move_piece(from_pos, to_pos)
        self.logger.log_move(self.current_player, from_pos, to_pos)

        self.pending_flip_groups = self.flip_rule.get_flip_groups_after_move(self.current_player, to_pos)
        self.pending_flips = self.flip_rule.get_flips_after_move(self.current_player, to_pos)
        self.selected_flip_group = None
        self.selected_pos = to_pos

        if self.pending_flip_groups:
            self.state = Game.FLIPPING
        else:
            self._end_turn()

    def ai_move(self):
        if self.game_mode != 'pve' or self.current_player != 2:
            return
        if self.ai_player is None:
            return
        if self.state != Game.SELECTING:
            return

        from_pos, to_pos = self.ai_player.choose_move(self.board)
        if from_pos is None or to_pos is None:
            return
        self.select_piece(from_pos)
        self.move_to(to_pos)

    def ai_flip(self):
        if self.state != Game.FLIPPING or not self.pending_flip_groups:
            return

        group_idx = self.ai_player.choose_flip_group(self.pending_flip_groups)
        self.selected_flip_group = group_idx
        self.apply_flips()

    def ai_chain(self):
        if self.state != Game.CHAIN_FLIPPING:
            return

        if self.chain_handler.selected_trigger is None:
            triggers = self.chain_handler.get_triggers()
            if not triggers:
                self.chain_skip()
                return
            self.chain_handler.select_trigger(triggers[0])
            return

        if self.chain_handler.selected_group is None:
            groups = self.chain_handler.get_available_groups()
            if not groups:
                self.chain_handler.selected_trigger = None
                return
            group_idx = self.ai_player.choose_flip_group(groups)
            self.chain_handler.selected_group = group_idx
            self.chain_handler.preview_flips = [p for p, _ in groups[group_idx]['flips']]
            return

        self.chain_apply()

    def select_flip_group(self, pos: Tuple[int, int]):
        if self.state != Game.FLIPPING:
            return
        for i, group in enumerate(self.pending_flip_groups):
            for p, _ in group["flips"]:
                if p == pos:
                    self.selected_flip_group = i
                    return

    def apply_flips(self):
        if self.state != Game.FLIPPING:
            return
        if self.selected_flip_group is None:
            return

        group = self.pending_flip_groups[self.selected_flip_group]
        flip_list = [(pos, self.current_player) for pos, reason in group["flips"]]
        reasons = [reason for pos, reason in group["flips"]]
        self.after_anim_data = {
            "type": "flip",
            "flips": flip_list,
            "reasons": reasons
        }
        self.after_anim_state = Game.CHAIN_FLIPPING
        self.state = Game.ANIMATING

    def do_real_flip(self, flip_list, reasons):
        for i, (pos, player) in enumerate(flip_list):
            self.board.set_piece(pos, player)
            self.logger.log_flip(player, pos, reasons[i])

        self.pending_flips = []
        self.pending_flip_groups = []
        self.selected_flip_group = None

        if self.chain_handler.start_chain_flip(self.current_player):
            self.state = Game.CHAIN_FLIPPING
            self.logger.log_chain_flip_start()
        else:
            self._end_turn()

    def skip_flips(self):
        if self.state != Game.FLIPPING:
            return
        self.logger.log(f"玩家{self.current_player} 跳过翻转")
        self.pending_flips = []
        self.pending_flip_groups = []
        self.selected_flip_group = None
        self._end_turn()

    def chain_select(self, pos: Tuple[int, int]):
        if self.state != Game.CHAIN_FLIPPING:
            return
        if self.chain_handler.selected_trigger is not None:
            self.chain_handler.select_group(pos)
        if self.chain_handler.selected_trigger is None or pos in self.chain_handler.get_triggers():
            self.chain_handler.select_trigger(pos)

    def chain_apply(self):
        if self.state != Game.CHAIN_FLIPPING:
            return
        if self.chain_handler.selected_trigger is None or self.chain_handler.selected_group is None:
            return

        groups = self.chain_handler.available_groups
        group = groups[self.chain_handler.selected_group]
        flip_list = [(pos, self.current_player) for pos, reason in group["flips"]]
        reasons = [reason for pos, reason in group["flips"]]
        del groups[self.chain_handler.selected_group]

        self.after_anim_data = {
            "type": "chain_flip",
            "flips": flip_list,
            "reasons": reasons
        }
        self.after_anim_state = Game.CHAIN_FLIPPING
        self.state = Game.ANIMATING

    def do_real_chain_flip(self, flip_list, reasons):
        for i, (pos, player) in enumerate(flip_list):
            self.board.set_piece(pos, player)
            self.logger.log_flip(player, pos, reasons[i])

        # 让ChainFlipHandler正确处理后续状态
        # 重新获取该触发点的剩余分组
        remaining_groups = self.flip_rule.get_flip_groups_for_trigger(self.current_player, self.chain_handler.selected_trigger)
        if remaining_groups:
            # 还有其他分组可选，保持在当前触发点
            self.chain_handler.available_groups = remaining_groups
            self.chain_handler.selected_group = None
            self.chain_handler.preview_flips = [p for p, _ in remaining_groups[0]['flips']]
            self.state = Game.CHAIN_FLIPPING
        else:
            # 当前触发点已无分组，检查是否有其他触发点
            self.chain_handler.selected_trigger = None
            self.chain_handler.available_groups = []
            self.chain_handler.selected_group = None
            self.chain_handler.preview_flips = []
            self.chain_handler.available_triggers = self.flip_rule.get_triggers(self.current_player)
            if self.chain_handler.available_triggers:
                self.state = Game.CHAIN_FLIPPING
            else:
                self._end_turn()

    def chain_skip(self):
        if self.state != Game.CHAIN_FLIPPING:
            return
        self.logger.log_chain_flip_choice(self.current_player, "跳过")
        self._end_turn()

    def cancel_selection(self):
        if self.state == Game.MOVING:
            self.state = Game.SELECTING
            self.selected_pos = None

    def _end_turn(self):
        p1_count = self.board.count_pieces(1)
        p2_count = self.board.count_pieces(2)

        if p1_count == 0:
            self.state = Game.GAME_OVER
            self.logger.log_game_over(2)
            return
        if p2_count == 0:
            self.state = Game.GAME_OVER
            self.logger.log_game_over(1)
            return

        self.current_player = 3 - self.current_player
        if not self.board.has_any_move(self.current_player):
            winner = 3 - self.current_player
            self.state = Game.GAME_OVER
            self.logger.log(f"玩家{self.current_player}无子可走！玩家{winner}获胜！")
            self.logger.log_game_over(winner)
            return
        self.state = Game.SELECTING
        self.selected_pos = None
        self.logger.log_turn_start(self.current_player)

    def restart(self):
        self.__init__(self.logger)


class GUI:
    """pygame界面 - 网页版"""

    def __init__(self, game: Game, logger: GameLogger):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("翻转棋")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("simhei", 16)
        self.small_font = pygame.font.SysFont("simhei", 12)
        self.large_font = pygame.font.SysFont("simhei", 24)

        self.game = game
        self.logger = logger

        self.ai_action_timer = 0
        self.ai_action_delay = 600

        self.rule_page = 0
        self.rule_anim_timer = 0

        self.anim_timer = 0
        self.anim_duration = 300
        self.anim_type = None
        self.anim_move_from = None
        self.anim_move_to = None
        self.anim_flips = []
        self.anim_saved_piece = None

    def pos_to_screen(self, pos):
        return (MARGIN + pos[0] * CELL_SIZE, MARGIN + pos[1] * CELL_SIZE)

    def screen_to_pos(self, screen_pos):
        sx, sy = screen_pos
        x = round((sx - MARGIN) / CELL_SIZE)
        y = round((sy - MARGIN) / CELL_SIZE)
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            dx = abs(sx - (MARGIN + x * CELL_SIZE))
            dy = abs(sy - (MARGIN + y * CELL_SIZE))
            if dx < 20 and dy < 20:
                return (x, y)
        return None

    def draw_button(self, rect, text, hover):
        color = BUTTON_HOVER if hover else BUTTON_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        txt = self.font.render(text, True, BLACK)
        self.screen.blit(txt, (rect.centerx - txt.get_width() // 2,
                                rect.centery - txt.get_height() // 2))

    def draw_mode_select(self):
        self.screen.fill(BOARD_COLOR)

        title = self.large_font.render("翻转棋", True, BLACK)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 50))

        mouse_pos = pygame.mouse.get_pos()

        pvp_rect = pygame.Rect(WINDOW_WIDTH // 2 - 120, 130, 240, 50)
        self.draw_button(pvp_rect, "双人对战", pvp_rect.collidepoint(mouse_pos))
        self.pvp_btn = pvp_rect

        pve_rect = pygame.Rect(WINDOW_WIDTH // 2 - 120, 200, 240, 50)
        self.draw_button(pve_rect, "人机对战", pve_rect.collidepoint(mouse_pos))
        self.pve_btn = pve_rect

        rule_rect = pygame.Rect(WINDOW_WIDTH // 2 - 120, 270, 240, 50)
        self.draw_button(rule_rect, "规则介绍", rule_rect.collidepoint(mouse_pos))
        self.rule_btn = rule_rect

    def draw_rule_intro(self, dt):
        self.screen.fill(BOARD_COLOR)
        self.rule_anim_timer += dt

        title = self.large_font.render("游戏规则", True, BLACK)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))

        mouse_pos = pygame.mouse.get_pos()
        if self.rule_page < 4:
            next_btn = pygame.Rect(WINDOW_WIDTH - 140, WINDOW_HEIGHT - 60, 120, 40)
            self.draw_button(next_btn, "下一步", next_btn.collidepoint(mouse_pos))
            self.next_btn = next_btn
        else:
            back_btn = pygame.Rect(WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT - 60, 120, 40)
            self.draw_button(back_btn, "返回", back_btn.collidepoint(mouse_pos))
            self.back_to_mode_btn = back_btn

        if self.rule_page > 0:
            prev_btn = pygame.Rect(20, WINDOW_HEIGHT - 60, 120, 40)
            self.draw_button(prev_btn, "上一步", prev_btn.collidepoint(mouse_pos))
            self.prev_btn = prev_btn

        if self.rule_page == 0:
            self.draw_rule_page1()
        elif self.rule_page == 1:
            self.draw_rule_page2(dt)
        elif self.rule_page == 2:
            self.draw_rule_page3(dt)
        elif self.rule_page == 3:
            self.draw_rule_page4(dt)
        else:
            self.draw_rule_page5()

        total_pages = 5
        page_text = self.small_font.render(f"{self.rule_page + 1}/{total_pages}", True, BLACK)
        self.screen.blit(page_text, (WINDOW_WIDTH // 2 - 15, WINDOW_HEIGHT - 90))

    def draw_rule_page1(self):
        desc = [
            "7x7交叉点，双方各14子",
            "红方先手，轮流走棋",
            "棋子沿横竖或斜线走一格",
            "中间两行是X形，方向不限！"
        ]
        y = 70
        for line in desc:
            txt = self.font.render(line, True, BLACK)
            self.screen.blit(txt, (40, y))
            y += 30

    def draw_rule_page2(self, dt):
        desc = [
            "规则A：己-敌-己",
            "走棋后，形成这样的排列",
            "就可以把中间的敌人翻转！"
        ]
        y = 70
        for line in desc:
            txt = self.font.render(line, True, BLACK)
            self.screen.blit(txt, (40, y))
            y += 30

    def draw_rule_page3(self, dt):
        desc = [
            "规则B：敌-己-敌",
            "走棋后，形成这样的排列",
            "两个敌人都可以翻转！"
        ]
        y = 70
        for line in desc:
            txt = self.font.render(line, True, BLACK)
            self.screen.blit(txt, (40, y))
            y += 30

    def draw_rule_page4(self, dt):
        desc = [
            "规则C：连锁翻转",
            "一次翻转后，又满足新规则",
            "可以选择继续或跳过"
        ]
        y = 70
        for line in desc:
            txt = self.font.render(line, True, BLACK)
            self.screen.blit(txt, (40, y))
            y += 30

    def draw_rule_page5(self):
        desc = [
            "胜利条件：",
            "1. 对方棋子归零",
            "2. 对方无法走棋"
        ]
        y = 90
        for line in desc:
            txt = self.font.render(line, True, BLACK)
            self.screen.blit(txt, (WINDOW_WIDTH // 2 - txt.get_width() // 2, y))
            y += 35

    def draw_board(self):
        self.screen.fill(BOARD_COLOR)

        for gy in range(GRID_SIZE):
            s, e = self.pos_to_screen((0, gy)), self.pos_to_screen((GRID_SIZE - 1, gy))
            pygame.draw.line(self.screen, BLACK, s, e, 2)
        for gx in range(GRID_SIZE):
            s, e = self.pos_to_screen((gx, 0)), self.pos_to_screen((gx, GRID_SIZE - 1))
            pygame.draw.line(self.screen, BLACK, s, e, 2)

        for gy in range(GRID_SIZE - 1):
            for gx in range(GRID_SIZE - 1):
                if gy == 2 or gy == 3:
                    s = self.pos_to_screen((gx, gy))
                    e = self.pos_to_screen((gx + 1, gy + 1))
                    pygame.draw.line(self.screen, BLACK, s, e, 1)
                    s = self.pos_to_screen((gx + 1, gy))
                    e = self.pos_to_screen((gx, gy + 1))
                    pygame.draw.line(self.screen, BLACK, s, e, 1)
                else:
                    if gy % 2 == 1:
                        s = self.pos_to_screen((gx, gy))
                        e = self.pos_to_screen((gx + 1, gy + 1))
                    else:
                        s = self.pos_to_screen((gx + 1, gy))
                        e = self.pos_to_screen((gx, gy + 1))
                    pygame.draw.line(self.screen, BLACK, s, e, 1)

    def draw_pieces(self, skip_pos=None):
        for gy in range(GRID_SIZE):
            for gx in range(GRID_SIZE):
                if skip_pos and (gx, gy) == skip_pos:
                    continue
                p = self.game.board.get_piece((gx, gy))
                if p != 0:
                    color = PLAYER1_COLOR if p == 1 else PLAYER2_COLOR
                    c = self.pos_to_screen((gx, gy))
                    pygame.draw.circle(self.screen, color, c, 16)
                    pygame.draw.circle(self.screen, BLACK, c, 16, 2)

    def draw_moving_animation(self):
        t = self.anim_timer / self.anim_duration
        from_x, from_y = self.anim_move_from
        to_x, to_y = self.anim_move_to
        curr_x = from_x + (to_x - from_x) * t
        curr_y = from_y + (to_y - from_y) * t
        center = (MARGIN + curr_x * CELL_SIZE, MARGIN + curr_y * CELL_SIZE)
        color = PLAYER1_COLOR if self.game.board.get_piece((to_x, to_y)) != 0 else (
            PLAYER1_COLOR if self.game.current_player == 1 else PLAYER2_COLOR
        )
        if self.anim_saved_piece is not None:
            color = PLAYER1_COLOR if self.anim_saved_piece == 1 else PLAYER2_COLOR
        pygame.draw.circle(self.screen, color, center, 16)
        pygame.draw.circle(self.screen, BLACK, center, 16, 2)

    def draw_flipping_animation(self):
        t = self.anim_timer / self.anim_duration
        for (gx, gy), old_c, new_c in self.anim_flips:
            center = self.pos_to_screen((gx, gy))
            scale = 1.0 - abs(0.5 - t) * 0.6
            r = int(old_c[0] + (new_c[0] - old_c[0]) * t)
            g = int(old_c[1] + (new_c[1] - old_c[1]) * t)
            b = int(old_c[2] + (new_c[2] - old_c[2]) * t)
            col = (r, g, b)
            rad = int(16 * scale)
            pygame.draw.circle(self.screen, col, center, rad)
            pygame.draw.circle(self.screen, BLACK, center, rad, 2)

    def draw_highlight(self):
        if self.game.state == Game.ANIMATING:
            return

        if self.game.selected_pos:
            c = self.pos_to_screen(self.game.selected_pos)
            pygame.draw.circle(self.screen, SELECTED_COLOR, c, 22, 4)

        if self.game.state == Game.MOVING:
            for pos in self.game.board.get_valid_moves(self.game.current_player, self.game.selected_pos):
                c = self.pos_to_screen(pos)
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, c, 10, 3)

        if self.game.state == Game.FLIPPING:
            colors = [(0, 200, 255), (255, 0, 255), (0, 255, 128), (255, 128, 0)]
            for i, group in enumerate(self.game.pending_flip_groups):
                col = colors[i % len(colors)]
                w = 6 if self.game.selected_flip_group == i else 3
                for pos, _ in group["flips"]:
                    c = self.pos_to_screen(pos)
                    pygame.draw.circle(self.screen, col, c, 22, w)

        if self.game.state == Game.CHAIN_FLIPPING:
            triggers = self.game.chain_handler.get_triggers()
            sel_trig = self.game.chain_handler.selected_trigger
            groups = self.game.chain_handler.get_available_groups()
            sel_idx = self.game.chain_handler.get_selected_group()

            for pos in triggers:
                c = self.pos_to_screen(pos)
                pygame.draw.circle(self.screen, (255, 255, 255), c, 26)
                col = PLAYER1_COLOR if self.game.current_player == 1 else PLAYER2_COLOR
                pygame.draw.circle(self.screen, col, c, 16)
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, c, 26, 6)

            if sel_trig is not None and groups:
                colors = [(0, 200, 255), (255, 0, 255), (0, 255, 128), (255, 128, 0)]
                for i, group in enumerate(groups):
                    col = colors[i % len(colors)]
                    w = 6 if sel_idx == i else 3
                    for pos, _ in group["flips"]:
                        c = self.pos_to_screen(pos)
                        pygame.draw.circle(self.screen, col, c, 22, w)
            else:
                preview = self.game.chain_handler.get_preview_flips()
                for pos in preview:
                    c = self.pos_to_screen(pos)
                    pygame.draw.circle(self.screen, SELECTED_COLOR, c, 22, 5)

    def draw_ui(self):
        y = MARGIN + CELL_SIZE * (GRID_SIZE - 1) + 15

        if self.game.state == Game.ANIMATING:
            msg = "..."
            txt_color = BLACK
        elif self.game.state == Game.GAME_OVER:
            winner = 2 if self.game.board.count_pieces(1) == 0 else 1
            msg = f"玩家{winner}获胜！点此重来"
            txt_color = BLACK
        else:
            col = PLAYER1_COLOR if self.game.current_player == 1 else PLAYER2_COLOR
            p_name = f"玩家{self.game.current_player}"
            if self.game.game_mode == 'pve' and self.game.current_player == 2:
                p_name = "AI"

            if self.game.state == Game.SELECTING:
                msg = f"{p_name} - 选棋子"
            elif self.game.state == Game.MOVING:
                msg = f"{p_name} - 走棋"
            elif self.game.state == Game.FLIPPING:
                msg = f"{p_name} - 选翻转组"
            elif self.game.state == Game.CHAIN_FLIPPING:
                msg = f"{p_name} - 连锁翻转"
            else:
                msg = ""
            txt_color = col

        txt = self.font.render(msg, True, txt_color)
        self.screen.blit(txt, (10, y))

        p1_count = self.game.board.count_pieces(1)
        p2_count = self.game.board.count_pieces(2)
        stat_txt = f"红:{p1_count} 蓝:{p2_count}"
        stat = self.font.render(stat_txt, True, BLACK)
        self.screen.blit(stat, (WINDOW_WIDTH - 120, y))

        if self.game.state == Game.FLIPPING:
            self.draw_flip_buttons()
        elif self.game.state == Game.CHAIN_FLIPPING:
            self.draw_chain_buttons()

    def draw_flip_buttons(self):
        y = WINDOW_HEIGHT - 50
        m_pos = pygame.mouse.get_pos()
        btn_conf = pygame.Rect(WINDOW_WIDTH - 180, y, 80, 35)
        self.draw_button(btn_conf, "确认", btn_conf.collidepoint(m_pos))
        self.btn_flip_confirm = btn_conf

        btn_skip = pygame.Rect(WINDOW_WIDTH - 90, y, 80, 35)
        col = (220, 100, 100)
        if btn_skip.collidepoint(m_pos):
            col = (240, 120, 120)
        pygame.draw.rect(self.screen, col, btn_skip, border_radius=8)
        txt = self.font.render("跳过", True, BLACK)
        self.screen.blit(txt, (btn_skip.centerx - txt.get_width() // 2,
                                btn_skip.centery - txt.get_height() // 2))
        self.btn_flip_skip = btn_skip

    def draw_chain_buttons(self):
        y = WINDOW_HEIGHT - 50
        m_pos = pygame.mouse.get_pos()
        btn_conf = pygame.Rect(WINDOW_WIDTH - 180, y, 80, 35)
        self.draw_button(btn_conf, "确认", btn_conf.collidepoint(m_pos))
        self.btn_chain_confirm = btn_conf

        btn_skip = pygame.Rect(WINDOW_WIDTH - 90, y, 80, 35)
        col = (220, 100, 100)
        if btn_skip.collidepoint(m_pos):
            col = (240, 120, 120)
        pygame.draw.rect(self.screen, col, btn_skip, border_radius=8)
        txt = self.font.render("跳过", True, BLACK)
        self.screen.blit(txt, (btn_skip.centerx - txt.get_width() // 2,
                                btn_skip.centery - txt.get_height() // 2))
        self.btn_chain_skip = btn_skip

    def handle_click(self, pos):
        if self.game.state == Game.ANIMATING:
            return

        if self.game.state == Game.RULE_INTRO:
            if hasattr(self, 'next_btn') and self.next_btn.collidepoint(pos):
                self.rule_page += 1
            elif hasattr(self, 'prev_btn') and self.prev_btn.collidepoint(pos):
                self.rule_page -= 1
            elif hasattr(self, 'back_to_mode_btn') and self.back_to_mode_btn.collidepoint(pos):
                self.game.state = Game.MODE_SELECT
                self.rule_page = 0
            return

        if self.game.state == Game.MODE_SELECT:
            if hasattr(self, 'pvp_btn') and self.pvp_btn.collidepoint(pos):
                self.game.set_mode('pvp')
            elif hasattr(self, 'pve_btn') and self.pve_btn.collidepoint(pos):
                self.game.set_mode('pve')
            elif hasattr(self, 'rule_btn') and self.rule_btn.collidepoint(pos):
                self.game.state = Game.RULE_INTRO
            return

        if self.game.state == Game.GAME_OVER:
            self.game.restart()
            return

        if self.game.state == Game.FLIPPING:
            if hasattr(self, 'btn_flip_confirm') and self.btn_flip_confirm.collidepoint(pos):
                self.game.apply_flips()
                return
            if hasattr(self, 'btn_flip_skip') and self.btn_flip_skip.collidepoint(pos):
                self.game.skip_flips()
                return

        if self.game.state == Game.CHAIN_FLIPPING:
            if hasattr(self, 'btn_chain_confirm') and self.btn_chain_confirm.collidepoint(pos):
                self.game.chain_apply()
                return
            if hasattr(self, 'btn_chain_skip') and self.btn_chain_skip.collidepoint(pos):
                self.game.chain_skip()
                return

        b_pos = self.screen_to_pos(pos)
        if not b_pos:
            return

        if self.game.state == Game.SELECTING:
            self.game.select_piece(b_pos)
        elif self.game.state == Game.MOVING:
            if not self.game.move_to(b_pos):
                self.game.select_piece(b_pos)
        elif self.game.state == Game.FLIPPING:
            self.game.select_flip_group(b_pos)
        elif self.game.state == Game.CHAIN_FLIPPING:
            self.game.chain_select(b_pos)

    def handle_right_click(self):
        self.game.cancel_selection()

    def start_animation(self):
        data = self.game.after_anim_data
        self.anim_timer = 0
        if data["type"] == "move":
            self.anim_type = "move"
            self.anim_move_from = data["from"]
            self.anim_move_to = data["to"]
            self.anim_saved_piece = self.game.board.get_piece(data["from"])
        elif data["type"] in ("flip", "chain_flip"):
            self.anim_type = "flip"
            self.anim_flips = []
            for pos, new_player in data["flips"]:
                old_p = self.game.board.get_piece(pos)
                old_c = PLAYER1_COLOR if old_p == 1 else PLAYER2_COLOR
                new_c = PLAYER1_COLOR if new_player == 1 else PLAYER2_COLOR
                self.anim_flips.append((pos, old_c, new_c))

    def update_animation(self, dt):
        self.anim_timer += dt
        if self.anim_timer >= self.anim_duration:
            data = self.game.after_anim_data
            if data["type"] == "move":
                self.game.do_real_move(data["from"], data["to"])
            elif data["type"] == "flip":
                self.game.do_real_flip(data["flips"], data["reasons"])
            elif data["type"] == "chain_flip":
                self.game.do_real_chain_flip(data["flips"], data["reasons"])
            self.anim_type = None
            return True
        return False

    async def run(self):
        running = True
        while running:
            dt = self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                    elif event.button == 3:
                        self.handle_right_click()
                elif event.type == pygame.FINGERDOWN:
                    # 触摸事件支持
                    x = event.x * WINDOW_WIDTH
                    y = event.y * WINDOW_HEIGHT
                    self.handle_click((x, y))

            if self.game.state == Game.ANIMATING:
                if self.anim_type is None:
                    self.start_animation()
                else:
                    done = self.update_animation(dt)
            else:
                self.anim_type = None

            if self.game.game_mode == 'pve' and self.game.current_player == 2 and self.game.state != Game.ANIMATING:
                self.ai_action_timer += dt
                if self.ai_action_timer >= self.ai_action_delay:
                    self.ai_action_timer = 0
                    if self.game.state == Game.SELECTING:
                        self.game.ai_move()
                    elif self.game.state == Game.FLIPPING:
                        self.game.ai_flip()
                    elif self.game.state == Game.CHAIN_FLIPPING:
                        self.game.ai_chain()
            else:
                self.ai_action_timer = 0

            if self.game.state == Game.RULE_INTRO:
                self.draw_rule_intro(dt)
            elif self.game.state == Game.MODE_SELECT:
                self.draw_mode_select()
            else:
                self.draw_board()
                if self.game.state == Game.ANIMATING and self.anim_type == "move":
                    self.draw_pieces(skip_pos=self.anim_move_from)
                    self.draw_moving_animation()
                elif self.game.state == Game.ANIMATING and self.anim_type == "flip":
                    self.draw_pieces()
                    self.draw_flipping_animation()
                else:
                    self.draw_pieces()
                self.draw_highlight()
                self.draw_ui()

            pygame.display.flip()
            await asyncio.sleep(0)

        pygame.quit()


async def main():
    logger = GameLogger()
    game = Game(logger)
    gui = GUI(game, logger)
    await gui.run()


if __name__ == "__main__":
    asyncio.run(main())
