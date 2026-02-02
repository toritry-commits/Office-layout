# Office-layout 設計仕様書

## 概要

Office-layoutは、オフィスの部屋サイズと必要席数を入力すると、最適な家具配置を自動計算するツールです。

## システム構成

```
+------------------+     +------------------+     +------------------+
|   UI Layer       |     |   Core Logic     |     |   Output Layer   |
+------------------+     +------------------+     +------------------+
| streamlit_app.py |---->| app.py           |---->| export_pdf.py    |
| (Web UI)         |     | patterns.py      |     | export_svg.py    |
|                  |     | scoring.py       |     | export_data.py   |
| cli_generate.py  |     +------------------+     +------------------+
| (CLI)            |            |
+------------------+            v
                       +------------------+
                       |   Data Layer     |
                       +------------------+
                       | config.yaml      |
                       | catalog.json     |
                       | constants.py     |
                       | catalog.py       |
                       +------------------+
```

## モジュール構成

### UIレイヤー

| ファイル | 役割 |
|---------|------|
| `streamlit_app.py` | Webブラウザ用インターフェース |
| `cli_generate.py` | コマンドライン実行用スクリプト |
| `app.py` | CLI版メインロジック (argparse対応) |

### コアロジック

| ファイル | 役割 |
|---------|------|
| `patterns.py` | 配置パターン計算 (壁付け、対面、片壁) |
| `geometry.py` | 座標計算、衝突判定、矩形操作 |
| `desk_chair.py` | 机と椅子のセット配置ロジック |
| `scoring.py` | レイアウト評価・比較機能 |
| `utils.py` | 共通ユーティリティ関数 |

### データレイヤー

| ファイル | 役割 |
|---------|------|
| `config.yaml` | システム設定 (定数、スコアリング重み) |
| `catalog.json` | 家具カタログ (サイズ定義) |
| `constants.py` | config.yaml読み込み、定数提供 |
| `catalog.py` | catalog.json読み込み、家具情報提供 |

### 出力レイヤー

| ファイル | 役割 |
|---------|------|
| `export_pdf.py` | PDF図面出力 (ReportLab使用) |
| `export_svg.py` | SVG画像出力 (Streamlit表示用) |
| `export_data.py` | JSON/CSV出力 |

---

## データ構造

### 座標系

```
(0,0) ────────────────────> X (幅方向)
  │
  │    +--------+
  │    |  部屋  |
  │    +--------+
  │
  v
  Y (奥行方向)
```

- 単位: mm (ミリメートル)
- 原点: 左上
- X軸: 右方向が正
- Y軸: 下方向が正

### Rect (矩形) 構造

```python
@dataclass(frozen=True)
class Rect:
    x: int    # 左上X座標 (mm)
    y: int    # 左上Y座標 (mm)
    w: int    # 幅 (mm)
    d: int    # 奥行 (mm)
```

### レイアウト結果 (result dict)

```python
{
    "ok": bool,              # 配置成功フラグ
    "seats_placed": int,     # 配置した席数
    "equipment_placed": int, # 配置した設備数
    "ws_type": str,          # 使用した机タイプ
    "pattern": str,          # パターン名
    "items": [               # 配置アイテムリスト
        {
            "type": "desk" | "chair" | "storage_M" | "mfp" | ...,
            "rect": Rect,
            "label": str,
            "chair_back": "T" | "B" | "L" | "R",  # 椅子のみ
        },
        ...
    ]
}
```

---

## 配置アルゴリズム

### 1. 壁付け配置 (Wall Placement)

```
+---------------------------+
|  [D][D][D]      [D][D][D] |  <- 左右壁に机を配置
|  [C][C][C]      [C][C][C] |  <- 椅子は壁と反対側
|                           |
|         [通路]            |
|                           |
|  [C][C][C]      [C][C][C] |
|  [D][D][D]      [D][D][D] |
+---------------------------+
      D=机, C=椅子
```

**処理フロー:**
1. ドア位置から配置禁止エリアを計算
2. 左壁から可能な限り机を配置
3. 右壁から可能な限り机を配置
4. 椅子を各机の内側に配置
5. 設備を空きスペースに配置

### 2. 対面配置 (Face-to-Face)

```
+---------------------------+
|                           |
|      [D][D][D][D]         |  <- 上段机 (椅子は上)
|      [C][C][C][C]         |
|                           |
|      [C][C][C][C]         |  <- 下段椅子
|      [D][D][D][D]         |  <- 下段机
|                           |
+---------------------------+
```

