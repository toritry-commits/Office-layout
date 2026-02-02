# Office-layout

オフィスのレイアウト (机や収納の配置) を自動で計算・提案するツールです。

## このツールでできること

- 部屋のサイズと必要な席数を入力するだけで、最適なレイアウト案を自動生成
- 複数のパターン (壁付け配置、対面配置、混在配置など) を比較検討
- 柱や凹凸を避けた自動配置 (ドラッグ&ドロップで配置可能)
- 窓の位置を指定して採光を考慮
- 最大50m x 50mの大規模オフィスに対応
- スコアリング機能で最適なレイアウトを選択
- PDF、JSON、CSV、SVG形式で出力
- 設定ファイルで家具サイズや評価基準をカスタマイズ可能

## 必要な環境

- Python 3.10以上
- 以下のライブラリ (後述のインストール手順で自動導入)

## インストール方法

```bash
# 1. リポジトリをクローン (ダウンロード)
git clone https://github.com/toritry-commits/Office-layout.git
cd Office-layout

# 2. 必要なライブラリをインストール
pip install -r requirements.txt
```

## 使い方

### Webアプリ版 (おすすめ)

ブラウザで操作できる画面が開きます。

```bash
streamlit run src/streamlit_app.py
```

**操作手順:**
1. 部屋の横幅・縦幅 (mm) を入力
2. 入口の位置を選択
3. 必要に応じて柱や凹凸を追加
4. 座席数・収納数を指定
5. 「レイアウト生成」ボタンをクリック
6. PDF等をダウンロード

### コマンドライン版

```bash
# 基本的な使い方
python src/app.py --w 5000 --d 4000 --seats 8

# 収納や複合機も配置する場合
python src/app.py --w 5000 --d 4000 --seats 8 --equip "storage_M,storage_M,mfp"

# 入口位置を指定 (L=左, R=右, T=上, B=下)
python src/app.py --w 5000 --d 4000 --seats 10 --door-side L --door-offset 1500
```

**主なオプション:**

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--w` | 部屋の横幅 (mm) | `--w 5000` |
| `--d` | 部屋の奥行 (mm) | `--d 4000` |
| `--seats` | 必要な席数 | `--seats 8` |
| `--equip` | 設備リスト | `--equip "storage_M,mfp"` |
| `--door-side` | 入口位置 (T/B/L/R) | `--door-side L` |
| `--priority` | 優先項目 | `--priority equipment` |

## 出力ファイル

| ファイル | 内容 |
|---------|------|
| `layout_3plans.pdf` | レイアウト図面 (A3サイズ) |
| `layout_3plans.json` | 配置データ (座標情報) |
| `layout_3plans.csv` | 配置データ (表形式) |

## ファイル構成

```
Office-layout/
├── config.yaml             # 設定ファイル (定数、スコアリング重み)
├── catalog.json            # 家具カタログ (サイズ定義)
├── requirements.txt        # 依存ライブラリ
├── README.md               # このファイル
├── src/                    # ソースコード
│   ├── streamlit_app.py    # Webアプリ版メイン
│   ├── app.py              # コマンドライン版メイン
│   ├── patterns.py         # レイアウト計算ロジック
│   ├── scoring.py          # スコアリング機能
│   ├── geometry.py         # 座標計算ユーティリティ
│   ├── desk_chair.py       # 机椅子配置ロジック
│   ├── constants.py        # 定数管理 (config.yaml対応)
│   ├── catalog.py          # 家具カタログ管理 (JSON対応)
│   ├── utils.py            # 共通ユーティリティ
│   ├── export_pdf.py       # PDF出力
│   ├── export_svg.py       # SVG出力
│   ├── export_data.py      # JSON/CSV出力
│   ├── cli_generate.py     # CLIスクリプト
│   ├── extract_room_size.py # PDF図面解析 (オプション)
│   └── debug_layout.py     # デバッグ用
├── output/                 # 生成された出力ファイル
├── docs/                   # ドキュメント
│   ├── architecture.md     # 設計仕様書
│   ├── configuration.md    # 設定ガイド
│   ├── api-reference.md    # APIリファレンス
│   └── development.md      # 開発ガイド
└── samples/                # サンプルファイル
```

## レイアウトパターン

このツールは以下のパターンを自動計算します:

| パターン | 説明 | 特徴 |
|---------|------|------|
| **両壁配置** | 左右の壁に沿って机を配置 | 席数重視 |
| **対面配置** | 机を向かい合わせに配置 | コミュニケーション重視 |
| **片壁配置** | 片側の壁のみに配置 | 通路確保 |
| **混在配置** | 壁沿い + 対面を組み合わせ | 柔軟なレイアウト |

## カスタマイズ

### 家具サイズの変更

`catalog.json` を編集して、新しい机サイズを追加できます:

```json
{
  "desks": {
    "ws_1400x700": {
      "name": "ワイドデスク",
      "w": 1400,
      "d": 700,
      "chair_space": 600,
      "unit_d": 1300
    }
  }
}
```

### スコアリング基準の変更

`config.yaml` の `scoring.weights` で評価基準を調整できます:

```yaml
scoring:
  weights:
    seat_count: 1.0        # 席数の重み
    passage_width: 0.5     # 通路幅の重み
    natural_light: 0.3     # 採光の重み
    traffic_flow: 0.4      # 動線効率の重み
```

### プリセット

用途に応じた重み設定のプリセットが用意されています:

| プリセット名 | 用途 |
|-------------|------|
| `max_seats` | 席数最大化 |
| `comfort` | 快適性重視 (通路・採光) |
| `collaboration` | コミュニケーション重視 (対面・動線) |
| `balanced` | バランス型 (デフォルト) |

詳細は [docs/configuration.md](docs/configuration.md) を参照してください。

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [デザイン仕様書](docs/design-spec.md) | 座標系、家具サイズ、配置制約、出力形式 |
| [設計仕様書](docs/architecture.md) | システム構成、データ構造、アルゴリズム |
| [設定ガイド](docs/configuration.md) | config.yaml、catalog.jsonのカスタマイズ方法 |
| [APIリファレンス](docs/api-reference.md) | 関数・クラスの詳細 |
| [開発ガイド](docs/development.md) | 開発環境構築、コーディング規約 |

## 技術仕様

| 項目 | 値 |
|-----|-----|
| 単位 | ミリメートル (mm) |
| 座標系 | 左上原点、X右方向、Y下方向 |
| 部屋サイズ | 最小 2000mm x 2000mm、最大 50000mm x 50000mm |
| ドアクリアランス | 900mm (対面配置時は200mmに緩和) |
| 椅子サイズ | 700mm x 700mm |
| 椅子引きしろ | 600mm |

詳細は [デザイン仕様書](docs/design-spec.md) を参照してください。

## 今後の拡張予定

- L字型部屋対応
- 複数ドア対応
- 遺伝的アルゴリズムによる最適化
- 3Dビュー出力

## ライセンス

MIT License

## 貢献

バグ報告や機能提案は Issue でお願いします。
