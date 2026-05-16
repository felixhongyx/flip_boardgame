
import pygame
import sys
from datetime import datetime
from typing import List, Tuple, Optional, Set

# 常量定义
GRID_SIZE = 7  # 7x7交叉点 = 6x6棋盘
CELL_SIZE = 80
MARGIN = 60
WINDOW_WIDTH = MARGIN * 2 + CELL_SIZE * (GRID_SIZE - 1)
WINDOW_HEIGHT = MARGIN * 2 + CELL_SIZE * (GRID_SIZE - 1) + 100

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PLAYER1_COLOR = (220, 50, 50)  # 红色
PLAYER2_COLOR = (50, 50, 220)  # 蓝色
BOARD_COLOR = (245, 222, 179)
HIGHLIGHT_COLOR = (255, 255, 0)
SELECTED_COLOR = (0, 255, 0)


class GameLogger:
    """游戏日志记录器"""

    def __init__(self, log_file: str = "game_log.txt"):
        self.log_file = log_file
        self.turn_count = 0
        # 清空日志文件
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"=== 游戏开始 - {datetime.now()} ===\n\n")

    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}\n"
        print(log_line, end="")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def log_turn_start(self, player: int):
        self.turn_count += 1
        self.log(f"--- 回合 {self.turn_count} - 玩家{player} ---")

    def log_move(self, player: int, from_pos: Tuple[int, int], to_pos: Tuple[int, int]):
        self.log(f"玩家{player} 走棋: {from_pos} -> {to_pos}")

    def log_flip(self, player: int, flipped_pos: Tuple[int, int], reason: str):
        self.log(f"玩家{player} 翻转 {flipped_pos} - {reason}")

    def log_chain_flip_start(self):
        self.log("--- 连锁翻转阶段 ---")

    def log_chain_flip_choice(self, player: int, choice: str):
        self.log(f"玩家{player} 选择连锁翻转: {choice}")

    def log_game_over(self, winner: int):
        self.log(f"\n=== 游戏结束 - 玩家{winner} 获胜! ===")

    def log_board_state(self, board: List[List[int]]):
        """记录棋盘状态"""
        self.log("棋盘状态:")
        for row in board:
            self.log("  " + " ".join(str(c) if c != 0 else "." for c in row))


