from typing import List, Tuple, Optional
from board import Board, FlipRule, ChainFlipHandler
import copy
import random

class AIPlayer:
    """AI玩家 - 使用 Minimax 算法 + Alpha-Beta 剪枝"""

    def __init__(self, player_num: int, depth: int = 2):
        self.player_num = player_num  # 1 或 2
        self.opponent = 3 - player_num
        self.depth = depth  # 搜索深度（2-3是性能和效果的平衡点）

    def choose_move(self, board: Board) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        选择一个走法
        返回: (from_pos, to_pos)
        """
        best_score = -float('inf')
        best_moves = []

        # 枚举所有己方棋子
        from_positions = board.get_valid_moves(self.player_num)

        for from_pos in from_positions:
            # 枚举该棋子的所有合法移动
            to_positions = board.get_valid_moves(self.player_num, from_pos)
            for to_pos in to_positions:
                # 模拟这个走法
                score = self._simulate_move_and_evaluate(board, from_pos, to_pos)
                if score > best_score:
                    best_score = score
                    best_moves = [(from_pos, to_pos)]
                elif score == best_score:
                    best_moves.append((from_pos, to_pos))

        # 从最优走法中随机选择
        if best_moves:
            return random.choice(best_moves)
        return None

    def _simulate_move_and_evaluate(self, board: Board, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> float:
        """模拟走棋并评估，包含立即翻转的处理"""
        # 创建棋盘副本
        sim_board = board.copy()
        sim_board.move_piece(from_pos, to_pos)

        # 处理走棋后的翻转（选择最优翻转）
        flip_rule = FlipRule(sim_board)
        flip_groups = flip_rule.get_flip_groups_after_move(self.player_num, to_pos)

        if flip_groups:
            # 选择对己方最有利的翻转组
            best_group = max(flip_groups, key=lambda g: self._count_flips(g))
            for pos, _ in best_group["flips"]:
                sim_board.set_piece(pos, self.player_num)

            # 处理连锁翻转（AI直接选择最优连锁）
            self._apply_best_chain_flips(sim_board, self.player_num)

        # 现在用 Minimax 评估这个局面
        return self._minimax(sim_board, self.depth - 1, -float('inf'), float('inf'), False)

    def _count_flips(self, group: dict) -> int:
        """计算一个翻转组能翻转多少棋子"""
        return len(group["flips"])

    def _apply_best_chain_flips(self, board: Board, player: int):
        """应用最优连锁翻转（贪心）"""
        flip_rule = FlipRule(board)
        chain_handler = ChainFlipHandler(board, flip_rule)

        while chain_handler.start_chain_flip(player):
            triggers = chain_handler.get_triggers()
            if not triggers:
                break

            best_trigger = None
            best_group_idx = 0
            best_score = -1

            for trigger in triggers:
                chain_handler.select_trigger(trigger)
                groups = chain_handler.get_available_groups()
                if not groups:
                    continue

                group_idx = self.choose_flip_group(groups)
                score = len(groups[group_idx]["flips"]) * 10
                if groups[group_idx]["type"] == "b":
                    score += 5

                if score > best_score:
                    best_score = score
                    best_trigger = trigger
                    best_group_idx = group_idx

            if best_trigger is None:
                break

            chain_handler.select_trigger(best_trigger)
            chain_handler.selected_group = best_group_idx
            # 应用这个翻转组
            group = chain_handler.available_groups[best_group_idx]
            for pos, _ in group["flips"]:
                board.set_piece(pos, player)

    def _minimax(self, board: Board, depth: int, alpha: float, beta: float, is_maximizing: bool) -> float:
        """Minimax 算法 + Alpha-Beta 剪枝"""
        # 检查游戏是否结束
        player1_count = board.count_pieces(1)
        player2_count = board.count_pieces(2)

        if player1_count == 0 or player2_count == 0:
            if self.player_num == 1:
                return 10000 if player2_count == 0 else -10000
            else:
                return 10000 if player1_count == 0 else -10000

        # 检查是否无子可走
        current_player = self.player_num if is_maximizing else self.opponent
        if not board.has_any_move(current_player):
            if self.player_num == 1:
                return 10000 if player1_count > player2_count else -10000
            else:
                return 10000 if player2_count > player1_count else -10000

        # 到达搜索深度，评估局面
        if depth == 0:
            return self._evaluate_board(board)

        if is_maximizing:
            max_eval = -float('inf')
            # 枚举所有可能的走法
            for from_pos in board.get_valid_moves(self.player_num):
                for to_pos in board.get_valid_moves(self.player_num, from_pos):
                    # 模拟走棋
                    new_board = board.copy()
                    new_board.move_piece(from_pos, to_pos)

                    # 处理翻转
                    flip_rule = FlipRule(new_board)
                    flip_groups = flip_rule.get_flip_groups_after_move(self.player_num, to_pos)
                    if flip_groups:
                        best_group = max(flip_groups, key=lambda g: self._count_flips(g))
                        for pos, _ in best_group["flips"]:
                            new_board.set_piece(pos, self.player_num)
                        # 处理连锁翻转
                        self._apply_best_chain_flips(new_board, self.player_num)

                    eval_score = self._minimax(new_board, depth - 1, alpha, beta, False)
                    max_eval = max(max_eval, eval_score)
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break  # Beta 剪枝
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            # 枚举对手所有可能的走法
            for from_pos in board.get_valid_moves(self.opponent):
                for to_pos in board.get_valid_moves(self.opponent, from_pos):
                    # 模拟走棋
                    new_board = board.copy()
                    new_board.move_piece(from_pos, to_pos)

                    # 处理翻转
                    flip_rule = FlipRule(new_board)
                    flip_groups = flip_rule.get_flip_groups_after_move(self.opponent, to_pos)
                    if flip_groups:
                        best_group = max(flip_groups, key=lambda g: self._count_flips(g))
                        for pos, _ in best_group["flips"]:
                            new_board.set_piece(pos, self.opponent)
                        # 处理连锁翻转
                        self._apply_best_chain_flips(new_board, self.opponent)

                    eval_score = self._minimax(new_board, depth - 1, alpha, beta, True)
                    min_eval = min(min_eval, eval_score)
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        break  # Alpha 剪枝
                if beta <= alpha:
                    break
            return min_eval

    def _evaluate_board(self, board: Board) -> float:
        """评估棋盘局面（正数表示对AI有利）"""
        score = 0.0

        # 1. 棋子数量优势
        my_count = board.count_pieces(self.player_num)
        opp_count = board.count_pieces(self.opponent)
        score += (my_count - opp_count) * 100

        # 2. 位置价值（中心更重要）
        for y in range(7):
            for x in range(7):
                piece = board.get_piece((x, y))
                if piece == self.player_num:
                    score += Board.evaluate_position((x, y)) * 10
                elif piece == self.opponent:
                    score -= Board.evaluate_position((x, y)) * 10

        # 3. 行动力优势（可走步数）
        my_mobility = self._count_moves(board, self.player_num)
        opp_mobility = self._count_moves(board, self.opponent)
        score += (my_mobility - opp_mobility) * 20

        # 4. 翻转潜力
        flip_rule = FlipRule(board)
        my_triggers = len(flip_rule.get_triggers(self.player_num))
        opp_triggers = len(flip_rule.get_triggers(self.opponent))
        score += (my_triggers - opp_triggers) * 30

        return score

    def _count_moves(self, board: Board, player: int) -> int:
        """计算玩家的总合法走法数"""
        count = 0
        from_positions = board.get_valid_moves(player)
        for from_pos in from_positions:
            count += len(board.get_valid_moves(player, from_pos))
        return count

    def choose_flip_group(self, groups: List[dict]) -> int:
        """
        选择翻转组
        返回: 选中的组索引
        """
        best_score = -1
        best_indices = []
        for i, group in enumerate(groups):
            score = len(group["flips"]) * 10
            if group["type"] == "b":
                score += 5
            if score > best_score:
                best_score = score
                best_indices = [i]
            elif score == best_score:
                best_indices.append(i)
        # 从最优选项中随机选择
        return random.choice(best_indices)

    def choose_chain_trigger(self, chain_handler: ChainFlipHandler) -> Tuple[Optional[Tuple[int, int]], Optional[int]]:
        """
        选择连锁翻转的触发点和组
        返回: (trigger_pos, group_idx) 或 (None, None) 如果跳过
        """
        triggers = chain_handler.get_triggers()
        if not triggers:
            return None, None

        best_score = -1
        best_options = []

        for t in triggers:
            chain_handler.select_trigger(t)
            groups = chain_handler.get_available_groups()
            if not groups:
                continue

            group_idx = self.choose_flip_group(groups)
            score = len(groups[group_idx]["flips"]) * 10
            if groups[group_idx]["type"] == "b":
                score += 5

            if score > best_score:
                best_score = score
                best_options = [(t, group_idx)]
            elif score == best_score:
                best_options.append((t, group_idx))

        # 从最优选项中随机选择
        if best_options:
            return random.choice(best_options)
        return None, None
