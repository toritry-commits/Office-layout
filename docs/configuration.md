# 設定ガイド

このドキュメントでは、Office-layoutのカスタマイズ方法を説明します。

## 設定ファイル一覧

| ファイル | 場所 | 用途 |
|---------|------|------|
| `config.yaml` | プロジェクトルート | システム設定、スコアリング重み |
| `catalog.json` | プロジェクトルート | 家具サイズ定義 |

---

## config.yaml

### 基本構造

```yaml
# 椅子関連
chair:
  size: 700           # 椅子のサイズ(mm)
  desk_gap: 5         # 椅子と机の間隔(mm)

# ドア関連
door:
  width: 850          # ドアの幅(mm)
  buffer_depth: 900   # ドア前の確保スペース(mm)
  clear_radius: 900   # ドア開閉半径(mm)

# 配置関連
placement:
  default_desk_depth: 600   # デフォルト机奥行(mm)
  desk_side_clearance: 200  # 机横のクリアランス(mm)
  equipment_clearance: 100  # 設備間のクリアランス(mm)

# 通路
passage:
  min_width: 1000     # 最小通路幅(mm)

# スコアリング
scoring:
  weights:
    seat_count: 1.0
    passage_width: 0.5
    ...
```

### セクション詳細

#### chair (椅子設定)

| キー | 型 | デフォルト | 説明 |
|-----|---|-----------|------|
| `size` | int | 700 | 椅子の一辺サイズ (正方形) |
| `desk_gap` | int | 5 | 机と椅子の間隔 |

**カスタマイズ例:**
```yaml
chair:
  size: 600    # コンパクトな椅子に変更
  desk_gap: 10 # 間隔を広めに
```

#### door (ドア設定)

| キー | 型 | デフォルト | 説明 |
|-----|---|-----------|------|
| `width` | int | 850 | ドアの幅 |
| `buffer_depth` | int | 900 | ドア前に確保するスペース |
| `clear_radius` | int | 900 | ドア開閉時に必要な半径 |

**カスタマイズ例:**
```yaml
door:
  width: 900       # 幅広ドア
  buffer_depth: 1200  # 車椅子対応で広めに
```

#### placement (配置設定)

| キー | 型 | デフォルト | 説明 |
|-----|---|-----------|------|
| `default_desk_depth` | int | 600 | 机タイプが不明な場合のデフォルト奥行 |
| `desk_side_clearance` | int | 200 | 机の横に確保するスペース |
| `equipment_clearance` | int | 100 | 設備間の最小間隔 |
| `desk_clear_radius` | int | 1225 | 机周辺の確保半径 |

#### passage (通路設定)

| キー | 型 | デフォルト | 説明 |
|-----|---|-----------|------|
| `min_width` | int | 1000 | 最小通路幅 (消防法基準) |

#### pdf (PDF出力設定)

| キー | 型 | デフォルト | 説明 |
|-----|---|-----------|------|
| `wall_line_width` | int | 2 | 壁線の太さ |
| `outer_offset_mm` | int | 10 | 外枠オフセット |
| `outer_line_width` | int | 4 | 外枠線の太さ |

#### colors (色設定)

RGB値を0.0-1.0で指定:

```yaml
colors:
  text_gray: [0.55, 0.55, 0.55]   # テキスト色
  dim_color: [0.5, 0.5, 0.5]     # 寸法線色
  floor_base: [0.85, 0.85, 0.85] # 床ベース色
  floor_grid: [0.75, 0.75, 0.75] # グリッド色
```

#### grid (グリッド設定)

| キー | 型 | デフォルト | 説明 |
|-----|---|-----------|------|
| `step_mm` | int | 500 | グリッド間隔 |

#### ws_candidates (机候補)

```yaml
ws_candidates:
  default: ["ws_1200x600", "ws_1000x600", "ws_1200x700"]
  1200_only: ["ws_1200x600", "ws_1200x700"]
```

---

### スコアリング設定

#### 重み (weights)

各評価項目の重要度を設定:

```yaml
scoring:
  weights:
    seat_count: 1.0        # 席数の重み
    passage_width: 0.5     # 通路幅の重み
    natural_light: 0.3     # 採光の重み
    traffic_flow: 0.4      # 動線効率の重み
    face_to_face_bonus: 0.2 # 対面配置ボーナス
    space_efficiency: 0.3  # スペース効率の重み
```