class Board:
    """棋盘类"""

    def __init__(self):
        # 初始化空棋盘: 0=空, 1=玩家1, 2=玩家2
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self._init_pieces()

    def _init_pieces(self):
        """初始化棋子位置"""
        # 玩家1在顶部两行 (y=0, y=1)
        for x in range(GRID_SIZE):
            self.grid[0][x] = 1
            self.grid[1][x] = 1
        # 玩家2在底部两行 (y=5, y=6)
        for x in range(GRID_SIZE):
            self.grid[5][x] = 2
            self.grid[6][x] = 2

    def get_piece(self, pos: Tuple[int, int]) -> int:
        x, y = pos
        return self.grid[y][x]

    def set_piece(self, pos: Tuple[int, int], player: int):
        x, y = pos
        self.grid[y][x] = player

    def has_connection(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """检查两点之间是否有连线（根据棋盘设计）"""
        fx, fy = from_pos
        tx, ty = to_pos

        dx = tx - fx
        dy = ty - fy

        # 横竖移动始终允许
        if dx == 0 or dy == 0:
            return True

        # 只能走一格斜
        if abs(dx) != 1 or abs(dy) != 1:
            return False

        # 确定这两个点属于哪个格子的斜线
        # gy是斜线所在的行（看绘制代码，y循环是斜线的行）
        gy = min(fy, ty)

        # 检查是否有对应斜线（与draw_board一致）
        if gy % 2 == 1:
            # 奇数行: 右下斜 \ (连接 (x, gy) 和 (x+1, gy+1))
            return (fx == tx - 1 and fy == gy and ty == gy + 1) or \
                   (fx == tx + 1 and fy == gy + 1 and ty == gy)
        else:
            # 偶数行: 右上斜 / (连接 (x+1, gy) 和 (x, gy+1))
            return (fx == tx + 1 and fy == gy and ty == gy + 1) or \
                   (fx == tx - 1 and fy == gy + 1 and ty == gy)

    def get_valid_moves(self, player: int, from_pos: Optional[Tuple[int, int]] = None) -> List[Tuple[int, int]]:
        """获取合法移动"""
        if from_pos is None:
            # 返回所有己方棋子位置
            return [(x, y) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if self.grid[y][x] == player]

        fx, fy = from_pos
        valid = []

        # 检查8个方向
        directions = [(-1, -1), (0, -1), (1, -1),
                      (-1, 0), (1, 0),
                      (-1, 1), (0, 1), (1, 1)]

        for dx, dy in directions:
            tx, ty = fx + dx, fy + dy
            # 检查是否在棋盘范围内
            if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                # 检查终点是否为空
                if self.grid[ty][tx] == 0:
                    # 检查是否有连线
                    if self.has_connection(from_pos, (tx, ty)):
                        valid.append((tx, ty))

        return valid

    def move_piece(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> bool:
        """移动棋子，返回是否成功"""
        fx, fy = from_pos
        tx, ty = to_pos

        player = self.grid[fy][fx]
        if player == 0:
            return False
        if self.grid[ty][tx] != 0:
            return False

        self.grid[ty][tx] = player
        self.grid[fy][fx] = 0
        return True

    def copy(self) -> 'Board':
        """复制棋盘"""
        new_board = Board()
        new_board.grid = [row[:] for row in self.grid]
        return new_board

    def count_pieces(self, player: int) -> int:
        """统计棋子数量"""
        return sum(row.count(player) for row in self.grid)


class FlipRule:
    """翻转规则"""

    def __init__(self, board: Board):
        self.board = board

    def get_flips_after_move(self, player: int, new_pos: Tuple[int, int]) -> List[Tuple[Tuple[int, int], str]]:
        """获取走棋后可以翻转的棋子列表，返回 (位置, 原因)"""
        groups = self.get_flip_groups_after_move(player, new_pos)
        result = []
        for g in groups:
            result.extend(g["flips"])
        return result

    def get_flip_groups_after_move(self, player: int, new_pos: Tuple[int, int]) -> List[dict]:
        """获取走棋后可以翻转的棋子分组，返回 [{"type": "a"/"b", "dir": (dx, dy), "flips": [(pos, reason), ...]}]"""
        groups = []
        opponent = 3 - player

        # 8个方向
        directions = [(-1, -1), (0, -1), (1, -1),
                      (-1, 0), (1, 0),
                      (-1, 1), (0, 1), (1, 1)]

        nx, ny = new_pos

        for dx, dy in directions:
            # 规则a: 己方-敌方-己方 (新位置是第二个己方)
            ax1, ay1 = nx + dx, ny + dy
            ax2, ay2 = nx + dx * 2, ny + dy * 2
            if (0 <= ax1 < GRID_SIZE and 0 <= ay1 < GRID_SIZE and
                    0 <= ax2 < GRID_SIZE and 0 <= ay2 < GRID_SIZE):
                if (self.board.get_piece((ax1, ay1)) == opponent and
                        self.board.get_piece((ax2, ay2)) == player):
                    groups.append({
                        "type": "a",
                        "dir": (dx, dy),
                        "flips": [((ax1, ay1), f"规则a: 方向({dx},{dy}) 己方-敌方-己方")]
                    })

            # 规则b: 敌方-己方-敌方 (新位置是中间的己方)
            bx1, by1 = nx - dx, ny - dy
            bx2, by2 = nx + dx, ny + dy
            if (0 <= bx1 < GRID_SIZE and 0 <= by1 < GRID_SIZE and
                    0 <= bx2 < GRID_SIZE and 0 <= by2 < GRID_SIZE):
                if (self.board.get_piece((bx1, by1)) == opponent and
                        self.board.get_piece((bx2, by2)) == opponent):
                    groups.append({
                        "type": "b",
                        "dir": (dx, dy),
                        "flips": [
                            ((bx1, by1), f"规则b: 方向({dx},{dy}) 敌方-己方-敌方 (左)"),
                            ((bx2, by2), f"规则b: 方向({dx},{dy}) 敌方-己方-敌方 (右)")
                        ]
                    })

        return groups

    def get_triggers(self, player: int) -> List[Tuple[int, int]]:
        """获取可以触发连锁翻转的己方棋子位置"""
        triggers = []
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.board.get_piece((x, y)) == player:
                    if self._get_flips_for_trigger(player, (x, y)):
                        triggers.append((x, y))
        return triggers

    def get_flips_for_trigger(self, player: int, trigger_pos: Tuple[int, int]) -> List[Tuple[Tuple[int, int], str]]:
        """获取选中触发点后应该翻转的棋子"""
        return self._get_flips_for_trigger(player, trigger_pos)

    def get_flip_groups_for_trigger(self, player: int, pos: Tuple[int, int]) -> List[dict]:
        """获取单个触发点能翻转的分组"""
        groups = []
        opponent = 3 - player
        px, py = pos

        directions = [(-1, -1), (0, -1), (1, -1),
                      (-1, 0), (1, 0),
                      (-1, 1), (0, 1), (1, 1)]

        for dx, dy in directions:
            # 规则a: 己方-敌方-己方 (当前位置是第一个己方)
            ax1, ay1 = px + dx, py + dy
            ax2, ay2 = px + dx * 2, py + dy * 2
            if (0 <= ax1 < GRID_SIZE and 0 <= ay1 < GRID_SIZE and
                    0 <= ax2 < GRID_SIZE and 0 <= ay2 < GRID_SIZE):
                if (self.board.get_piece((ax1, ay1)) == opponent and
                        self.board.get_piece((ax2, ay2)) == player):
                    groups.append({
                        "type": "a",
                        "dir": (dx, dy),
                        "flips": [((ax1, ay1), f"连锁-规则a 触发点({px},{py})")]
                    })

            # 规则b: 敌方-己方-敌方 (当前位置是中间的己方)
            bx1, by1 = px - dx, py - dy
            bx2, by2 = px + dx, py + dy
            if (0 <= bx1 < GRID_SIZE and 0 <= by1 < GRID_SIZE and
                    0 <= bx2 < GRID_SIZE and 0 <= by2 < GRID_SIZE):
                if (self.board.get_piece((bx1, by1)) == opponent and
                        self.board.get_piece((bx2, by2)) == opponent):
                    groups.append({
                        "type": "b",
                        "dir": (dx, dy),
                        "flips": [
                            ((bx1, by1), f"连锁-规则b 触发点({px},{py})"),
                            ((bx2, by2), f"连锁-规则b 触发点({px},{py})")
                        ]
                    })

        return groups

    def _get_flips_for_trigger(self, player: int, pos: Tuple[int, int]) -> List[Tuple[Tuple[int, int], str]]:
        """获取单个触发点能翻转的所有棋子"""
        groups = self.get_flip_groups_for_trigger(player, pos)
        result = []
        for g in groups:
            result.extend(g["flips"])
        return result


class ChainFlipHandler:
    """连锁翻转处理器"""

    def __init__(self, board: Board, flip_rule: FlipRule, logger: GameLogger):
        self.board = board
        self.flip_rule = flip_rule
        self.logger = logger
        self.player = 0
        self.available_triggers = []
        self.selected_trigger = None
        self.preview_flips = []
        # 新增：分组相关
        self.available_groups = []
        self.selected_group = None

    def start_chain_flip(self, player: int) -> bool:
        """开始连锁翻转阶段，返回是否有可翻转的"""
        self.player = player
        self.available_triggers = self.flip_rule.get_triggers(player)
        self.selected_trigger = None
        self.preview_flips = []
        self.available_groups = []
        self.selected_group = None
        return len(self.available_triggers) > 0

    def get_triggers(self) -> List[Tuple[int, int]]:
        """获取可用触发点"""
        return self.available_triggers

    def get_preview_flips(self) -> List[Tuple[int, int]]:
        """获取当前预览的翻转位置"""
        return self.preview_flips

    def get_available_groups(self) -> List[dict]:
        """获取当前选中触发点的可用分组"""
        return self.available_groups

    def get_selected_group(self) -> Optional[int]:
        """获取当前选中的分组索引"""
        return self.selected_group

    def select_trigger(self, pos: Tuple[int, int]):
        """选择一个触发点"""
        if pos in self.available_triggers:
            self.selected_trigger = pos
            self.available_groups = self.flip_rule.get_flip_groups_for_trigger(self.player, pos)
            self.selected_group = None
            # 默认预览第一个组
            if self.available_groups:
                self.preview_flips = [p for p, _ in self.available_groups[0]["flips"]]
            else:
                self.preview_flips = []

    def select_group(self, pos: Tuple[int, int]):
        """选择一个翻转组"""
        if self.selected_trigger is None:
            return
        for i, group in enumerate(self.available_groups):
            for p, _ in group["flips"]:
                if p == pos:
                    self.selected_group = i
                    self.preview_flips = [p for p, _ in group["flips"]]
                    return

    def apply_group(self) -> bool:
        """应用选中的翻转组，返回是否还能继续连锁"""
        if self.selected_trigger is None or self.selected_group is None:
            return False

        group = self.available_groups[self.selected_group]
        for pos, reason in group["flips"]:
            self.board.set_piece(pos, self.player)
            self.logger.log_flip(self.player, pos, reason)

        # 重新获取该触发点的剩余分组（可能有新产生的，但先检查当前触发点是否还有效）
        remaining_groups = self.flip_rule.get_flip_groups_for_trigger(self.player, self.selected_trigger)
        if remaining_groups:
            # 还有其他分组可选，保持在当前触发点
            self.available_groups = remaining_groups
            self.selected_group = None
            self.preview_flips = [p for p, _ in remaining_groups[0]["flips"]]
            return True
        else:
            # 当前触发点已无分组，检查是否有其他触发点
            self.selected_trigger = None
            self.available_groups = []
            self.selected_group = None
            self.preview_flips = []
            self.available_triggers = self.flip_rule.get_triggers(self.player)
            return len(self.available_triggers) > 0


class Game:
    """游戏主逻辑"""

    SELECTING = "selecting"
    MOVING = "moving"
    FLIPPING = "flipping"
    CHAIN_FLIPPING = "chain_flipping"
    GAME_OVER = "game_over"

    def __init__(self, logger: GameLogger):
        self.logger = logger
        self.board = Board()
        self.flip_rule = FlipRule(self.board)
        self.chain_handler = ChainFlipHandler(self.board, self.flip_rule, logger)

        self.current_player = 1
        self.state = Game.SELECTING
        self.selected_pos = None
        self.pending_flips = []
        self.pending_flip_groups = []  # 翻转分组
        self.selected_flip_group = None  # 选中的分组索引

        self.logger.log_board_state(self.board.grid)

    def select_piece(self, pos: Tuple[int, int]) -> bool:
        """选择棋子"""
        if self.state != Game.SELECTING:
            return False
        if self.board.get_piece(pos) != self.current_player:
            return False

        self.selected_pos = pos
        self.state = Game.MOVING
        self.logger.log(f"玩家{self.current_player} 选择 {pos}")
        return True

    def move_to(self, pos: Tuple[int, int]) -> bool:
        """移动到指定位置"""
        if self.state != Game.MOVING:
            return False
        if pos not in self.board.get_valid_moves(self.current_player, self.selected_pos):
            return False

        # 执行移动
        from_pos = self.selected_pos
        self.board.move_piece(from_pos, pos)
        self.logger.log_move(self.current_player, from_pos, pos)
        self.logger.log_board_state(self.board.grid)

        # 检查翻转
        self.pending_flip_groups = self.flip_rule.get_flip_groups_after_move(self.current_player, pos)
        self.pending_flips = self.flip_rule.get_flips_after_move(self.current_player, pos)
        self.selected_flip_group = None
        if self.pending_flip_groups:
            self.state = Game.FLIPPING
            self.selected_pos = pos
            for i, g in enumerate(self.pending_flip_groups):
                self.logger.log(f"翻转组{i}: {[p for p, _ in g['flips']]} (规则{g['type']})")
        else:
            self._end_turn()

        return True

    def select_flip_group(self, pos: Tuple[int, int]):
        """选择翻转组"""
        if self.state != Game.FLIPPING:
            return
        for i, group in enumerate(self.pending_flip_groups):
            for p, _ in group["flips"]:
                if p == pos:
                    self.selected_flip_group = i
                    return

    def apply_flips(self):
        """应用选中的翻转组"""
        if self.state != Game.FLIPPING:
            return
        if self.selected_flip_group is None:
            return

        group = self.pending_flip_groups[self.selected_flip_group]
        for pos, reason in group["flips"]:
            self.board.set_piece(pos, self.current_player)
            self.logger.log_flip(self.current_player, pos, reason)

        self.logger.log_board_state(self.board.grid)

        # 检查连锁翻转
        self.pending_flips = []
        self.pending_flip_groups = []
        self.selected_flip_group = None
        if self.chain_handler.start_chain_flip(self.current_player):
            self.state = Game.CHAIN_FLIPPING
            self.logger.log_chain_flip_start()
        else:
            self._end_turn()

    def skip_flips(self):
        """跳过翻转阶段（如果玩家不想翻转任何组）"""
        if self.state != Game.FLIPPING:
            return
        self.logger.log(f"玩家{self.current_player} 跳过翻转")
        self.pending_flips = []
        self.pending_flip_groups = []
        self.selected_flip_group = None
        self._end_turn()

    def chain_select(self, pos: Tuple[int, int]):
        """连锁翻转时选择触发点或翻转组"""
        if self.state != Game.CHAIN_FLIPPING:
            return
        # 如果已选中触发点，尝试选择分组
        if self.chain_handler.selected_trigger is not None:
            self.chain_handler.select_group(pos)
        # 否则选择触发点
        if self.chain_handler.selected_trigger is None or pos in self.chain_handler.available_triggers:
            self.chain_handler.select_trigger(pos)

    def chain_apply(self):
        """应用连锁翻转"""
        if self.state != Game.CHAIN_FLIPPING:
            return

        has_more = self.chain_handler.apply_group()
        self.logger.log_board_state(self.board.grid)

        if not has_more:
            self._end_turn()

    def chain_skip(self):
        """跳过连锁翻转"""
        if self.state != Game.CHAIN_FLIPPING:
            return
        self.logger.log_chain_flip_choice(self.current_player, "跳过")
        self._end_turn()

    def cancel_selection(self):
        """取消选择"""
        if self.state == Game.MOVING:
            self.state = Game.SELECTING
            self.selected_pos = None

    def _end_turn(self):
        """结束回合"""
        # 检查游戏结束
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

        # 切换玩家
        self.current_player = 3 - self.current_player
        self.state = Game.SELECTING
        self.selected_pos = None
        self.logger.log_turn_start(self.current_player)

    def restart(self):
        """重新开始"""
        self.__init__(self.logger)


class GUI:
    """pygame界面"""

    def __init__(self, game: Game, logger: GameLogger):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("双人棋类游戏")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("simhei", 24)
        self.small_font = pygame.font.SysFont("simhei", 18)

        self.game = game
        self.logger = logger

    def pos_to_screen(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        x, y = pos
        return (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)

    def screen_to_pos(self, screen_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        sx, sy = screen_pos
        x = round((sx - MARGIN) / CELL_SIZE)
        y = round((sy - MARGIN) / CELL_SIZE)
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            dx = abs(sx - (MARGIN + x * CELL_SIZE))
            dy = abs(sy - (MARGIN + y * CELL_SIZE))
            if dx < 25 and dy < 25:
                return (x, y)
        return None

    def draw_board(self):
        """绘制棋盘"""
        self.screen.fill(BOARD_COLOR)

        # 绘制横线
        for y in range(GRID_SIZE):
            start = self.pos_to_screen((0, y))
            end = self.pos_to_screen((GRID_SIZE - 1, y))
            pygame.draw.line(self.screen, BLACK, start, end, 2)

        # 绘制竖线
        for x in range(GRID_SIZE):
            start = self.pos_to_screen((x, 0))
            end = self.pos_to_screen((x, GRID_SIZE - 1))
            pygame.draw.line(self.screen, BLACK, start, end, 2)

        # 绘制斜线
        for y in range(GRID_SIZE - 1):
            for x in range(GRID_SIZE - 1):
                if y % 2 == 1:
                    # 奇数行: 右下斜 \
                    start = self.pos_to_screen((x, y))
                    end = self.pos_to_screen((x + 1, y + 1))
                    pygame.draw.line(self.screen, BLACK, start, end, 1)
                else:
                    # 偶数行: 右上斜 /
                    start = self.pos_to_screen((x + 1, y))
                    end = self.pos_to_screen((x, y + 1))
                    pygame.draw.line(self.screen, BLACK, start, end, 1)

        # 绘制坐标提示
        for x in range(GRID_SIZE):
            txt = self.small_font.render(str(x), True, BLACK)
            pos = self.pos_to_screen((x, -0.4))
            self.screen.blit(txt, (pos[0] - txt.get_width() // 2, pos[1]))
        for y in range(GRID_SIZE):
            txt = self.small_font.render(str(y), True, BLACK)
            pos = self.pos_to_screen((-0.4, y))
            self.screen.blit(txt, (pos[0] - txt.get_width() // 2, pos[1] - txt.get_height() // 2))

    def draw_pieces(self):
        """绘制棋子"""
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                piece = self.game.board.get_piece((x, y))
                if piece != 0:
                    color = PLAYER1_COLOR if piece == 1 else PLAYER2_COLOR
                    center = self.pos_to_screen((x, y))
                    pygame.draw.circle(self.screen, color, center, 25)
                    pygame.draw.circle(self.screen, BLACK, center, 25, 2)

    def draw_highlight(self):
        """绘制高亮提示"""
        # 选中的棋子
        if self.game.selected_pos:
            center = self.pos_to_screen(self.game.selected_pos)
            pygame.draw.circle(self.screen, SELECTED_COLOR, center, 30, 4)

        # 合法移动位置
        if self.game.state == Game.MOVING:
            valid_moves = self.game.board.get_valid_moves(self.game.current_player, self.game.selected_pos)
            for pos in valid_moves:
                center = self.pos_to_screen(pos)
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, center, 15, 3)

        # 待翻转的棋子 - 分组显示
        if self.game.state == Game.FLIPPING:
            colors = [(0, 200, 255), (255, 0, 255), (0, 255, 128), (255, 128, 0)]  # 不同组颜色
            for i, group in enumerate(self.game.pending_flip_groups):
                color = colors[i % len(colors)]
                is_selected = self.game.selected_flip_group == i
                line_width = 6 if is_selected else 3
                for pos, _ in group["flips"]:
                    center = self.pos_to_screen(pos)
                    pygame.draw.circle(self.screen, color, center, 30, line_width)

        # 连锁翻转选择
        if self.game.state == Game.CHAIN_FLIPPING:
            triggers = self.game.chain_handler.get_triggers()
            preview = self.game.chain_handler.get_preview_flips()
            selected_trigger = self.game.chain_handler.selected_trigger
            groups = self.game.chain_handler.get_available_groups()
            selected_group_idx = self.game.chain_handler.get_selected_group()

            # 绘制可点击的触发点（己方棋子）
            for pos in triggers:
                center = self.pos_to_screen(pos)
                # 画一个白色圆圈在后面，确保可见
                pygame.draw.circle(self.screen, (255,255,255), center, 35)
                # 再画棋子
                color = PLAYER1_COLOR if self.game.current_player == 1 else PLAYER2_COLOR
                pygame.draw.circle(self.screen, color, center, 25)
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, center, 35, 6)

            # 如果已选中触发点且有分组，分组显示待翻转棋子
            if selected_trigger is not None and groups:
                colors = [(0, 200, 255), (255, 0, 255), (0, 255, 128), (255, 128, 0)]
                for i, group in enumerate(groups):
                    color = colors[i % len(colors)]
                    is_selected = selected_group_idx == i
                    line_width = 6 if is_selected else 3
                    for pos, _ in group["flips"]:
                        center = self.pos_to_screen(pos)
                        pygame.draw.circle(self.screen, color, center, 30, line_width)
            else:
                # 否则只画预览
                for pos in preview:
                    center = self.pos_to_screen(pos)
                    pygame.draw.circle(self.screen, SELECTED_COLOR, center, 30, 5)

    def draw_ui(self):
        """绘制UI"""
        y = MARGIN + CELL_SIZE * (GRID_SIZE - 1) + 20

        # 状态提示
        if self.game.state == Game.GAME_OVER:
            winner = 2 if self.game.board.count_pieces(1) == 0 else 1
            txt = self.font.render(f"游戏结束! 玩家{winner} 获胜! 点击重新开始", True, BLACK)
        else:
            color = PLAYER1_COLOR if self.game.current_player == 1 else PLAYER2_COLOR
            player_name = f"玩家{self.game.current_player}"
            if self.game.state == Game.SELECTING:
                msg = f"{player_name} - 选择棋子"
            elif self.game.state == Game.MOVING:
                msg = f"{player_name} - 选择目标位置 (右键取消)"
            elif self.game.state == Game.FLIPPING:
                msg = f"{player_name} - 点击棋子选择翻转组, 确认/跳过"
            elif self.game.state == Game.CHAIN_FLIPPING:
                msg = f"{player_name} - 选择触发点, 再选择翻转组, 确认/跳过"
            else:
                msg = ""
            txt = self.font.render(msg, True, color)

        self.screen.blit(txt, (20, y))

        # 棋子统计
        p1 = self.game.board.count_pieces(1)
        p2 = self.game.board.count_pieces(2)
        stat = self.font.render(f"红: {p1}  蓝: {p2}", True, BLACK)
        self.screen.blit(stat, (WINDOW_WIDTH - 200, y))

        # 翻转按钮
        if self.game.state == Game.FLIPPING:
            self._draw_flip_buttons()
        # 连锁翻转按钮
        elif self.game.state == Game.CHAIN_FLIPPING:
            self._draw_chain_buttons()

    def _draw_flip_buttons(self):
        """绘制翻转阶段按钮"""
        y = WINDOW_HEIGHT - 50

        # 确认按钮
        btn_confirm = pygame.Rect(WINDOW_WIDTH - 240, y, 100, 40)
        pygame.draw.rect(self.screen, (100, 200, 100), btn_confirm)
        txt = self.font.render("确认", True, BLACK)
        self.screen.blit(txt, (btn_confirm.x + 25, btn_confirm.y + 5))
        self.btn_flip_confirm = btn_confirm

        # 跳过按钮
        btn_skip = pygame.Rect(WINDOW_WIDTH - 130, y, 100, 40)
        pygame.draw.rect(self.screen, (200, 100, 100), btn_skip)
        txt = self.font.render("跳过", True, BLACK)
        self.screen.blit(txt, (btn_skip.x + 25, btn_skip.y + 5))
        self.btn_flip_skip = btn_skip

    def _draw_chain_buttons(self):
        """绘制连锁翻转按钮"""
        y = WINDOW_HEIGHT - 50

        # 确认按钮
        btn_confirm = pygame.Rect(WINDOW_WIDTH - 240, y, 100, 40)
        pygame.draw.rect(self.screen, (100, 200, 100), btn_confirm)
        txt = self.font.render("确认", True, BLACK)
        self.screen.blit(txt, (btn_confirm.x + 25, btn_confirm.y + 5))
        self.btn_confirm = btn_confirm

        # 跳过按钮
        btn_skip = pygame.Rect(WINDOW_WIDTH - 130, y, 100, 40)
        pygame.draw.rect(self.screen, (200, 100, 100), btn_skip)
        txt = self.font.render("跳过", True, BLACK)
        self.screen.blit(txt, (btn_skip.x + 25, btn_skip.y + 5))
        self.btn_skip = btn_skip

    def handle_click(self, pos: Tuple[int, int]):
        """处理点击"""
        if self.game.state == Game.GAME_OVER:
            self.game.restart()
            return

        # 检查翻转阶段按钮
        if self.game.state == Game.FLIPPING:
            if hasattr(self, 'btn_flip_confirm') and self.btn_flip_confirm.collidepoint(pos):
                self.game.apply_flips()
                return
            if hasattr(self, 'btn_flip_skip') and self.btn_flip_skip.collidepoint(pos):
                self.game.skip_flips()
                return

        # 检查连锁翻转按钮
        if self.game.state == Game.CHAIN_FLIPPING:
            if hasattr(self, 'btn_confirm') and self.btn_confirm.collidepoint(pos):
                self.game.chain_apply()
                return
            if hasattr(self, 'btn_skip') and self.btn_skip.collidepoint(pos):
                self.game.chain_skip()
                return

        board_pos = self.screen_to_pos(pos)
        if not board_pos:
            return

        if self.game.state == Game.SELECTING:
            self.game.select_piece(board_pos)
        elif self.game.state == Game.MOVING:
            if not self.game.move_to(board_pos):
                self.game.select_piece(board_pos)
        elif self.game.state == Game.FLIPPING:
            self.game.select_flip_group(board_pos)
        elif self.game.state == Game.CHAIN_FLIPPING:
            self.game.chain_select(board_pos)

    def handle_right_click(self):
        """处理右键"""
        self.game.cancel_selection()

    def run(self):
        """主循环"""
        self.logger.log_turn_start(1)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                    elif event.button == 3:
                        self.handle_right_click()

            self.draw_board()
            self.draw_pieces()
            self.draw_highlight()
            self.draw_ui()

            pygame.display.flip()
            self.clock.tick(30)

        pygame.quit()


def main():
    logger = GameLogger()
    game = Game(logger)
    gui = GUI(game, logger)
    gui.run()


if __name__ == "__main__":
    main()

