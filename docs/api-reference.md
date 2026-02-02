# APIリファレンス

主要モジュールの関数リファレンスです。

---

## geometry.py

座標計算と衝突判定の基本機能。

### Rect

```python
@dataclass(frozen=True)
class Rect:
    x: int    # 左上X座標 (mm)
    y: int    # 左上Y座標 (mm)
    w: int    # 幅 (mm)
    d: int    # 奥行 (mm)

    @property
    def x2(self) -> int:  # 右端X座標
    @property
    def y2(self) -> int:  # 下端Y座標
```

### intersects

```python
def intersects(a: Rect, b: Rect) -> bool:
    """
    2つの矩形が重なっているか判定

    Args:
        a, b: 比較する矩形

    Returns:
        重なっていればTrue、端が接しているだけならFalse
    """
```

### inside_room

```python
def inside_room(r: Rect, room_w: int, room_d: int) -> bool:
    """
    矩形が部屋内に完全に収まっているか判定

    Args:
        r: 判定する矩形
        room_w: 部屋の幅
        room_d: 部屋の奥行

    Returns:
        部屋内ならTrue
    """
```

### can_place

```python
def can_place(r: Rect, room_w: int, room_d: int, blocks: List[Rect]) -> bool:
    """
    矩形を配置可能か判定 (部屋内かつ障害物なし)

    Args:
        r: 配置する矩形
        room_w, room_d: 部屋サイズ
        blocks: 障害物リスト

    Returns:
        配置可能ならTrue
    """
```

### check_desk_chair_collision

```python
def check_desk_chair_collision(
    desk_rect: Rect,
    chair_rect: Rect,
    blocks: List[Rect],
    room_w: int,
    room_d: int,
) -> bool:
    """
    机と椅子のペアが配置可能か判定

    Returns:
        衝突なしで配置可能ならTrue
    """
```

---

## scoring.py

レイアウト評価・比較機能。

### ScoreBreakdown

```python
@dataclass
class ScoreBreakdown:
    seat_count: float = 0.0
    passage_width: float = 0.0
    natural_light: float = 0.0
    traffic_flow: float = 0.0
    face_to_face_bonus: float = 0.0
    space_efficiency: float = 0.0
    total: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """辞書形式で取得"""
```

### load_scoring_weights

```python
def load_scoring_weights(preset: Optional[str] = None) -> Dict[str, float]:
    """
    config.yamlからスコアリングの重みを読み込む

    Args:
        preset: プリセット名 ("max_seats", "comfort", "collaboration", "balanced")
                Noneの場合はデフォルトの重みを使用

    Returns:
        重みの辞書 {"seat_count": 1.0, "passage_width": 0.5, ...}
    """
```

### calculate_layout_score

```python
def calculate_layout_score(
    result: Dict,
    room_w: int,
    room_d: int,
    weights: Optional[Dict[str, float]] = None,
    preset: Optional[str] = None,
    door_positions: Optional[List[Dict]] = None,
    max_seats: int = 20,
) -> Tuple[float, ScoreBreakdown]:
    """
    レイアウトの総合スコアを計算

    Args:
        result: レイアウト結果 (ok, seats_placed, items等を含む)
        room_w, room_d: 部屋サイズ (mm)
        weights: 各評価項目の重み (Noneでconfig.yamlから読み込み)
        preset: プリセット名
        door_positions: ドア位置リスト [{"x": int, "y": int}, ...]
        max_seats: 想定最大席数 (正規化用)

    Returns:
        (総合スコア, スコア内訳)
    """
```

### compare_layouts

```python
def compare_layouts(
    results: List[Dict],
    room_w: int,
    room_d: int,
    preset: Optional[str] = None,
) -> List[Tuple[int, float, ScoreBreakdown]]:
    """
    複数のレイアウト候補を比較してランキングを返す

    Args:
        results: レイアウト結果のリスト
        room_w, room_d: 部屋サイズ
        preset: スコアリングプリセット

    Returns:
        [(元のインデックス, スコア, 内訳), ...] スコア降順
    """
```

### get_best_layout

```python
def get_best_layout(
    results: List[Dict],
    room_w: int,
    room_d: int,
    preset: Optional[str] = None,
) -> Tuple[Optional[Dict], float, ScoreBreakdown]:
    """
    最高スコアのレイアウトを取得

    Returns:
        (最良のレイアウト結果, スコア, 内訳)
    """
```

---

## desk_chair.py