**調整例:**
- 席数を最優先: `seat_count: 2.0`, 他を `0.3` 以下
- 快適性重視: `passage_width: 1.0`, `natural_light: 1.0`

#### プリセット (presets)

用途別の重み設定を定義:

```yaml
scoring:
  presets:
    max_seats:        # 席数最大化
      seat_count: 2.0
      passage_width: 0.3
      ...

    comfort:          # 快適性重視
      seat_count: 0.5
      passage_width: 1.0
      natural_light: 1.0
      ...

    collaboration:    # コミュニケーション重視
      seat_count: 0.8
      face_to_face_bonus: 1.0
      traffic_flow: 1.0
      ...

    balanced:         # バランス型
      seat_count: 1.0
      passage_width: 0.5
      ...
```

**コードでの使用:**
```python
from scoring import load_scoring_weights

# プリセット読み込み
weights = load_scoring_weights("comfort")
```

---

## catalog.json

### 基本構造

```json
{
  "desks": { ... },
  "storage": { ... },
  "equipment": { ... },
  "meeting": { ... },
  "chairs": { ... }
}
```

### desks (デスク定義)

```json
{
  "desks": {
    "ws_1200x600": {
      "name": "標準デスク 1200x600",
      "w": 1200,           // 幅 (mm)
      "d": 600,            // 奥行 (mm)
      "chair_space": 600,  // 椅子用スペース
      "unit_d": 1200       // ユニット奥行 (机+椅子)
    }
  }
}
```

**新しいデスクを追加:**
```json
{
  "desks": {
    "ws_1400x700": {
      "name": "ワイドデスク 1400x700",
      "w": 1400,
      "d": 700,
      "chair_space": 600,
      "unit_d": 1300
    }
  }
}
```

### storage (収納定義)

```json
{
  "storage": {
    "storage_M": {
      "name": "収納キャビネット M",
      "w": 900,            // 幅
      "d": 450,            // 奥行
      "clear_front": 600   // 前方に必要な空間
    }
  }
}
```

### equipment (OA機器定義)

```json
{
  "equipment": {
    "mfp": {
      "name": "複合機",
      "w": 600,
      "d": 650,
      "clear_front": 900   // 操作スペース
    }
  }
}
```

### meeting (会議スペース定義)

```json
{
  "meeting": {
    "meet4p": {
      "name": "4人用打合せスペース",
      "w": 1200,
      "d": 900,
      "clear_front": 800
    }
  }
}
```

---

## カスタマイズ手順

### 1. 新しい机サイズを追加

1. `catalog.json` を開く
2. `desks` セクションに新しいエントリを追加:

```json
"ws_1500x750": {
  "name": "エグゼクティブデスク",
  "w": 1500,
  "d": 750,
  "chair_space": 700,
  "unit_d": 1450
}
```

3. `config.yaml` の `ws_candidates` に追加:

```yaml
ws_candidates:
  default: ["ws_1200x600", "ws_1000x600", "ws_1500x750"]
```

### 2. スコアリング基準を変更

1. `config.yaml` を開く
2. `scoring.weights` を編集:

```yaml
scoring:
  weights:
    seat_count: 0.8      # 席数の重要度を下げる
    passage_width: 1.2   # 通路幅を重視
```

### 3. カスタムプリセットを追加

```yaml
scoring:
  presets:
    my_custom:           # 新しいプリセット
      seat_count: 1.5
      passage_width: 0.8
      natural_light: 0.5
      traffic_flow: 0.6
      face_to_face_bonus: 0.4
      space_efficiency: 0.5
```

**使用方法:**
```python
weights = load_scoring_weights("my_custom")
```

---

## 設定の再読み込み

コード内で設定を再読み込みする場合:

```python
from constants import reload_config
from catalog import reload_catalog

# 設定を再読み込み
reload_config()
reload_catalog()
```

---

## トラブルシューティング

### config.yamlが読み込まれない

1. ファイルがプロジェクトルートにあるか確認
2. YAML構文エラーがないか確認
3. PyYAMLがインストールされているか確認:
   ```bash
   pip install pyyaml
   ```

### catalog.jsonが読み込まれない

1. JSON構文エラーがないか確認
2. ファイルパスが正しいか確認

### デフォルト値が使われる

config.yaml/catalog.jsonが見つからない場合、コード内のデフォルト値が使用されます。これは正常な動作です。
