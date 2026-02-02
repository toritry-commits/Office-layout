# 家具カタログ (サイズは mm)
# catalog.jsonから読み込み、フォールバックとしてハードコード値を使用

import os
import json
from typing import Dict, Any, Optional


def _find_catalog_path() -> str:
    """catalog.jsonのパスを探す"""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    return os.path.join(project_root, "catalog.json")


def _load_catalog() -> Dict[str, Any]:
    """catalog.jsonを読み込む"""
    catalog_path = _find_catalog_path()
    if not os.path.exists(catalog_path):
        return {}

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# カタログを読み込み
_catalog = _load_catalog()

# デフォルト値 (JSONが読めない場合のフォールバック)
_DEFAULT_FURNITURE = {
    # 席ユニット (デスク + 椅子引きしろ800mm込み)
    "ws_1200x700": {"w": 1200, "d": 1300},
    "ws_1200x600": {"w": 1200, "d": 1200},
    "ws_1000x600": {"w": 1000, "d": 1200},

    # 収納 (混在しても扱えるように、3クラスで吸収)
    "storage_S": {"w": 900, "d": 350, "clear_front": 600},
    "storage_M": {"w": 900, "d": 450, "clear_front": 600},
    "storage_D": {"w": 900, "d": 600, "clear_front": 600},

    # 複合機 (前に立つスペースを広めに)
    "mfp": {"w": 600, "d": 650, "clear_front": 900},

    # 2人打合せ (MVPは前方600確保でOK)
    "meet2p": {"w": 750, "d": 750, "clear_front": 600},
}


def _build_furniture_dict() -> Dict[str, Dict[str, Any]]:
    """
    JSONカタログからFURNITURE辞書を構築
    既存コードとの互換性を維持するため、フラットな辞書形式に変換
    """
    if not _catalog:
        return _DEFAULT_FURNITURE.copy()

    result = {}

    # デスク
    for key, data in _catalog.get("desks", {}).items():
        if key.startswith("_"):
            continue
        result[key] = {
            "w": data.get("w", 1200),
            "d": data.get("unit_d", data.get("d", 1200) + 600),  # unit_dがあればそれを使用
        }

    # 収納
    for key, data in _catalog.get("storage", {}).items():
        if key.startswith("_"):
            continue
        result[key] = {
            "w": data.get("w", 900),
            "d": data.get("d", 450),
            "clear_front": data.get("clear_front", 600),
        }

    # OA機器
    for key, data in _catalog.get("equipment", {}).items():
        if key.startswith("_"):
            continue
        result[key] = {
            "w": data.get("w", 600),
            "d": data.get("d", 600),
            "clear_front": data.get("clear_front", 900),
        }

    # 会議スペース
    for key, data in _catalog.get("meeting", {}).items():
        if key.startswith("_"):
            continue
        result[key] = {
            "w": data.get("w", 750),
            "d": data.get("d", 750),
            "clear_front": data.get("clear_front", 600),
        }

    # 結果が空の場合はデフォルト値を使用
    if not result:
        return _DEFAULT_FURNITURE.copy()

    return result


# 既存コードとの互換性を維持するためのFURNITURE辞書
FURNITURE = _build_furniture_dict()


def get_desk_info(desk_type: str) -> Optional[Dict[str, Any]]:
    """
    机タイプの詳細情報を取得

    Args:
        desk_type: 机タイプ (例: "ws_1200x600")

    Returns:
        机の情報 (w, d, name等) または None
    """
    desks = _catalog.get("desks", {})
    return desks.get(desk_type)


def get_furniture_info(furniture_type: str) -> Optional[Dict[str, Any]]:
    """
    家具タイプの情報を取得

    Args:
        furniture_type: 家具タイプ

    Returns:
        家具の情報または None
    """
    return FURNITURE.get(furniture_type)


def list_desks() -> Dict[str, Dict[str, Any]]:
    """利用可能な全デスクを取得"""
    desks = _catalog.get("desks", {})
    return {k: v for k, v in desks.items() if not k.startswith("_")}


def list_storage() -> Dict[str, Dict[str, Any]]:
    """利用可能な全収納家具を取得"""
    storage = _catalog.get("storage", {})
    return {k: v for k, v in storage.items() if not k.startswith("_")}


def list_equipment() -> Dict[str, Dict[str, Any]]:
    """利用可能な全OA機器を取得"""
    equipment = _catalog.get("equipment", {})
    return {k: v for k, v in equipment.items() if not k.startswith("_")}


def list_meeting() -> Dict[str, Dict[str, Any]]:
    """利用可能な全会議スペースを取得"""
    meeting = _catalog.get("meeting", {})
    return {k: v for k, v in meeting.items() if not k.startswith("_")}


def reload_catalog():
    """カタログを再読み込みする (テスト用)"""
    global _catalog, FURNITURE
    _catalog = _load_catalog()
    FURNITURE = _build_furniture_dict()
