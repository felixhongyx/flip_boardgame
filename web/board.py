from typing import List, Tuple, Optional

GRID_SIZE = 7


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
        gy = min(fy, ty)

        # 中间两行（第2、3行）是X形，两个方向斜线都允许
        if gy == 2 or gy == 3:
            return True

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

    def has_any_move(self, player: int) -> bool:
        """检查玩家是否有任何合法走法"""
        from_positions = self.get_valid_moves(player)
        for from_pos in from_positions:
            to_positions = self.get_valid_moves(player, from_pos)
            if to_positions:
                return True
        return False

    @staticmethod
    def evaluate_position(pos: Tuple[int, int]) -> float:
        """评估一个位置的价值（中心更高）"""
        x, y = pos
        center_x, center_y = GRID_SIZE / 2 - 0.5, GRID_SIZE / 2 - 0.5
        # 距离中心越近价值越高
        distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
        max_distance = ((GRID_SIZE / 2) ** 2 + (GRID_SIZE / 2) ** 2) ** 0.5
        return (max_distance - distance) / max_distance


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

    def __init__(self, board: Board, flip_rule: FlipRule):
        self.board = board
        self.flip_rule = flip_rule
        self.logger = None  # 会在Game中设置
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
            if self.logger:
                self.logger.log_flip(self.player, pos, reason)

        # 重新获取该触发点的剩余分组
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