机と椅子の配置ロジック。

### calc_chair_rect

```python
def calc_chair_rect(
    desk_x: int,
    desk_y: int,
    desk_w: int,
    desk_d: int,
    chair_direction: str,
) -> Rect:
    """
    机の位置から椅子のRectを計算

    Args:
        desk_x, desk_y: 机の座標
        desk_w, desk_d: 机のサイズ
        chair_direction: 椅子の方向 ("T", "B", "L", "R")
            T=上(机の上側に椅子)、B=下、L=左、R=右

    Returns:
        椅子のRect
    """
```

### add_desk_and_chair

```python
def add_desk_and_chair(
    items: list,
    label_prefix: str,
    ws_type: str,
    desk_x: int,
    desk_y: int,
    desk_w: int,
    desk_d: int,
    chair_direction: str,
    chair_rotate_deg: int = 0,
):
    """
    机と椅子をitemsリストに追加

    Args:
        items: アイテムリスト (追加先)
        label_prefix: ラベル接頭辞 (例: "WS1")
        ws_type: 机タイプ
        desk_x, desk_y: 机の座標
        desk_w, desk_d: 机のサイズ
        chair_direction: 椅子の方向 ("T", "B", "L", "R")
        chair_rotate_deg: 椅子の回転角度 (0 or 90)
    """
```

### add_wall_desk_and_chair

```python
def add_wall_desk_and_chair(
    items: list,
    label_prefix: str,
    room_size: int,
    ws_type: str,
    wall_side: str,
    position: int,
    unit_along_wall: int,
    unit_depth: int,
    is_horizontal: bool = False,
):
    """
    壁付け机と椅子を配置

    Args:
        items: アイテムリスト
        label_prefix: ラベル接頭辞
        room_size: 部屋サイズ (壁からの計算用)
        ws_type: 机タイプ
        wall_side: 壁の位置 ("L", "R", "T", "B")
        position: 壁沿い方向の位置
        unit_along_wall: 壁沿い方向のサイズ
        unit_depth: 壁からの奥行
        is_horizontal: 水平配置か (T/Bの場合True)
    """
```

### can_place_desk_chair

```python
def can_place_desk_chair(
    room_size: int,
    room_w: int,
    room_d: int,
    ws_type: str,
    wall_side: str,
    position: int,
    unit_along_wall: int,
    unit_depth: int,
    is_horizontal: bool,
    pillar_blocks: List[Rect],
) -> bool:
    """
    壁付け机と椅子が配置可能かチェック

    Returns:
        配置可能ならTrue
    """
```

---

## catalog.py

家具カタログ管理。

### FURNITURE

```python
FURNITURE: Dict[str, Dict[str, Any]]
"""
家具情報の辞書 (catalog.jsonから読み込み)

例:
{
    "ws_1200x600": {"w": 1200, "d": 1200},
    "storage_M": {"w": 900, "d": 450, "clear_front": 600},
    ...
}
"""
```

### get_desk_info

```python
def get_desk_info(desk_type: str) -> Optional[Dict[str, Any]]:
    """
    机タイプの詳細情報を取得

    Args:
        desk_type: 机タイプ (例: "ws_1200x600")

    Returns:
        机の情報 (w, d, name等) または None
    """
```

### list_desks

```python
def list_desks() -> Dict[str, Dict[str, Any]]:
    """利用可能な全デスクを取得"""
```

### list_storage

```python
def list_storage() -> Dict[str, Dict[str, Any]]:
    """利用可能な全収納家具を取得"""
```

### reload_catalog

```python
def reload_catalog():
    """カタログを再読み込み (設定変更後に使用)"""
```

---

## constants.py

定数管理 (config.yaml対応)。

### 主要定数

```python
# 椅子関連
CHAIR_SIZE: int        # 椅子サイズ (デフォルト: 700)
CHAIR_DESK_GAP: int    # 椅子と机の間隔 (デフォルト: 5)

# ドア関連
DOOR_WIDTH: int        # ドア幅 (デフォルト: 850)
DOOR_BUFFER_DEPTH: int # ドアバッファ奥行 (デフォルト: 900)
DOOR_CLEAR_RADIUS: int # ドア確保半径 (デフォルト: 900)

# 配置関連
DEFAULT_DESK_DEPTH: int    # デフォルト机奥行 (デフォルト: 600)
DESK_SIDE_CLEARANCE: int   # 机側面クリアランス (デフォルト: 200)
MIN_PASSAGE_WIDTH: int     # 最小通路幅 (デフォルト: 1000)

# PDF出力関連
PT_PER_MM: float       # 1mm = 72/25.4 pt
WALL_LINE_WIDTH: int   # 壁線太さ (デフォルト: 2)

# 色定義 (RGB 0-1)
TEXT_GRAY: Tuple[float, float, float]
FLOOR_BASE: Tuple[float, float, float]
```

