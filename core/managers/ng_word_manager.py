"""
NGワード管理システム専用モジュール

責任:
- NGワード辞書の読み込み・保存
- NGワード検出・分析
- リスクレベル判定
- NGワードフィルタリング適用

設計原則:
- Single Responsibility Principle準拠
- 他モジュールから独立
- テスト容易性確保
"""

import json
import re
import pandas as pd
import pathlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NGWordManager:
    """NGワード管理システムのメインクラス"""
    
    def __init__(self, data_dir: Optional[pathlib.Path] = None):
        """
        NGWordManagerの初期化
        
        Args:
            data_dir: データディレクトリのパス（Noneの場合は自動検出）
        """
        self.data_dir = self._determine_data_dir(data_dir)
        self.ng_words_path = self.data_dir / 'ng_words.json'
        self.ng_words_dict = self.load_ng_words()
        
        logger.info(f"NGWordManager初期化完了: {self.ng_words_path}")
    
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
    
    def load_ng_words(self) -> Dict[str, List[str]]:
        """
        NGワード辞書の読み込み
        
        Returns:
            NGワード辞書（カテゴリ別）
        """
        try:
            if self.ng_words_path.exists():
                with open(self.ng_words_path, 'r', encoding='utf-8') as f:
                    ng_data = json.load(f)
                logger.info(f"NGワード辞書読み込み成功: {self.ng_words_path}")
                return ng_data
            else:
                logger.warning(f"NGワード辞書ファイルが見つかりません: {self.ng_words_path}")
                default_ng_words = self.create_default_ng_words()
                self.save_ng_words(default_ng_words)
                return default_ng_words
        except Exception as e:
            logger.error(f"NGワード辞書読み込みエラー: {e}")
            return self.create_default_ng_words()
    
    def create_default_ng_words(self) -> Dict[str, List[str]]:
        """
        デフォルトNGワード辞書の作成
        
        Returns:
            デフォルトNGワード辞書
        """
        return {
            "禁止商品": [
                "cigarette", "tobacco", "vape", "e-cigarette", "smoking",
                "alcohol", "wine", "beer", "sake", "whiskey", "vodka",
                "cbd", "thc", "marijuana", "cannabis", "hemp",
                "prescription", "medicine", "drug", "pharmaceutical",
                "weapon", "gun", "knife", "blade", "sword"
            ],
            "年齢制限": [
                "adult", "sexy", "lingerie", "underwear", "bikini",
                "18+", "mature", "erotic", "sensual"
            ],
            "医療関連": [
                "medical", "surgical", "clinic", "hospital", "therapy",
                "treatment", "cure", "heal", "diagnosis", "symptom"
            ],
            "著作権": [
                "disney", "pokemon", "hello kitty", "anime", "manga",
                "branded", "counterfeit", "replica", "fake", "copy"
            ],
            "危険物": [
                "explosive", "flammable", "toxic", "poison", "hazardous",
                "chemical", "battery", "lithium", "radioactive"
            ],
            "その他リスク": [
                "stolen", "illegal", "forbidden", "banned", "restricted",
                "unauthorized", "pirated", "bootleg"
            ]
        }
    
    def save_ng_words(self, ng_words_dict: Dict[str, List[str]]) -> bool:
        """
        NGワード辞書の保存
        
        Args:
            ng_words_dict: 保存するNGワード辞書
            
        Returns:
            保存成功フラグ
        """
        try:
            self.data_dir.mkdir(exist_ok=True)
            with open(self.ng_words_path, 'w', encoding='utf-8') as f:
                json.dump(ng_words_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"NGワード辞書保存成功: {self.ng_words_path}")
            self.ng_words_dict = ng_words_dict  # メモリ内辞書も更新
            return True
        except Exception as e:
            logger.error(f"NGワード辞書保存エラー: {e}")
            return False
    
    def check_ng_words(self, text: str) -> Dict[str, Any]:
        """
        テキストのNGワードチェック
        
        Args:
            text: チェック対象テキスト
            
        Returns:
            NGワードチェック結果
        """
        if not text or not self.ng_words_dict:
            return self._create_safe_result()
        
        text_lower = text.lower()
        matched_words = []
        ng_categories = []
        
        for category, words in self.ng_words_dict.items():
            for ng_word in words:
                if isinstance(ng_word, str):
                    # 完全一致と部分一致の両方をチェック
                    pattern = r'\b' + re.escape(ng_word.lower()) + r'\b'
                    if re.search(pattern, text_lower):
                        matched_words.append(ng_word)
                        ng_categories.append(category)
        
        # リスクレベル判定
        risk_level = self._determine_risk_level(ng_categories)
        
        return {
            'is_ng': len(matched_words) > 0,
            'ng_category': ng_categories[0] if ng_categories else None,
            'matched_words': matched_words,
            'risk_level': risk_level,
            'all_categories': list(set(ng_categories)),
            'check_timestamp': datetime.now().isoformat()
        }
    
    def _create_safe_result(self) -> Dict[str, Any]:
        """安全な結果を作成"""
        return {
            'is_ng': False,
            'ng_category': None,
            'matched_words': [],
            'risk_level': 'safe',
            'all_categories': [],
            'check_timestamp': datetime.now().isoformat()
        }
    
    def _determine_risk_level(self, ng_categories: List[str]) -> str:
        """
        NGワードカテゴリからリスクレベルを判定
        
        Args:
            ng_categories: 検出されたNGワードカテゴリリスト
            
        Returns:
            リスクレベル ('safe', 'low', 'medium', 'high')
        """
        if not ng_categories:
            return 'safe'
        
        high_risk_categories = ['禁止商品', '医療関連', '危険物']
        medium_risk_categories = ['年齢制限', '著作権']
        
        if any(cat in high_risk_categories for cat in ng_categories):
            return 'high'
        elif any(cat in medium_risk_categories for cat in ng_categories):
            return 'medium'
        else:
            return 'low'
    
    def apply_ng_word_filtering(self, df: pd.DataFrame, 
                               text_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        データフレームにNGワードフィルタリングを適用
        
        Args:
            df: 処理対象のデータフレーム
            text_columns: チェック対象カラム名リスト（Noneの場合は自動判定）
            
        Returns:
            NGワードチェック結果が追加されたデータフレーム
        """
        if df is None or df.empty:
            logger.warning("入力データフレームが空です")
            return df
        
        df_filtered = df.copy()
        
        # デフォルトのテキストカラム
        if text_columns is None:
            text_columns = ['clean_title', 'japanese_name', 'amazon_title']
        
        # NGワードチェック実行
        ng_check_results = []
        for idx, row in df_filtered.iterrows():
            # 複数カラムのテキストを結合
            text_to_check = ""
            for col in text_columns:
                if col in row and pd.notna(row[col]):
                    text_to_check += str(row[col]) + " "
            
            ng_result = self.check_ng_words(text_to_check.strip())
            ng_check_results.append(ng_result)
        
        # 結果をデータフレームに追加
        df_filtered['ng_check_is_ng'] = [result['is_ng'] for result in ng_check_results]
        df_filtered['ng_check_category'] = [result['ng_category'] for result in ng_check_results]
        df_filtered['ng_check_matched_words'] = [', '.join(result['matched_words']) for result in ng_check_results]
        df_filtered['ng_check_risk_level'] = [result['risk_level'] for result in ng_check_results]
        df_filtered['ng_check_timestamp'] = [result['check_timestamp'] for result in ng_check_results]
        
        # shopee_groupの調整
        self._adjust_shopee_groups(df_filtered)
        
        logger.info(f"NGワードフィルタリング完了: {len(df_filtered)}件処理, {df_filtered['ng_check_is_ng'].sum()}件検出")
        return df_filtered
    
    def _adjust_shopee_groups(self, df: pd.DataFrame) -> None:
        """
        NGワード検出に基づいてshopee_groupを調整
        
        Args:
            df: 調整対象のデータフレーム（in-place更新）
        """
        ng_indices = df[df['ng_check_is_ng'] == True].index
        if len(ng_indices) == 0:
            return
        
        # 高リスクは完全除外、中・低リスクはCランクに降格
        high_risk_indices = df[
            (df['ng_check_is_ng'] == True) & 
            (df['ng_check_risk_level'] == 'high')
        ].index
        
        medium_low_risk_indices = df[
            (df['ng_check_is_ng'] == True) & 
            (df['ng_check_risk_level'].isin(['medium', 'low']))
        ].index
        
        # 除外フラグ設定
        df.loc[high_risk_indices, 'ng_exclusion_flag'] = True
        df.loc[medium_low_risk_indices, 'ng_exclusion_flag'] = False
        
        # Cランクに降格
        if 'shopee_group' in df.columns:
            df.loc[ng_indices, 'shopee_group'] = 'C'
            if 'classification_reason' in df.columns:
                df.loc[ng_indices, 'classification_reason'] = (
                    df.loc[ng_indices, 'classification_reason'].astype(str) + ' (NGワード検出)'
                )
    
    def get_ng_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        NGワード検出統計の取得
        
        Args:
            df: 統計対象のデータフレーム
            
        Returns:
            NGワード統計情報
        """
        if df is None or df.empty or 'ng_check_is_ng' not in df.columns:
            return {
                'total_items': 0,
                'ng_detected_count': 0,
                'ng_rate_percentage': 0,
                'risk_distribution': {},
                'category_distribution': {}
            }
        
        total_items = len(df)
        ng_detected_count = df['ng_check_is_ng'].sum()
        ng_rate = (ng_detected_count / total_items * 100) if total_items > 0 else 0
        
        # リスクレベル分布
        risk_distribution = df[df['ng_check_is_ng'] == True]['ng_check_risk_level'].value_counts().to_dict()
        
        # カテゴリ分布
        category_distribution = df[df['ng_check_is_ng'] == True]['ng_check_category'].value_counts().to_dict()
        
        return {
            'total_items': total_items,
            'ng_detected_count': int(ng_detected_count),
            'ng_rate_percentage': round(ng_rate, 2),
            'risk_distribution': risk_distribution,
            'category_distribution': category_distribution,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def add_ng_word(self, category: str, word: str) -> bool:
        """
        NGワードの追加
        
        Args:
            category: カテゴリ名
            word: 追加するNGワード
            
        Returns:
            追加成功フラグ
        """
        try:
            if category not in self.ng_words_dict:
                self.ng_words_dict[category] = []
            
            if word not in self.ng_words_dict[category]:
                self.ng_words_dict[category].append(word)
                success = self.save_ng_words(self.ng_words_dict)
                if success:
                    logger.info(f"NGワード追加成功: {category}/{word}")
                    return True
            else:
                logger.warning(f"NGワード既存: {category}/{word}")
                return False
        except Exception as e:
            logger.error(f"NGワード追加エラー: {e}")
            return False
    
    def remove_ng_word(self, category: str, word: str) -> bool:
        """
        NGワードの削除
        
        Args:
            category: カテゴリ名
            word: 削除するNGワード
            
        Returns:
            削除成功フラグ
        """
        try:
            if category in self.ng_words_dict and word in self.ng_words_dict[category]:
                self.ng_words_dict[category].remove(word)
                success = self.save_ng_words(self.ng_words_dict)
                if success:
                    logger.info(f"NGワード削除成功: {category}/{word}")
                    return True
            else:
                logger.warning(f"NGワード見つからず: {category}/{word}")
                return False
        except Exception as e:
            logger.error(f"NGワード削除エラー: {e}")
            return False
    
    def export_ng_detected_items(self, df: pd.DataFrame, 
                                 export_path: Optional[pathlib.Path] = None) -> Optional[pathlib.Path]:
        """
        NGワード検出商品のエクスポート
        
        Args:
            df: エクスポート対象のデータフレーム
            export_path: エクスポート先パス（Noneの場合は自動生成）
            
        Returns:
            エクスポートファイルパス（失敗時はNone）
        """
        try:
            if df is None or df.empty or 'ng_check_is_ng' not in df.columns:
                logger.warning("NGワードチェック結果がありません")
                return None
            
            ng_detected_df = df[df['ng_check_is_ng'] == True].copy()
            if ng_detected_df.empty:
                logger.info("NGワード検出商品がありません")
                return None
            
            if export_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_path = self.data_dir / f'ng_detected_items_{timestamp}.csv'
            
            # エクスポート用カラム選択
            export_columns = [
                'clean_title', 'asin', 'shopee_group', 
                'ng_check_category', 'ng_check_risk_level', 'ng_check_matched_words'
            ]
            export_df = ng_detected_df[[col for col in export_columns if col in ng_detected_df.columns]]
            
            export_df.to_csv(export_path, index=False, encoding='utf-8-sig')
            logger.info(f"NGワード検出商品エクスポート成功: {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"NGワード検出商品エクスポートエラー: {e}")
            return None

# 便利関数
def create_ng_word_manager(data_dir: Optional[Union[str, pathlib.Path]] = None) -> NGWordManager:
    """
    NGWordManagerのファクトリ関数
    
    Args:
        data_dir: データディレクトリパス
        
    Returns:
        NGWordManagerインスタンス
    """
    if isinstance(data_dir, str):
        data_dir = pathlib.Path(data_dir)
    return NGWordManager(data_dir)

# モジュールレベルの便利関数（後方互換性用）
def check_ng_words(text: str, ng_words_dict: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    レガシー関数：NGWordManagerを使用してください
    """
    import warnings
    warnings.warn("この関数は非推奨です。NGWordManagerクラスを使用してください。", DeprecationWarning)
    
    manager = NGWordManager()
    manager.ng_words_dict = ng_words_dict
    return manager.check_ng_words(text)

def apply_ng_word_filtering(df: pd.DataFrame, ng_words_dict: Dict[str, List[str]]) -> pd.DataFrame:
    """
    レガシー関数：NGWordManagerを使用してください
    """
    import warnings
    warnings.warn("この関数は非推奨です。NGWordManagerクラスを使用してください。", DeprecationWarning)
    
    manager = NGWordManager()
    manager.ng_words_dict = ng_words_dict
    return manager.apply_ng_word_filtering(df)

if __name__ == "__main__":
    # テスト実行
    manager = create_ng_word_manager()
    
    # テストデータ
    test_texts = [
        "FANCL mild cleansing oil",
        "alcohol based sanitizer",
        "medical device for therapy",
        "natural organic cream"
    ]
    
    print("=== NGワード管理システムテスト ===")
    for text in test_texts:
        result = manager.check_ng_words(text)
        print(f"テキスト: {text}")
        print(f"結果: {result}")
        print()
