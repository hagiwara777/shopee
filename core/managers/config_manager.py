"""
閾値調整・設定管理システム (config_manager.py)

責任:
- 分類閾値の動的管理
- 設定ファイルの読み込み・保存
- 設定変更履歴の記録
- プリセット管理

設計原則:
- Single Responsibility Principle準拠
- 設定変更の安全性確保
- 履歴管理による追跡可能性
"""

import json
import pathlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
import copy

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThresholdConfigManager:
    """閾値・設定管理システムのメインクラス"""
    
    def __init__(self, data_dir: Optional[pathlib.Path] = None):
        """
        ThresholdConfigManagerの初期化
        
        Args:
            data_dir: データディレクトリのパス（Noneの場合は自動検出）
        """
        self.data_dir = self._determine_data_dir(data_dir)
        self.config_path = self.data_dir / 'thresholds.json'
        self.history_path = self.data_dir / 'threshold_history.json'
        
        # 設定の読み込み
        self.current_config = self.load_config()
        self.config_history = self.load_history()
        
        logger.info(f"ThresholdConfigManager初期化完了: {self.config_path}")
    
    def _determine_data_dir(self, data_dir: Optional[pathlib.Path]) -> pathlib.Path:
        """データディレクトリの決定"""
        if data_dir:
            return data_dir
        
        # 自動検出: スクリプトのパス、親ディレクトリ、カレントディレクトリの順
        possible_paths = [
            pathlib.Path(__file__).parent / 'data',
            pathlib.Path(__file__).parent.parent / 'data',
            pathlib.Path.cwd() / 'data'
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # 存在しない場合は最初のパスを作成
        possible_paths[0].mkdir(parents=True, exist_ok=True)
        return possible_paths[0]
    
    def create_default_config(self) -> Dict[str, Any]:
        """
        デフォルト閾値設定の作成
        
        Returns:
            デフォルト設定辞書
        """
        return {
            "config_version": "4.0.1",
            "last_updated": datetime.now().isoformat(),
            "last_updated_by": "system",
            
            # Prime信頼性関連閾値
            "prime_thresholds": {
                "high_confidence_threshold": 70,     # Prime確実判定
                "medium_confidence_threshold": 40,   # Prime要確認判定
                "low_confidence_threshold": 25,      # Prime疑わしい判定
                
                "amazon_seller_bonus": 25,           # Amazon出品者ボーナス
                "official_manufacturer_bonus": 20,   # 公式メーカーボーナス
                "third_party_bonus": 15,             # サードパーティボーナス
                
                "amazon_jp_seller_bonus": 30,        # Amazon.co.jp特別ボーナス
                "estimated_seller_penalty": -30,     # 推定出品者ペナルティ
                "valid_seller_bonus": 10,            # 有効出品者ボーナス
                "non_prime_amazon_penalty": -25      # 非PrimeAmazonペナルティ
            },
            
            # ShippingTime関連閾値
            "shipping_thresholds": {
                "super_fast_hours": 12,              # 超高速発送
                "fast_hours": 24,                    # 高速発送
                "standard_hours": 48,                # 標準発送
                "slow_hours": 72,                    # やや低速発送
                
                "confidence_excellent": 95,          # 発送信頼性：優秀
                "confidence_high": 80,               # 発送信頼性：高
                "confidence_medium": 60,             # 発送信頼性：中
                
                "super_fast_bonus": 15,              # 超高速ボーナス
                "fast_bonus": 10,                    # 高速ボーナス
                "standard_bonus": 5                  # 標準ボーナス
            },
            
            # Shopee適性スコア関連閾値
            "shopee_thresholds": {
                "group_a_threshold": 70,             # グループA（即出品）閾値
                "group_b_threshold": 50,             # グループB（要管理）閾値
                
                "prime_bonus": 10,                   # Primeボーナス
                "amazon_seller_bonus": 8,            # Amazon出品者ボーナス
                "brand_detection_bonus": 7,          # ブランド検出ボーナス
                "relevance_high_bonus": 10,          # 高関連性ボーナス
                "relevance_medium_bonus": 5,         # 中関連性ボーナス
                
                "base_score": 50                     # ベーススコア
            },
            
            # 関連性・一致度関連閾値
            "relevance_thresholds": {
                "high_relevance_threshold": 80,      # 高関連性判定
                "medium_relevance_threshold": 60,    # 中関連性判定
                "low_relevance_threshold": 30,       # 低関連性判定
                
                "beauty_terms_weight": 0.7,          # 美容用語重み
                "basic_match_weight": 0.3,           # 基本一致重み
                
                "match_excellent_threshold": 90,     # 優秀一致度
                "match_good_threshold": 70,          # 良好一致度
                "match_fair_threshold": 50           # 普通一致度
            },
            
            # NGワード関連設定
            "ng_word_actions": {
                "high_risk_action": "exclude",       # 高リスク：除外
                "medium_risk_action": "downgrade",   # 中リスク：降格
                "low_risk_action": "warn",           # 低リスク：警告
                
                "exclude_from_processing": True,     # 処理から除外
                "downgrade_to_group": "C",           # 降格先グループ
                "warning_display": True              # 警告表示
            },
            
            # 分類ロジック関連
            "classification_rules": {
                "prime_weight": 40,                  # Prime判定重み
                "shipping_weight": 30,               # ShippingTime重み
                "relevance_weight": 20,              # 関連性重み
                "brand_weight": 10,                  # ブランド重み
                
                "group_a_min_conditions": 2,         # グループA最小条件数
                "group_b_min_conditions": 1,         # グループB最小条件数
                
                "auto_approve_threshold": 85,        # 自動承認閾値
                "manual_review_threshold": 60        # 手動レビュー閾値
            },
            
            # システム設定
            "system_settings": {
                "enable_fallback": True,             # フォールバック有効
                "max_retry_attempts": 2,             # 最大リトライ回数
                "batch_processing_limit": 100,       # バッチ処理制限
                "api_timeout_seconds": 30,           # APIタイムアウト
                
                "debug_mode": False,                 # デバッグモード
                "verbose_logging": False,            # 詳細ログ
                "performance_monitoring": True       # パフォーマンス監視
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        設定ファイルの読み込み
        
        Returns:
            設定辞書
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # バージョンチェック・マイグレーション
                config = self._migrate_config_if_needed(config)
                
                logger.info(f"設定ファイル読み込み成功: {self.config_path}")
                return config
            else:
                logger.warning(f"設定ファイルが見つかりません: {self.config_path}")
                default_config = self.create_default_config()
                self.save_config(default_config)
                return default_config
                
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return self.create_default_config()
    
    def _migrate_config_if_needed(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定ファイルのバージョンマイグレーション
        
        Args:
            config: 既存の設定辞書
            
        Returns:
            マイグレーション後の設定辞書
        """
        current_version = config.get("config_version", "3.0.0")
        target_version = "4.0.1"
        
        if current_version != target_version:
            logger.info(f"設定ファイルマイグレーション: {current_version} → {target_version}")
            
            # デフォルト設定を取得
            default_config = self.create_default_config()
            
            # 既存設定をマージ（新しいキーを追加、既存キーは保持）
            migrated_config = self._deep_merge_configs(default_config, config)
            migrated_config["config_version"] = target_version
            migrated_config["last_updated"] = datetime.now().isoformat()
            migrated_config["migration_from"] = current_version
            
            # マイグレーション後の設定を保存
            self.save_config(migrated_config)
            
            return migrated_config
        
        return config
    
    def _deep_merge_configs(self, default: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定辞書の深いマージ
        
        Args:
            default: デフォルト設定
            existing: 既存設定
            
        Returns:
            マージされた設定
        """
        result = copy.deepcopy(default)
        
        for key, value in existing.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge_configs(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        設定ファイルの保存
        
        Args:
            config: 保存する設定辞書
            
        Returns:
            保存成功フラグ
        """
        try:
            # 履歴に現在の設定を記録
            if hasattr(self, 'current_config') and self.current_config:
                self._record_config_change(self.current_config, config)
            
            # データディレクトリを作成
            self.data_dir.mkdir(exist_ok=True)
            
            # 設定を保存
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.current_config = config
            logger.info(f"設定ファイル保存成功: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"設定ファイル保存エラー: {e}")
            return False
    
    def load_history(self) -> List[Dict[str, Any]]:
        """
        設定変更履歴の読み込み
        
        Returns:
            履歴リスト
        """
        try:
            if self.history_path.exists():
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                logger.info(f"設定履歴読み込み成功: {len(history)}件")
                return history
            else:
                return []
        except Exception as e:
            logger.error(f"設定履歴読み込みエラー: {e}")
            return []
    
    def _record_config_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """
        設定変更の履歴記録
        
        Args:
            old_config: 変更前設定
            new_config: 変更後設定
        """
        try:
            changes = self._detect_config_changes(old_config, new_config)
            
            if changes:
                history_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "user": new_config.get("last_updated_by", "system"),
                    "changes": changes,
                    "old_version": old_config.get("config_version", "unknown"),
                    "new_version": new_config.get("config_version", "unknown")
                }
                
                self.config_history.append(history_entry)
                
                # 履歴ファイルを保存
                with open(self.history_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config_history, f, ensure_ascii=False, indent=2)
                
                logger.info(f"設定変更履歴記録: {len(changes)}項目変更")
        
        except Exception as e:
            logger.error(f"設定変更履歴記録エラー: {e}")
    
    def _detect_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        設定変更の検出
        
        Args:
            old_config: 変更前設定
            new_config: 変更後設定
            
        Returns:
            変更項目リスト
        """
        changes = []
        
        def compare_dicts(old_dict: Dict[str, Any], new_dict: Dict[str, Any], path: str = ""):
            for key, new_value in new_dict.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in old_dict:
                    changes.append({
                        "type": "added",
                        "path": current_path,
                        "new_value": new_value
                    })
                elif isinstance(new_value, dict) and isinstance(old_dict[key], dict):
                    compare_dicts(old_dict[key], new_value, current_path)
                elif old_dict[key] != new_value:
                    changes.append({
                        "type": "modified",
                        "path": current_path,
                        "old_value": old_dict[key],
                        "new_value": new_value
                    })
            
            # 削除された項目をチェック
            for key in old_dict:
                if key not in new_dict:
                    current_path = f"{path}.{key}" if path else key
                    changes.append({
                        "type": "removed",
                        "path": current_path,
                        "old_value": old_dict[key]
                    })
        
        compare_dicts(old_config, new_config)
        return changes
    
    def get_threshold(self, category: str, key: str, default: Any = None) -> Any:
        """
        特定の閾値を取得
        
        Args:
            category: カテゴリ名（prime_thresholds, shipping_thresholds等）
            key: キー名
            default: デフォルト値
            
        Returns:
            閾値
        """
        try:
            return self.current_config.get(category, {}).get(key, default)
        except Exception as e:
            logger.error(f"閾値取得エラー: {category}.{key} - {e}")
            return default
    
    def update_threshold(self, category: str, key: str, value: Any, user: str = "system") -> bool:
        """
        特定の閾値を更新
        
        Args:
            category: カテゴリ名
            key: キー名
            value: 新しい値
            user: 更新者
            
        Returns:
            更新成功フラグ
        """
        try:
            if category not in self.current_config:
                self.current_config[category] = {}
            
            old_value = self.current_config[category].get(key)
            self.current_config[category][key] = value
            self.current_config["last_updated"] = datetime.now().isoformat()
            self.current_config["last_updated_by"] = user
            
            success = self.save_config(self.current_config)
            
            if success:
                logger.info(f"閾値更新成功: {category}.{key} {old_value} → {value}")
            
            return success
            
        except Exception as e:
            logger.error(f"閾値更新エラー: {category}.{key} - {e}")
            return False
    
    def get_preset_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        プリセット設定の取得
        
        Returns:
            プリセット設定辞書
        """
        presets = {
            "conservative": self._create_conservative_preset(),
            "balanced": self.create_default_config(),
            "aggressive": self._create_aggressive_preset()
        }
        return presets
    
    def _create_conservative_preset(self) -> Dict[str, Any]:
        """保守的設定プリセット"""
        config = self.create_default_config()
        
        # より厳しい閾値設定
        config["prime_thresholds"]["high_confidence_threshold"] = 80
        config["prime_thresholds"]["medium_confidence_threshold"] = 60
        config["shopee_thresholds"]["group_a_threshold"] = 80
        config["shopee_thresholds"]["group_b_threshold"] = 60
        config["shipping_thresholds"]["fast_hours"] = 18
        config["classification_rules"]["group_a_min_conditions"] = 3
        
        config["preset_name"] = "conservative"
        config["preset_description"] = "保守的設定 - 高品質商品のみを重視"
        
        return config
    
    def _create_aggressive_preset(self) -> Dict[str, Any]:
        """攻撃的設定プリセット"""
        config = self.create_default_config()
        
        # より緩い閾値設定
        config["prime_thresholds"]["high_confidence_threshold"] = 60
        config["prime_thresholds"]["medium_confidence_threshold"] = 30
        config["shopee_thresholds"]["group_a_threshold"] = 60
        config["shopee_thresholds"]["group_b_threshold"] = 40
        config["shipping_thresholds"]["fast_hours"] = 36
        config["classification_rules"]["group_a_min_conditions"] = 1
        
        config["preset_name"] = "aggressive"
        config["preset_description"] = "攻撃的設定 - より多くの商品を対象に"
        
        return config
    
    def apply_preset(self, preset_name: str, user: str = "system") -> bool:
        """
        プリセット設定の適用
        
        Args:
            preset_name: プリセット名
            user: 適用者
            
        Returns:
            適用成功フラグ
        """
        try:
            presets = self.get_preset_configs()
            
            if preset_name not in presets:
                logger.error(f"存在しないプリセット: {preset_name}")
                return False
            
            preset_config = presets[preset_name]
            preset_config["last_updated_by"] = user
            preset_config["applied_preset"] = preset_name
            
            return self.save_config(preset_config)
            
        except Exception as e:
            logger.error(f"プリセット適用エラー: {preset_name} - {e}")
            return False

# 便利関数
def create_threshold_config_manager(data_dir: Optional[Union[str, pathlib.Path]] = None) -> ThresholdConfigManager:
    """
    ThresholdConfigManagerのファクトリ関数
    
    Args:
        data_dir: データディレクトリパス
        
    Returns:
        ThresholdConfigManagerインスタンス
    """
    if isinstance(data_dir, str):
        data_dir = pathlib.Path(data_dir)
    return ThresholdConfigManager(data_dir)

if __name__ == "__main__":
    # テスト実行
    manager = create_threshold_config_manager()
    
    print("=== 閾値調整システムテスト ===")
    
    # 閾値取得テスト
    prime_threshold = manager.get_threshold("prime_thresholds", "high_confidence_threshold")
    print(f"Prime高信頼性閾値: {prime_threshold}")
    
    # 閾値更新テスト
    success = manager.update_threshold("prime_thresholds", "high_confidence_threshold", 75, "test_user")
    print(f"閾値更新結果: {success}")
    
    # プリセットテスト
    presets = manager.get_preset_configs()
    print(f"利用可能プリセット: {list(presets.keys())}")
    
    print("テスト完了")