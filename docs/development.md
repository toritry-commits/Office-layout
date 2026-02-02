# 開発ガイド

このドキュメントでは、Office-layoutの開発環境構築と開発手順を説明します。

## 開発環境構築

### 必要なソフトウェア

- Python 3.10以上
- Git
- (推奨) VS Code または PyCharm

### セットアップ手順

```bash
# 1. リポジトリをクローン
git clone https://github.com/toritry-commits/Office-layout.git
cd Office-layout

# 2. 仮想環境を作成 (推奨)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. 依存関係をインストール
pip install -r requirements.txt

# 4. 動作確認
streamlit run src/streamlit_app.py
```

### オプション依存関係

PDF図面から部屋サイズを抽出する機能を使う場合:

```bash
pip install pdfplumber pymupdf

# OCR機能も使う場合 (Tesseractが必要)
pip install pytesseract
```

---

## プロジェクト構造

```
Office-layout/
├── src/                    # ソースコード
│   ├── app.py              # CLIメインロジック
│   ├── streamlit_app.py    # WebUI
│   ├── patterns.py         # 配置アルゴリズム
│   ├── geometry.py         # 座標計算
│   ├── desk_chair.py       # 机椅子配置
│   ├── scoring.py          # スコアリング
│   ├── constants.py        # 定数管理
│   ├── catalog.py          # 家具カタログ
│   ├── utils.py            # ユーティリティ
│   ├── export_pdf.py       # PDF出力
│   ├── export_svg.py       # SVG出力
│   ├── export_data.py      # JSON/CSV出力
│   ├── cli_generate.py     # CLIスクリプト
│   ├── extract_room_size.py # PDF解析
│   └── debug_layout.py     # デバッグ用
├── docs/                   # ドキュメント
├── output/                 # 出力ファイル
├── samples/                # サンプル
├── config.yaml             # 設定ファイル
├── catalog.json            # 家具カタログ
├── requirements.txt        # 依存関係
└── README.md
```

---

## 開発フロー

### 1. 新機能の追加

```
1. featureブランチを作成
   git checkout -b feature/new-feature

2. コードを実装

3. 動作確認
   streamlit run src/streamlit_app.py

4. コミット
   git add .
   git commit -m "Add new feature"

5. プッシュ & PR作成
   git push origin feature/new-feature
```

### 2. デバッグ

```bash
# デバッグスクリプトを実行
python src/debug_layout.py

# 特定のテストケースを実行
python src/cli_generate.py
```

### 3. ログ出力

`app.py` ではloggingモジュールを使用:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("配置開始")
logger.debug(f"部屋サイズ: {room_w} x {room_d}")
logger.warning("席数が不足")
logger.error("配置失敗")
```

ログレベル変更:
```python
logging.basicConfig(level=logging.DEBUG)
```

---

## コーディング規約

### 命名規則

| 種類 | 規則 | 例 |
|------|------|-----|
| 変数・関数 | snake_case | `room_width`, `calc_score()` |
| 定数 | UPPER_SNAKE_CASE | `CHAIR_SIZE`, `MIN_PASSAGE_WIDTH` |
| クラス | PascalCase | `Rect`, `ScoreBreakdown` |
| プライベート | 先頭に`_` | `_load_config()`, `_calc_area()` |

### コメント

- 日本語でOK
- 関数にはdocstringを付ける:

```python
def calc_chair_rect(desk_x: int, desk_y: int, ...) -> Rect:
    """
    机の位置から椅子のRectを計算する

    Args:
        desk_x, desk_y: 机の座標
        ...

    Returns:
        椅子のRect
    """
```

### 型ヒント

可能な限り型ヒントを付ける:

```python
from typing import List, Dict, Optional, Tuple

def solve_one_plan(
    room_w: int,
    room_d: int,
    seats_required: int,
    ws_candidates: List[str],
    blocks: List[Rect],
) -> Dict[str, Any]:
    ...
```

---

## モジュール解説

### geometry.py

座標計算の基本:

```python
from geometry import Rect, intersects, inside_room, can_place

# 矩形作成
desk = Rect(x=0, y=0, w=1200, d=600)

# 衝突判定
if intersects(desk, pillar):
    print("衝突!")

# 部屋内チェック
if inside_room(desk, room_w, room_d):
    print("部屋内")

# 配置可能チェック (部屋内 + 障害物なし)
if can_place(desk, room_w, room_d, blocks):
    print("配置OK")
```

### patterns.py

配置パターン関数:

```python
from patterns import (
    place_workstations_double_wall,
    place_workstations_double_wall_top_bottom,
    place_workstations_single_wall,
    place_workstations_single_wall_tb,
    place_workstations_face_to_face_center,
    place_workstations_mixed,
    place_equipment_along_wall,
)

# 対面配置
result = place_workstations_face_to_face_center(
    room_w=5000,
    room_d=4000,
    furniture=FURNITURE,
    ws_type="ws_1200x600",
    seats_required=8,
    blocks=blocks,
    ...
)

