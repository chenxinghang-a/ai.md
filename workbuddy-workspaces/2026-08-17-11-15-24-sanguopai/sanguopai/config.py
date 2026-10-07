"""三国牌全局配置：所有倍率、场次参数集中在这里，不硬编码到逻辑中。"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class SanGuoPaiConfig:
    # 牌型倍率 m_g，g=0..8 对应 单张..同花顺
    type_multipliers: Tuple[int, ...] = (10, 20, 30, 40, 60, 80, 100, 400, 1000)

    # 排名倍率：索引=名次，第1名占位（赢所有人），第2~5名
    rank_multipliers: Tuple[int, ...] = (0, 0, 32, 24, 12, 4)  # 索引2..5有效

    # 暴击倍率：同阵营人数（含第一名）1..5
    #   老板定：同阵营 = 1 2 4 8 12（5人同阵营致命）
    crit_multipliers: Tuple[int, ...] = (1, 1, 2, 4, 8, 12)  # 索引0不用

    # 杀牌倍率：同牌型/同类人数（含第一名）1..5
    #   老板定：同牌型 = 1 2 4 8 16（5人同型连锁最狠）
    kill_multipliers: Tuple[int, ...] = (1, 1, 2, 4, 8, 16)  # 索引0不用

    # 杀牌分类：key=grade，value=class_id；相同class_id视为同类
    # 单张/对子/两对/三张 同属一类(class 0)，其余各自一类
    kill_classes: Tuple[int, ...] = (0, 0, 0, 0, 1, 2, 3, 4, 5)

    # 阵营公共牌数量：魏、蜀、吴
    public_cards: Tuple[int, ...] = (3, 0, 2)

    # 玩家数、手牌数、轮次数
    n_players: int = 5
    hand_size: int = 8
    n_rounds: int = 4

    # ★ 计分方式（老板 2026-09-14 定："直接搞积分得了，拿 +/- 参与"）
    #   "score" = **纯积分制（默认）**：每个输家对每个第一名各付一份
    #              `±(牌型倍率 × 暴击 × 名次 × 杀牌)`，**无封顶、无财富档、不破产、无补豆**。
    #     优点：封顶会把"打得好"和"打得差"抹成同一个数（多数局面 L 都超 1800万 → 都付满），
    #           策略差异被抹平、梯度信号消失；积分制下差异**直接体现在分数上**，更适合练牌。
    #   "chips" = 豆（含封顶 1800万 / 赢家收款财富档 / 破产补豆，即经济系统那一套）
    scoring: str = "score"

    # 场次参数（顶级场）
    base_score: int = 4500
    # 结算两侧封顶（**不对称**，欢乐斗地主规则）：
    #   输（支付）：恒为 cap(1800万)，"管你有多少"，不看财富档；实付受「当前豆」限制，
    #              付不满即破产，缺口由赢家自担（"赢家吃亏"）。
    #   赢（收款）：每份上限 = clamp( max(入场豆, 当前豆), min_win, cap )
    #              · 带 >=1800万 → 收满1800万（看入场豆，中途掉豆也照收）
    #              · 带 450万~1800万 → 入场/当前谁大用谁
    #              · 带 <450万 → 每份只收450万（低豆赢不大）
    cap: int = 18_000_000  # 输家封顶 / 赢家收款上限的顶（1800万）
    min_win: int = 4_500_000  # 赢家收款上限的底（450万）
    entry_min: int = 160_000  # 入场最少豆（门槛，不直接影响结算）
    rebuy: int = 160_000  # 破产补豆：局间续打补 16 万豆（= 入场门槛）
    ticket: int = 0  # 门票：老板定性为"没实现" → 设为 0，池子豆子守恒（不进系统池）

    def validate(self):
        assert len(self.type_multipliers) == 9
        assert len(self.rank_multipliers) == 6  # 索引0,1占位，2..5有效
        assert len(self.crit_multipliers) == 6
        assert len(self.kill_multipliers) == 6
        assert len(self.kill_classes) == 9


# 默认配置
DEFAULT_CONFIG = SanGuoPaiConfig()
