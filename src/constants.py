# 定数定義ファイル
# config.yamlから設定を読み込み、フォールバックとしてハードコード値を使用

import os
from typing import Dict, Any, Tuple, List

# YAML読み込みを試みる (インストールされていない場合はフォールバック)
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def _find_config_path() -> str:
    """config.yamlのパスを探す"""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    return os.path.join(project_root, "config.yaml")


def _load_config() -> Dict[str, Any]:
    """config.yamlを読み込む"""
    if not YAML_AVAILABLE:
        return {}

    config_path = _find_config_path()
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


# 設定ファイルを読み込み
_config = _load_config()


def _get(section: str, key: str, default: Any) -> Any:
    """設定値を取得 (セクション.キー形式)"""
    return _config.get(section, {}).get(key, default)


def _get_color(key: str, default: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """色設定を取得してタプルに変換"""
    color = _config.get("colors", {}).get(key, default)
    if isinstance(color, list) and len(color) == 3:
        return tuple(color)
    return default


# === 椅子関連 ===
CHAIR_SIZE = _get("chair", "size", 700)              # 椅子のサイズ(mm) - 正方形
CHAIR_DESK_GAP = _get("chair", "desk_gap", 5)        # 椅子と机の間隔(mm)

# === ドア関連 ===
DOOR_WIDTH = _get("door", "width", 850)              # ドアの幅(mm)
DOOR_BUFFER_DEPTH = _get("door", "buffer_depth", 900)  # ドアバッファの奥行(mm)
DOOR_CLEAR_RADIUS = _get("door", "clear_radius", 900)  # ドア周辺の確保半径(mm)

# === 配置関連 ===
DEFAULT_DESK_DEPTH = _get("placement", "default_desk_depth", 600)     # デフォルトの机奥行(mm)
DESK_SIDE_CLEARANCE = _get("placement", "desk_side_clearance", 200)   # 机の側面クリアランス(mm)
EQUIPMENT_CLEARANCE = _get("placement", "equipment_clearance", 100)   # 設備間のクリアランス(mm)
DESK_CLEAR_RADIUS = _get("placement", "desk_clear_radius", 1225)      # 机周辺の確保半径(mm)

# === 通路関連 ===
# オフィスレイアウト設計原則に基づく通路幅
# - メイン通路: 1200mm以上 (人がすれ違える幅)
# - 最小通路: 600mm (一人通行)
# - 建築基準法: 両側居室廊下1.6m、片側1.2m
MIN_PASSAGE_WIDTH = _get("passage", "min_width", 1200)  # 最小通路幅(mm) - 人がすれ違える幅
MIN_AISLE_WIDTH = _get("passage", "min_aisle_width", 600)  # 最小通路幅(mm) - 一人通行
RECOMMENDED_PASSAGE_WIDTH = _get("passage", "recommended_width", 1500)  # 推奨通路幅(mm)

# === デスク間隔 ===
# 背中合わせのデスク間隔: 1500-1800mm (椅子の引き出し + 通路)
BACK_TO_BACK_SPACING = _get("desk_spacing", "back_to_back", 1600)  # 背中合わせ間隔(mm)
SIDE_BY_SIDE_SPACING = _get("desk_spacing", "side_by_side", 0)  # 横並び間隔(mm)

# === PDF出力関連 ===
PT_PER_MM = _get("pdf", "pt_per_mm", 72.0 / 25.4)      # 1mm = 72/25.4 pt
WALL_LINE_WIDTH = _get("pdf", "wall_line_width", 2)     # 壁線の太さ
OUTER_OFFSET_MM = _get("pdf", "outer_offset_mm", 10)    # 外枠オフセット(mm)
OUTER_LINE_WIDTH = _get("pdf", "outer_line_width", 4)   # 外枠線の太さ

# === 色定義(RGB 0-1) ===
TEXT_GRAY = _get_color("text_gray", (0.55, 0.55, 0.55))
DIM_COLOR = _get_color("dim_color", (0.5, 0.5, 0.5))
FLOOR_BASE = _get_color("floor_base", (0.85, 0.85, 0.85))
FLOOR_GRID = _get_color("floor_grid", (0.75, 0.75, 0.75))

# === グリッド ===
GRID_STEP_MM = _get("grid", "step_mm", 500)  # グリッド間隔(mm)

# === 机候補リスト ===
_ws_candidates = _config.get("ws_candidates", {})
WS_CANDIDATES_DEFAULT = _ws_candidates.get("default", ["ws_1200x600", "ws_1000x600", "ws_1200x700"])
WS_CANDIDATES_1200 = _ws_candidates.get("1200_only", ["ws_1200x600", "ws_1200x700"])


def reload_config():
    """設定を再読み込みする (テスト用)"""
    global _config
    _config = _load_config()


def get_all_config() -> Dict[str, Any]:
    """現在の設定全体を取得する"""
    return _config.copy()
