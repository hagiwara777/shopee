# config_tab.py修正版 - メソッド存在チェック対応
import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime

def render_config_tab(config_available, config_manager, session_state):
    """閾値調整タブのレンダリング（メソッド存在チェック対応版）"""
    
    if not config_available or config_manager is None:
        st.error("⚠️ 動的閾値調整システムが利用できません")
        st.info("config_manager.pyが必要です")
        return
    
    st.header("🎛️ 動的閾値調整システム")
    
    # 現在の設定情報表示
    current_preset = config_manager.current_config.get("applied_preset", "カスタム")
    last_updated = config_manager.current_config.get("last_updated", "不明")
    
    # プリセット名の日英マッピング
    preset_mapping = {
        # 日本語 → 英語（内部処理用）
        "品質重視": "conservative",
        "標準設定": "balanced", 
        "量産重視": "aggressive",
        "カスタム": "カスタム"
    }
    
    # 英語 → 日本語（表示用）
    preset_display = {
        "conservative": "品質重視",
        "balanced": "標準設定",
        "aggressive": "量産重視", 
        "カスタム": "カスタム"
    }
    
    current_preset_jp = preset_display.get(current_preset, current_preset)
    
    # 現在の設定表示
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #10B981, #059669);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 1rem;
    ">
        <h4 style="margin: 0;">📊 現在の設定</h4>
        <p style="margin: 0.5rem 0 0 0;">
            <strong>適用中プリセット</strong>: {current_preset_jp}<br>
            <strong>最終更新</strong>: {last_updated}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # プリセット選択セクション
    st.subheader("🎯 プリセット選択")
    
    # 日本語選択肢のリスト
    preset_options = ["品質重視", "標準設定", "量産重視"]
    
    # 現在の設定に基づいたデフォルト選択
    current_index = 1  # デフォルトは「標準設定」
    if current_preset_jp in preset_options:
        current_index = preset_options.index(current_preset_jp)
    
    # プリセット選択ドロップダウン（日本語版）
    selected_preset_jp = st.selectbox(
        "プリセットを選択:",
        options=preset_options,
        index=current_index,
        help="商品の品質と量のバランスを調整します"
    )
    
    # 選択されたプリセットの説明表示
    preset_descriptions = {
        "品質重視": {
            "description": "高品質商品のみを選別する保守的な設定",
            "characteristics": [
                "Prime確実閾値: 80点 (高め)",
                "GroupA閾値: 75点 (高め)", 
                "対象商品数: 少なめ",
                "成功率: 最高 (98%+)",
                "適用場面: 初回運用、ブランド重視"
            ],
            "color": "#3B82F6"
        },
        "標準設定": {
            "description": "品質と量のバランスを取った推奨設定",
            "characteristics": [
                "Prime確実閾値: 70点 (標準)",
                "GroupA閾値: 70点 (標準)",
                "対象商品数: 適度",
                "成功率: 高い (97%+)",
                "適用場面: 通常運用、汎用的"
            ],
            "color": "#10B981"
        },
        "量産重視": {
            "description": "より多くの商品を対象とする積極的な設定",
            "characteristics": [
                "Prime確実閾値: 60点 (低め)",
                "GroupA閾値: 65点 (低め)",
                "対象商品数: 多め", 
                "成功率: 良い (95%+)",
                "適用場面: 大量出品、売上重視"
            ],
            "color": "#F59E0B"
        }
    }
    
    # 選択されたプリセットの詳細表示
    if selected_preset_jp in preset_descriptions:
        preset_info = preset_descriptions[selected_preset_jp]
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {preset_info['color']}, {preset_info['color']}AA);
            padding: 1rem;
            border-radius: 8px;
            color: white;
            margin: 1rem 0;
        ">
            <h4 style="margin: 0 0 0.5rem 0;">🎯 {selected_preset_jp}の特徴</h4>
            <p style="margin: 0 0 1rem 0; opacity: 0.9;">{preset_info['description']}</p>
            <ul style="margin: 0; padding-left: 1.2rem;">
                {''.join([f'<li>{char}</li>' for char in preset_info['characteristics']])}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # プリセット適用ボタン
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button(
            f"🔄 「{selected_preset_jp}」を適用", 
            help=f"{selected_preset_jp}の設定を適用します",
            use_container_width=True
        ):
            # 日本語から英語に変換
            preset_key = preset_mapping[selected_preset_jp]
            
            # プリセット適用
            try:
                if config_manager.apply_preset(preset_key, "UI_User"):
                    st.success(f"✅ 「{selected_preset_jp}」設定を適用しました！")
                    st.balloons()  # 成功時のアニメーション
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 設定の適用に失敗しました")
            except Exception as e:
                st.error(f"❌ 設定適用エラー: {str(e)}")
    
    # 現在の閾値表示
    st.markdown("---")
    st.subheader("📊 現在の閾値設定")
    
    # 主要閾値の取得（エラーハンドリング付き）
    try:
        prime_high = config_manager.get_threshold("prime_thresholds", "high_confidence_threshold", 70)
        prime_medium = config_manager.get_threshold("prime_thresholds", "medium_confidence_threshold", 40)
        group_a = config_manager.get_threshold("shopee_thresholds", "group_a_threshold", 70)
        group_b = config_manager.get_threshold("shopee_thresholds", "group_b_threshold", 50)
    except Exception as e:
        st.error(f"閾値取得エラー: {str(e)}")
        # フォールバック値
        prime_high = 70
        prime_medium = 40
        group_a = 70
        group_b = 50
    
    # 閾値表示（カード形式）
    threshold_col1, threshold_col2 = st.columns(2)
    
    with threshold_col1:
        st.markdown(f"""
        <div style="
            background: #F8F9FA;
            border-left: 4px solid #10B981;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 0.5rem;
        ">
            <h5 style="margin: 0; color: #10B981;">🎯 Prime判定閾値</h5>
            <p style="margin: 0.5rem 0 0 0; color: #666;">
                <strong>Prime確実</strong>: {prime_high}点<br>
                <strong>Prime要確認</strong>: {prime_medium}点
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with threshold_col2:
        st.markdown(f"""
        <div style="
            background: #F8F9FA;
            border-left: 4px solid #3B82F6;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 0.5rem;
        ">
            <h5 style="margin: 0; color: #3B82F6;">🛒 Shopee判定閾値</h5>
            <p style="margin: 0.5rem 0 0 0; color: #666;">
                <strong>グループA</strong>: {group_a}点<br>
                <strong>グループB</strong>: {group_b}点
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # 詳細設定（上級者向け）
    with st.expander("🔧 詳細設定（上級者向け）", expanded=False):
        st.warning("⚠️ 詳細設定の変更は慎重に行ってください")
        
        # 配送関連閾値
        st.markdown("**📦 配送関連閾値**")
        try:
            fast_hours = config_manager.get_threshold("shipping_thresholds", "fast_hours", 24)
            super_fast_hours = config_manager.get_threshold("shipping_thresholds", "super_fast_hours", 12)
            
            st.write(f"・超高速発送: {super_fast_hours}時間以内")
            st.write(f"・高速発送: {fast_hours}時間以内")
        except Exception as e:
            st.write("・超高速発送: 12時間以内（デフォルト）")
            st.write("・高速発送: 24時間以内（デフォルト）")
        
        # 美容用語関連閾値
        st.markdown("**💄 美容用語関連閾値**")
        try:
            beauty_bonus = config_manager.get_threshold("beauty_thresholds", "beauty_term_bonus", 5)
            brand_bonus = config_manager.get_threshold("beauty_thresholds", "brand_match_bonus", 10)
            
            st.write(f"・美容用語一致ボーナス: +{beauty_bonus}点")
            st.write(f"・ブランド一致ボーナス: +{brand_bonus}点")
        except Exception as e:
            st.write("・美容用語一致ボーナス: +5点（デフォルト）")
            st.write("・ブランド一致ボーナス: +10点（デフォルト）")
    
    # 設定履歴（メソッド存在チェック付き）
    with st.expander("📜 設定変更履歴", expanded=False):
        try:
            # メソッドが存在するかチェック
            if hasattr(config_manager, 'get_change_history'):
                history = config_manager.get_change_history()
                if history and len(history) > 0:
                    for entry in history[-5:]:  # 最新5件表示
                        timestamp = entry.get('timestamp', '不明')
                        preset = preset_display.get(entry.get('preset', ''), entry.get('preset', ''))
                        user = entry.get('user', '不明')
                        st.markdown(f"・**{timestamp}**: {preset} (by {user})")
                else:
                    st.info("設定変更履歴はありません")
            else:
                st.info("設定変更履歴機能は利用できません（メソッド未実装）")
        except Exception as e:
            st.warning(f"履歴取得エラー: {str(e)}")
            st.info("設定変更履歴の取得に失敗しました")
    
    # 設定のエクスポート/インポート（メソッド存在チェック付き）
    st.markdown("---")
    st.subheader("💾 設定の保存・読込")
    
    export_col, import_col = st.columns(2)
    
    with export_col:
        # エクスポート機能
        try:
            if hasattr(config_manager, 'export_config'):
                if st.button("📤 設定をエクスポート", help="現在の設定をJSONファイルとして保存"):
                    try:
                        config_json = config_manager.export_config()
                        st.download_button(
                            label="💾 設定ファイルをダウンロード",
                            data=config_json,
                            file_name=f"shopee_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    except Exception as e:
                        st.error(f"エクスポートエラー: {str(e)}")
            else:
                st.info("💾 設定エクスポート機能は利用できません")
        except Exception as e:
            st.error(f"エクスポート機能エラー: {str(e)}")
    
    with import_col:
        # インポート機能
        try:
            if hasattr(config_manager, 'import_config'):
                uploaded_file = st.file_uploader(
                    "📥 設定をインポート", 
                    type=['json'],
                    help="以前エクスポートした設定ファイルを読み込み"
                )
                
                if uploaded_file is not None:
                    if st.button("🔄 設定を適用"):
                        try:
                            config_data = json.loads(uploaded_file.read())
                            if config_manager.import_config(config_data):
                                st.success("✅ 設定のインポートが完了しました")
                                st.rerun()
                            else:
                                st.error("❌ 設定のインポートに失敗しました")
                        except json.JSONDecodeError:
                            st.error("❌ 無効なJSONファイルです")
                        except Exception as e:
                            st.error(f"❌ インポートエラー: {str(e)}")
            else:
                st.info("📥 設定インポート機能は利用できません")
        except Exception as e:
            st.error(f"インポート機能エラー: {str(e)}")
    
    # 現在利用可能な機能の表示
    st.markdown("---")
    st.subheader("🔧 利用可能な機能")
    
    # config_managerで利用可能なメソッドをチェック
    available_methods = []
    method_checks = [
        ('apply_preset', 'プリセット適用'),
        ('get_threshold', '閾値取得'),
        ('get_change_history', '変更履歴'),
        ('export_config', '設定エクスポート'),
        ('import_config', '設定インポート')
    ]
    
    for method_name, method_desc in method_checks:
        if hasattr(config_manager, method_name):
            available_methods.append(f"✅ {method_desc}")
        else:
            available_methods.append(f"❌ {method_desc}")
    
    for method_status in available_methods:
        st.markdown(method_status)
    
    # システム情報
    with st.expander("ℹ️ システム情報", expanded=False):
        st.markdown(f"""
        **設定管理システム**: Phase 4.0-3対応版  
        **現在時刻**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
        **設定ファイル**: 動的閾値調整システム  
        **エラーハンドリング**: 完全対応済み
        """)