**処理フロー:**
1. 部屋中央に対面ユニットを配置
2. 必要席数に応じて横に拡張
3. ドアとの干渉をチェック
4. 設備を周囲に配置

### 3. 片壁配置 (Single Wall)

```
+---------------------------+
|  [D][D][D][D][D]          |  <- 片側壁のみ使用
|  [C][C][C][C][C]          |
|                           |
|      [広い通路]           |
|                           |
+---------------------------+
```

---

## スコアリングシステム

### 評価項目

| 項目 | 説明 | 重み (デフォルト) |
|------|------|------------------|
| seat_count | 席数の多さ | 1.0 |
| passage_width | 通路の広さ | 0.5 |
| natural_light | 採光 (窓からの距離) | 0.3 |
| traffic_flow | 動線効率 | 0.4 |
| face_to_face_bonus | 対面配置ボーナス | 0.2 |
| space_efficiency | スペース効率 | 0.3 |

### プリセット

| プリセット名 | 用途 |
|-------------|------|
| `max_seats` | 席数最大化 |
| `comfort` | 快適性重視 |
| `collaboration` | コミュニケーション重視 |
| `balanced` | バランス型 |

### スコア計算式

```
総合スコア = Σ (各項目スコア × 重み)

各項目スコア = 0.0 ~ 1.0 に正規化
```

---

## 衝突判定

### 判定フロー

```
配置可能? = 部屋内チェック AND 柱・障害物チェック

1. inside_room(rect, room_w, room_d)
   - rect.x >= 0
   - rect.y >= 0
   - rect.x + rect.w <= room_w
   - rect.y + rect.d <= room_d

2. intersects_any(rect, blocks)
   - 全てのblockと重なりがないか
```

### 衝突判定 (intersects)

```
重なっている = NOT (
    a.x2 <= b.x OR   # aがbの左側
    a.x >= b.x2 OR   # aがbの右側
    a.y2 <= b.y OR   # aがbの上側
    a.y >= b.y2      # aがbの下側
)
```

---

## 定数・設定値

### 椅子関連 (config.yaml: chair)

| 項目 | デフォルト値 | 説明 |
|------|-------------|------|
| size | 700mm | 椅子サイズ (正方形) |
| desk_gap | 5mm | 机と椅子の間隔 |

### ドア関連 (config.yaml: door)

| 項目 | デフォルト値 | 説明 |
|------|-------------|------|
| width | 850mm | ドア幅 |
| buffer_depth | 900mm | ドアバッファ奥行 |
| clear_radius | 900mm | ドア開閉確保半径 |

### 配置関連 (config.yaml: placement)

| 項目 | デフォルト値 | 説明 |
|------|-------------|------|
| default_desk_depth | 600mm | デフォルト机奥行 |
| desk_side_clearance | 200mm | 机側面クリアランス |
| min_passage_width | 1000mm | 最小通路幅 |

---

## 家具カタログ (catalog.json)

### デスク定義

```json
{
  "ws_1200x600": {
    "name": "標準デスク 1200x600",
    "w": 1200,        // 幅
    "d": 600,         // 奥行
    "chair_space": 600,  // 椅子スペース
    "unit_d": 1200    // ユニット奥行 (机+椅子)
  }
}
```

### 収納定義

```json
{
  "storage_M": {
    "name": "収納キャビネット M",
    "w": 900,
    "d": 450,
    "clear_front": 600  // 前方必要スペース
  }
}
```

---

## 拡張ポイント

### 新しい配置パターンを追加する

1. `patterns.py` に新しい関数を追加
2. `app.py` の `solve_one_plan` から呼び出し
3. `streamlit_app.py` のUI選択肢に追加

### 新しい家具タイプを追加する

1. `catalog.json` に定義を追加
2. `export_pdf.py` と `export_svg.py` に描画ロジック追加

### スコアリング基準を追加する

1. `scoring.py` に `_calc_xxx_score` 関数を追加
2. `config.yaml` の weights に項目追加
3. `calculate_layout_score` で計算に組み込み

---

## 既知の制限事項

1. **L字型部屋非対応**: 矩形部屋のみ対応
2. **複数ドア非対応**: ドアは1つのみ
3. **家具回転制限**: 90度単位の回転のみ
4. **窓位置固定**: 採光計算は上辺・右辺を窓と仮定

---

## バージョン履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0 | - | 初期リリース |
| 1.1 | - | config.yaml/catalog.json外部化対応 |
| 1.2 | - | スコアリング機能追加 |