# 混在配置 (壁沿い + 対面)
result = place_workstations_mixed(
    room_w=6000,
    room_d=5000,
    furniture=FURNITURE,
    ws_type="ws_1200x600",
    seats_required=10,
    blocks=blocks,
    wall_seats=4,      # 壁沿い4席
    wall_side="L",     # 左壁に配置
    ...
)

# 設備配置
result = place_equipment_along_wall(
    base_result=result,
    room_w=5000,
    room_d=4000,
    furniture=FURNITURE,
    equipment_list=["storage_M", "mfp"],
    ...
)
```

### scoring.py

レイアウト評価:

```python
from scoring import (
    calculate_layout_score,
    compare_layouts,
    get_best_layout,
    load_scoring_weights,
)

# スコア計算
score, breakdown = calculate_layout_score(
    result=layout_result,
    room_w=5000,
    room_d=4000,
    preset="balanced",
)

print(f"総合スコア: {score}")
print(f"内訳: {breakdown.to_dict()}")

# 複数レイアウト比較
ranking = compare_layouts(results, room_w, room_d, preset="max_seats")

# 最良レイアウト取得
best, score, breakdown = get_best_layout(results, room_w, room_d)
```

### desk_chair.py

机椅子の配置:

```python
from desk_chair import (
    add_desk_and_chair,
    add_wall_desk_and_chair,
    add_free_desk_and_chair,
    calc_chair_rect,
    can_place_desk_chair,
)

# 机と椅子を追加 (壁付け)
add_wall_desk_and_chair(
    items=items,
    label_prefix="WS1",
    ws_type="ws_1200x600",
    x=0,
    y=0,
    desk_w=1200,
    unit_depth=1200,
    wall_side="L",  # 左壁に沿って配置
)

# 机と椅子を追加 (自由配置)
add_free_desk_and_chair(
    items=items,
    label_prefix="WS1",
    ws_type="ws_1200x600",
    x=1000,
    y=1000,
    desk_w=1200,
    unit_depth=1200,
    chair_side="down",  # 椅子は下側
)

# 配置可能チェック (柱回避)
if can_place_desk_chair(desk_rect, chair_rect, room_w, room_d, blocks):
    print("配置OK")
```

---

## テスト方法

### 手動テスト

```bash
# Webアプリで動作確認
streamlit run src/streamlit_app.py

# CLIで動作確認
python src/cli_generate.py
```

### 自動テスト

```bash
# 機能テスト (柱回避、収納配置、混在パターン等)
python src/test_improvements.py
```

テスト項目:
- 柱を避けた机・椅子の配置
- 机と椅子の間隔 (CHAIR_DESK_GAP=5mm)
- 収納配置ロジック
- 大きな間取り対応 (50m x 50m)
- 混在パターン (壁沿い + 対面)
- 椅子の境界チェック (部屋外に出ないこと)

### デバッグスクリプト

```bash
# 対面配置のデバッグ
python src/debug_layout.py
```

### インポートテスト

```bash
python -c "from src.scoring import calculate_layout_score; print('OK')"
python -c "from src.constants import CHAIR_SIZE; print(f'CHAIR_SIZE={CHAIR_SIZE}')"
```

---

## よくある問題と解決法

### ImportError: No module named 'xxx'

```bash
# 依存関係を再インストール
pip install -r requirements.txt

# 仮想環境が有効か確認
which python  # macOS/Linux
where python  # Windows
```

### Streamlitが起動しない

```bash
# ポートが使用中の場合
streamlit run src/streamlit_app.py --server.port 8502
```

### PDF出力で日本語が文字化け

ReportLabのCIDフォント問題。`export_pdf.py`で`HeiseiKakuGo-W5`を使用していますが、環境によっては表示されない場合があります。

### config.yamlの変更が反映されない

Pythonモジュールはインポート時に設定を読み込むため、変更後は再起動が必要:

```python
# または、明示的に再読み込み
from constants import reload_config
reload_config()
```

---

## 今後の拡張案

### 優先度: 高

1. **L字型部屋対応**: 複数矩形の組み合わせで表現
2. **複数ドア対応**: ドアリストを引数で受け取る
3. **ユニットテスト追加**: pytest導入

### 優先度: 中

1. **遺伝的アルゴリズム導入**: より最適な配置探索
2. **3Dビュー出力**: Three.js連携
3. **配置制約の追加**: 「この人は窓際」など

### 優先度: 低

1. **AI画像認識**: 図面画像から自動読み取り
2. **複数フロア対応**: フロア間の移動考慮
3. **コスト計算**: 家具の価格も含めた最適化

---

## コントリビューション

1. Issueを確認または作成
2. featureブランチで開発
3. PRを作成
4. レビュー後マージ

質問があれば Issue で気軽にどうぞ。