### reload_config

```python
def reload_config():
    """config.yamlを再読み込み"""
```

### get_all_config

```python
def get_all_config() -> Dict[str, Any]:
    """現在の設定全体を取得"""
```

---

## utils.py

共通ユーティリティ。

### parse_desk_depth

```python
def parse_desk_depth(ws_type: str) -> int:
    """
    机タイプから奥行を取得

    例: "ws_1000x600" -> 600
    """
```

### calc_desk_area

```python
def calc_desk_area(ws_type: str) -> int:
    """
    机タイプから面積を計算

    例: "ws_1200x600" -> 720000
    """
```

### score_layout

```python
def score_layout(result: Dict, priority: str) -> tuple:
    """
    レイアウト結果をスコア化 (比較用)

    Args:
        result: レイアウト結果
        priority: 優先項目 ("equipment", "desk", "desk_1200")

    Returns:
        比較用タプル (大きいほど良い)
    """
```

### parse_equipment

```python
def parse_equipment(equip_str: str) -> List[str]:
    """
    設備文字列をリストに変換

    例: "storage_M,storage_M,mfp" -> ["storage_M", "storage_M", "mfp"]
    """
```

---

## export_pdf.py

PDF出力機能。

### export_layout_pdf

```python
def export_layout_pdf(
    out_path: str,
    room_w: int,
    room_d: int,
    items: list,
    title: str = "",
    label_w: int = None,
    label_d: int = None,
):
    """
    レイアウトをPDFで出力

    Args:
        out_path: 出力ファイルパス
        room_w, room_d: 部屋サイズ
        items: レイアウトアイテムリスト
        title: タイトル
        label_w, label_d: 寸法ラベル用サイズ
    """
```

### export_multi_layout_pdf

```python
def export_multi_layout_pdf(
    out_path: str,
    room_w: int,
    room_d: int,
    pages: list,
    label_w: int = None,
    label_d: int = None,
):
    """
    複数ページのPDFを出力

    Args:
        pages: [{"title": str, "items": list}, ...]
    """
```

---

## export_svg.py

SVG出力機能 (Streamlit表示用)。

### render_layout_svg

```python
def render_layout_svg(
    room_w: int,
    room_d: int,
    items: list,
    title: str = "",
    width_px: int = 600,
) -> str:
    """
    レイアウトをSVG文字列として返す

    Args:
        room_w, room_d: 部屋サイズ
        items: レイアウトアイテムリスト
        title: タイトル
        width_px: SVG幅 (ピクセル)

    Returns:
        SVG文字列
    """
```

---

## export_data.py

データ出力機能。

### export_layout_json

```python
def export_layout_json(
    out_path: str,
    room_w: int,
    room_d: int,
    pages: list,
):
    """
    レイアウトをJSONで出力

    Args:
        out_path: 出力ファイルパス
        room_w, room_d: 部屋サイズ
        pages: [{"title": str, "items": list}, ...]
    """
```

### export_layout_csv

```python
def export_layout_csv(out_path: str, pages: list):
    """
    レイアウトをCSVで出力 (1行=1アイテム)
    """
```

---

## app.py

メインロジック。

### build_blocks

```python
def build_blocks(
    room_w: int,
    room_d: int,
    door_w: int,
    door_d: int,
    door_side: str,
    door_offset: Optional[int],
    pillars: List[Dict] = None,
) -> Tuple[List[Rect], Rect, str, int]:
    """
    配置禁止ブロックとドア情報を構築

    Returns:
        (blocks, door_rect, door_side, door_tip)
    """
```

### solve_one_plan

```python
def solve_one_plan(
    room_w: int,
    room_d: int,
    seats_required: int,
    ws_candidates: List[str],
    blocks: List[Rect],
    equipment: List[str],
    equipment_x_override: Optional[int],
    door_side: str,
    door_offset: Optional[int],
    priority: str,
    door_tip: int,
) -> Dict[str, Any]:
    """
    1つのレイアウトプランを計算

    Returns:
        レイアウト結果
    """
```
