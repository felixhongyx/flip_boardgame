from typing import List, Tuple, Optional
from board import Board, FlipRule, ChainFlipHandler


class AIPlayer:
    """AI玩家 - 贪心策略"""

    def __init__(self, player_num: int):
        self.player_num = player_num  # 1 或 2
        self.opponent = 3 - player_num

    def choose_move(self, board: Board) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        选择一个走法
        返回: (from_pos, to_pos)
        """
        best_score = -float('inf')
        best_move = None

        # 枚举所有己方棋子
        from_positions = board.get_valid_moves(self.player_num)
        print(f"AI: found {len(from_positions)} from positions")

        for from_pos in from_positions:
            # 枚举该棋子的所有合法移动
            to_positions = board.get_valid_moves(self.player_num, from_pos)
            print(f"AI: {from_pos} has {len(to_positions)} moves")
            for to_pos in to_positions:
                # 双重验证：确保真的可以走
                if not board.has_connection(from_pos, to_pos):
                    continue
                if board.get_piece(to_pos) != 0:
                    continue
                # 模拟这个走法
                score = self._evaluate_move(board, from_pos, to_pos)
                if score > best_score:
                    best_score = score
                    best_move = (from_pos, to_pos)

        print(f"AI: best_move = {best_move}")
        return best_move

    def _evaluate_move(self, board: Board, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> float:
        """评估一个走法的分数"""
        # 复制棋盘模拟
        sim_board = board.copy()
        sim_board.move_piece(from_pos, to_pos)
        flip_rule = FlipRule(sim_board)

        score = 0.0

        # 1. 目标位置价值
        score += Board.evaluate_position(to_pos) * 10

        # 2. 翻转价值
        flip_groups = flip_rule.get_flip_groups_after_move(self.player_num, to_pos)
        if flip_groups:
            # 选择能翻转最多的组
            best_group = max(flip_groups, key=lambda g: len(g["flips"]))
            flip_count = len(best_group["flips"])
            # 翻转得分：每个棋子100分，规则b额外加50分
            score += flip_count * 100
            if best_group["type"] == "b":
                score += 50

        # 3. 连锁潜力（简单评估）
        # 如果走棋后有触发点，额外加分
        triggers = flip_rule.get_triggers(self.player_num)
        if triggers:
            for t in triggers:
                groups = flip_rule.get_flip_groups_for_trigger(self.player_num, t)
                if groups:
                    max_flip = max(len(g["flips"]) for g in groups)
                    score += max_flip * 30  # 连锁潜力分

        return score

    def choose_flip_group(self, groups: List[dict]) -> int:
        """
        选择翻转组
        返回: 选中的组索引
        """
        # 优先选择翻转多的组，规则b优先
        best_idx = 0
        best_score = -1
        for i, group in enumerate(groups):
            score = len(group["flips"]) * 10
            if group["type"] == "b":
                score += 5
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def choose_chain_trigger(self, chain_handler: ChainFlipHandler) -> Tuple[Optional[Tuple[int, int]], Optional[int]]:
        """
        选择连锁翻转的触发点和组
        返回: (trigger_pos, group_idx) 或 (None, None) 如果跳过
        """
        triggers = chain_handler.get_triggers()
        if not triggers:
            return None, None

        best_score = -1
        best_trigger = None
        best_group_idx = 0

        for t in triggers:
            # 临时选中该触发点以获取分组
            chain_handler.select_trigger(t)
            groups = chain_handler.get_available_groups()
            if not groups:
                continue

            # 选该触发点下最好的组
            group_idx = self.choose_flip_group(groups)
            score = len(groups[group_idx]["flips"]) * 10
            if groups[group_idx]["type"] == "b":
                score += 5

            if score > best_score:
                best_score = score
                best_trigger = t
                best_group_idx = group_idx

        return best_trigger, best_group_idx
