# analysis_tab.py - 詳細分析機能（Phase 4.0-3）
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
import json

def render_analysis_tab(session_state, asin_helpers_available, sp_api_available):
    """詳細分析タブ"""
    
    st.header("🔬 詳細分析 - Phase 4.0-3")
    
    # データ存在チェック
    df = session_state.get('processed_df')
    if df is None or df.empty:
        st.warning("📋 データを読み込んでください（データ管理タブ）")
        render_demo_analysis()
        return
    
    # 分析タイプ選択
    analysis_type = st.selectbox(
        "🔍 分析タイプを選択:",
        [
            "美容用語効果分析",
            "ブランド別分析", 
            "Prime影響度分析",
            "配送時間相関分析",
            "成功率予測分析",
            "総合相関分析"
        ],
        help="実行したい分析を選択してください"
    )
    
    st.markdown("---")
    
    # 分析実行
    if analysis_type == "美容用語効果分析":
        render_beauty_terms_analysis(df)
    elif analysis_type == "ブランド別分析":
        render_brand_analysis(df)
    elif analysis_type == "Prime影響度分析":
        render_prime_impact_analysis(df)
    elif analysis_type == "配送時間相関分析":
        render_shipping_correlation_analysis(df)
    elif analysis_type == "成功率予測分析":
        render_success_prediction_analysis(df)
    elif analysis_type == "総合相関分析":
        render_comprehensive_correlation_analysis(df)

def render_demo_analysis():
    """デモ分析表示"""
    st.info("💡 デモデータで分析機能を表示しています")
    
    # デモ美容用語分析
    st.subheader("💄 美容用語効果分析（デモ）")
    
    demo_beauty_data = {
        'keyword': ['oil', 'cream', 'serum', 'lotion', 'mask'],
        'count': [25, 18, 15, 12, 8],
        'avg_shopee_score': [78.5, 82.1, 85.3, 74.2, 79.8],
        'avg_prime_score': [72.4, 75.8, 81.2, 68.9, 73.5]
    }
    
    demo_df = pd.DataFrame(demo_beauty_data)
    
    # 美容用語別スコア比較（デモ）
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Shopee適性スコア',
        x=demo_df['keyword'],
        y=demo_df['avg_shopee_score'],
        marker_color='#10B981'
    ))
    
    fig.add_trace(go.Bar(
        name='Prime信頼性スコア',
        x=demo_df['keyword'],
        y=demo_df['avg_prime_score'],
        marker_color='#3B82F6'
    ))
    
    fig.update_layout(
        title='美容用語別平均スコア比較（デモ）',
        xaxis_title='美容用語',
        yaxis_title='平均スコア',
        barmode='group',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # デモ詳細データ表示
    st.subheader("📊 美容用語詳細データ（デモ）")
    st.dataframe(demo_df, use_container_width=True)

def render_beauty_terms_analysis(df):
    """美容用語効果分析"""
    st.subheader("💄 美容用語効果分析")
    
    # 美容用語の検出
    beauty_keywords = ['oil', 'cream', 'serum', 'lotion', 'cleanser', 'mask', 'treatment', 'toner', 'essence', 'gel']
    
    if 'clean_title' not in df.columns:
        st.warning("商品タイトル情報が見つかりません")
        return
    
    beauty_data = []
    for keyword in beauty_keywords:
        keyword_df = df[df['clean_title'].str.contains(keyword, case=False, na=False)]
        if len(keyword_df) > 0:
            avg_shopee_score = keyword_df.get('shopee_suitability_score', pd.Series([0])).mean()
            avg_prime_score = keyword_df.get('prime_confidence_score', pd.Series([0])).mean()
            avg_relevance = keyword_df.get('relevance_score', pd.Series([0])).mean()
            count = len(keyword_df)
            group_a_rate = len(keyword_df[keyword_df.get('shopee_group') == 'A']) / len(keyword_df) * 100 if 'shopee_group' in keyword_df.columns else 0
            
            beauty_data.append({
                'keyword': keyword,
                'count': count,
                'avg_shopee_score': avg_shopee_score,
                'avg_prime_score': avg_prime_score,
                'avg_relevance': avg_relevance,
                'group_a_rate': group_a_rate
            })
    
    if beauty_data:
        beauty_df = pd.DataFrame(beauty_data)
        
        # 美容用語分析チャート
        analysis_col1, analysis_col2 = st.columns(2)
        
        with analysis_col1:
            # 美容用語別スコア比較
            fig1 = go.Figure()
            
            fig1.add_trace(go.Bar(
                name='Shopee適性スコア',
                x=beauty_df['keyword'],
                y=beauty_df['avg_shopee_score'],
                marker_color='#10B981'
            ))
            
            fig1.add_trace(go.Bar(
                name='Prime信頼性スコア',
                x=beauty_df['keyword'],
                y=beauty_df['avg_prime_score'],
                marker_color='#3B82F6'
            ))
            
            fig1.update_layout(
                title='美容用語別平均スコア比較',
                xaxis_title='美容用語',
                yaxis_title='平均スコア',
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        
        with analysis_col2:
            # 商品数とグループA率の相関
            fig2 = px.scatter(
                beauty_df,
                x='count',
                y='group_a_rate',
                size='avg_shopee_score',
                color='avg_prime_score',
                hover_name='keyword',
                title='商品数 vs グループA率',
                labels={'count': '商品数', 'group_a_rate': 'グループA率(%)'}
            )
            
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # 詳細データ表示
        st.subheader("📊 美容用語詳細データ")
        
        # データを見やすく整形
        display_df = beauty_df.copy()
        display_df['avg_shopee_score'] = display_df['avg_shopee_score'].round(1)
        display_df['avg_prime_score'] = display_df['avg_prime_score'].round(1)
        display_df['avg_relevance'] = display_df['avg_relevance'].round(1)
        display_df['group_a_rate'] = display_df['group_a_rate'].round(1)
        
        # カラム名を日本語に
        display_df.columns = ['美容用語', '商品数', 'Shopee適性平均', 'Prime信頼性平均', '関連性平均', 'グループA率(%)']
        
        st.dataframe(display_df, use_container_width=True)
        
        # トップ美容用語の分析
        top_keywords = beauty_df.nlargest(3, 'avg_shopee_score')
        st.subheader("🏆 トップ美容用語")
        
        for idx, row in top_keywords.iterrows():
            st.markdown(f"""
            **{row['keyword'].upper()}**
            - 商品数: {row['count']}件
            - Shopee適性: {row['avg_shopee_score']:.1f}点
            - Prime信頼性: {row['avg_prime_score']:.1f}点
            - グループA率: {row['group_a_rate']:.1f}%
            """)
    else:
        st.info("美容用語が検出されませんでした")

def render_brand_analysis(df):
    """ブランド別分析"""
    st.subheader("🏷️ ブランド別分析")
    
    if 'extracted_brand' not in df.columns:
        st.warning("ブランド情報が見つかりません")
        return
    
    # ブランドデータのクリーニング
    brand_df = df[df['extracted_brand'].notna() & (df['extracted_brand'] != '')].copy()
    
    if len(brand_df) == 0:
        st.info("ブランドデータがありません")
        return
    
    brand_analysis_col1, brand_analysis_col2 = st.columns(2)
    
    with brand_analysis_col1:
        # ブランド別商品数（Top 10）
        brand_counts = brand_df['extracted_brand'].value_counts().head(10)
        
        fig1 = px.pie(
            values=brand_counts.values,
            names=brand_counts.index,
            title="ブランド別商品数分布（Top 10）",
            height=400
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with brand_analysis_col2:
        # ブランド別スコア分析
        if 'shopee_suitability_score' in brand_df.columns:
            brand_scores = brand_df.groupby('extracted_brand').agg({
                'shopee_suitability_score': 'mean',
                'prime_confidence_score': 'mean' if 'prime_confidence_score' in brand_df.columns else lambda x: 0,
                'extracted_brand': 'count'
            }).round(2)
            
            brand_scores = brand_scores.rename(columns={'extracted_brand': 'count'})
            brand_scores = brand_scores[brand_scores['count'] >= 2].head(10)  # 2件以上のブランドのみ
            
            if len(brand_scores) > 0:
                fig2 = go.Figure()
                
                fig2.add_trace(go.Scatter(
                    x=brand_scores.index,
                    y=brand_scores['shopee_suitability_score'],
                    mode='markers+lines',
                    name='Shopee適性スコア',
                    marker=dict(size=10, color='#10B981'),
                    line=dict(color='#10B981', width=2)
                ))
                
                if 'prime_confidence_score' in brand_df.columns:
                    fig2.add_trace(go.Scatter(
                        x=brand_scores.index,
                        y=brand_scores['prime_confidence_score'],
                        mode='markers+lines',
                        name='Prime信頼性スコア',
                        marker=dict(size=10, color='#3B82F6'),
                        line=dict(color='#3B82F6', width=2)
                    ))
                
                fig2.update_layout(
                    title='ブランド別平均スコア',
                    xaxis_title='ブランド',
                    yaxis_title='平均スコア',
                    height=400,
                    xaxis_tickangle=-45
                )
                
                st.plotly_chart(fig2, use_container_width=True)
    
    # ブランドパフォーマンス詳細
    st.subheader("📊 ブランドパフォーマンス詳細")
    
    brand_performance = brand_df.groupby('extracted_brand').agg({
        'shopee_suitability_score': ['mean', 'std', 'count'],
        'prime_confidence_score': 'mean' if 'prime_confidence_score' in brand_df.columns else lambda x: 0,
        'shopee_group': lambda x: (x == 'A').sum() / len(x) * 100 if 'shopee_group' in brand_df.columns else 0
    }).round(2)
    
    # カラム名を平坦化
    brand_performance.columns = ['Shopee適性平均', 'Shopee適性標準偏差', '商品数', 'Prime信頼性平均', 'グループA率(%)']
    brand_performance = brand_performance[brand_performance['商品数'] >= 2].head(15)
    
    if len(brand_performance) > 0:
        st.dataframe(brand_performance, use_container_width=True)
        
        # トップブランドの特徴
        top_brand = brand_performance.loc[brand_performance['Shopee適性平均'].idxmax()]
        st.success(f"""
        🏆 **最高パフォーマンスブランド**: {top_brand.name}
        - Shopee適性: {top_brand['Shopee適性平均']:.1f}点
        - 商品数: {top_brand['商品数']:.0f}件
        - グループA率: {top_brand['グループA率(%)']:.1f}%
        """)

def render_prime_impact_analysis(df):
    """Prime影響度分析"""
    st.subheader("🎯 Prime影響度分析")
    
    if 'is_prime' not in df.columns:
        st.warning("Prime情報が見つかりません")
        return
    
    prime_analysis_col1, prime_analysis_col2 = st.columns(2)
    
    with prime_analysis_col1:
        # Prime vs 非Prime比較
        if 'shopee_suitability_score' in df.columns:
            prime_data = df[df['is_prime'] == True]['shopee_suitability_score']
            non_prime_data = df[df['is_prime'] == False]['shopee_suitability_score']
            
            fig1 = go.Figure()
            
            if len(prime_data) > 0:
                fig1.add_trace(go.Box(
                    y=prime_data,
                    name='Prime商品',
                    marker_color='#10B981'
                ))
            
            if len(non_prime_data) > 0:
                fig1.add_trace(go.Box(
                    y=non_prime_data,
                    name='非Prime商品',
                    marker_color='#EF4444'
                ))
            
            fig1.update_layout(
                title='Prime有無によるShopee適性スコア分布',
                yaxis_title='Shopee適性スコア',
                height=400
            )
            
            st.plotly_chart(fig1, use_container_width=True)
    
    with prime_analysis_col2:
        # Prime統計サマリー
        prime_count = len(df[df['is_prime'] == True])
        non_prime_count = len(df[df['is_prime'] == False])
        total_count = len(df)
        
        st.markdown(f"""
        <div class="analysis-container">
            <h4>📊 Prime統計サマリー</h4>
            <p><strong>Prime商品</strong>: {prime_count}件 ({prime_count/total_count*100:.1f}%)</p>
            <p><strong>非Prime商品</strong>: {non_prime_count}件 ({non_prime_count/total_count*100:.1f}%)</p>
        </div>
        """, unsafe_allow_html=True)
        
        if 'shopee_suitability_score' in df.columns:
            prime_avg = df[df['is_prime'] == True]['shopee_suitability_score'].mean()
            non_prime_avg = df[df['is_prime'] == False]['shopee_suitability_score'].mean()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Prime平均スコア", f"{prime_avg:.1f}", delta=f"{prime_avg - non_prime_avg:.1f}")
            with col2:
                st.metric("非Prime平均スコア", f"{non_prime_avg:.1f}")
    
    # Prime効果の統計的検定
    if 'shopee_suitability_score' in df.columns and len(prime_data) > 0 and len(non_prime_data) > 0:
        st.subheader("📈 統計的分析")
        
        # t検定実行
        t_stat, p_value = stats.ttest_ind(prime_data, non_prime_data)
        
        significance_level = 0.05
        is_significant = p_value < significance_level
        
        st.markdown(f"""
        **統計的検定結果**:
        - t統計量: {t_stat:.3f}
        - p値: {p_value:.6f}
        - 有意水準: {significance_level}
        - 結果: {'統計的に有意な差あり' if is_significant else '統計的に有意な差なし'}
        
        💡 **解釈**: Prime商品と非Prime商品の間に{'は' if is_significant else 'は'}統計的に有意な適性スコアの差が{'あります' if is_significant else 'ありません'}。
        """)

def render_shipping_correlation_analysis(df):
    """配送時間相関分析"""
    st.subheader("🚚 配送時間相関分析")
    
    if 'ship_hours' not in df.columns:
        st.warning("配送時間情報が見つかりません")
        return
    
    ship_data = df[df['ship_hours'].notna()].copy()
    
    if len(ship_data) == 0:
        st.info("配送時間データがありません")
        return
    
    shipping_col1, shipping_col2 = st.columns(2)
    
    with shipping_col1:
        # 配送時間とスコアの散布図
        if 'shopee_suitability_score' in ship_data.columns:
            fig1 = px.scatter(
                ship_data,
                x='ship_hours',
                y='shopee_suitability_score',
                title='配送時間 vs Shopee適性スコア',
                trendline='ols',
                hover_data=['asin'] if 'asin' in ship_data.columns else None,
                color='is_prime' if 'is_prime' in ship_data.columns else None,
                color_discrete_map={True: '#10B981', False: '#EF4444'}
            )
            
            fig1.update_layout(
                xaxis_title='配送時間（時間）',
                yaxis_title='Shopee適性スコア',
                height=400
            )
            
            st.plotly_chart(fig1, use_container_width=True)
    
    with shipping_col2:
        # 配送時間カテゴリ別分析
        ship_categories = pd.cut(
            ship_data['ship_hours'], 
            bins=[0, 12, 24, 48, float('inf')], 
            labels=['12h以内', '12-24h', '24-48h', '48h超']
        )
        
        ship_data['ship_category'] = ship_categories
        
        category_analysis = ship_data.groupby('ship_category').agg({
            'shopee_suitability_score': ['mean', 'count'],
            'prime_confidence_score': 'mean' if 'prime_confidence_score' in ship_data.columns else lambda x: 0
        }).round(2)
        
        # カラム名を平坦化
        category_analysis.columns = ['Shopee適性平均', '商品数', 'Prime信頼性平均']
        
        fig2 = px.bar(
            x=category_analysis.index,
            y=category_analysis['Shopee適性平均'],
            title='配送時間カテゴリ別平均スコア',
            labels={'x': '配送時間カテゴリ', 'y': 'Shopee適性平均スコア'},
            color=category_analysis['Shopee適性平均'],
            color_continuous_scale='Viridis'
        )
        
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
    
    # 配送時間詳細統計
    st.subheader("📊 配送時間詳細統計")
    st.dataframe(category_analysis, use_container_width=True)
    
    # 相関係数計算
    if 'shopee_suitability_score' in ship_data.columns:
        correlation = ship_data['ship_hours'].corr(ship_data['shopee_suitability_score'])
        
        if abs(correlation) > 0.3:
            strength = "強い" if abs(correlation) > 0.7 else "中程度の"
            direction = "負の" if correlation < 0 else "正の"
            st.success(f"📈 **相関分析結果**: 配送時間とShopee適性スコアの間に{strength}{direction}相関があります（r = {correlation:.3f}）")
        else:
            st.info(f"📈 **相関分析結果**: 配送時間とShopee適性スコアの間に明確な相関は見られません（r = {correlation:.3f}）")

def render_success_prediction_analysis(df):
    """成功率予測分析"""
    st.subheader("🎯 成功率予測分析")
    
    # 成功率予測モデル（簡易版）
    success_factors = []
    
    total_items = len(df)
    
    # 各要因の計算
    if 'shopee_group' in df.columns:
        group_a_count = len(df[df['shopee_group'] == 'A'])
        group_a_rate = group_a_count / total_items * 100
        success_factors.append(('グループA率', group_a_rate, 30, group_a_count))
    
    if 'is_prime' in df.columns:
        prime_count = len(df[df['is_prime'] == True])
        prime_rate = prime_count / total_items * 100
        success_factors.append(('Prime商品率', prime_rate, 25, prime_count))
    
    if 'ship_hours' in df.columns:
        fast_shipping_count = len(df[df['ship_hours'] <= 24])
        total_with_shipping = len(df[df['ship_hours'].notna()])
        fast_shipping_rate = fast_shipping_count / total_with_shipping * 100 if total_with_shipping > 0 else 0
        success_factors.append(('高速配送率', fast_shipping_rate, 20, fast_shipping_count))
    
    if 'extracted_brand' in df.columns:
        brand_count = len(df[df['extracted_brand'].notna() & (df['extracted_brand'] != '')])
        brand_coverage = brand_count / total_items * 100
        success_factors.append(('ブランド特定率', brand_coverage, 15, brand_count))
    
    # 予測成功率計算
    base_rate = 75
    bonus_rate = 0
    
    for factor_name, rate, weight, count in success_factors:
        normalized_rate = min(rate / 100, 1.0)
        bonus_rate += normalized_rate * weight
    
    predicted_success_rate = base_rate + bonus_rate
    
    # 成功率表示
    prediction_col1, prediction_col2, prediction_col3 = st.columns(3)
    
    with prediction_col1:
        st.metric("基本成功率", f"{base_rate}%")
    
    with prediction_col2:
        st.metric("ボーナス成功率", f"+{bonus_rate:.1f}%")
    
    with prediction_col3:
        st.metric("予測総合成功率", f"{predicted_success_rate:.1f}%")
    
    # 成功要因分析チャート
    if success_factors:
        factor_data = []
        for factor_name, rate, weight, count in success_factors:
            factor_data.append({
                '要因': factor_name,
                '現在値(%)': rate,
                '重要度': weight,
                '商品数': count,
                '貢献度': (rate/100) * weight
            })
        
        factor_df = pd.DataFrame(factor_data)
        
        analysis_chart_col1, analysis_chart_col2 = st.columns(2)
        
        with analysis_chart_col1:
            fig1 = px.bar(
                factor_df,
                x='要因',
                y='現在値(%)',
                color='重要度',
                title='成功率要因分析',
                color_continuous_scale='Viridis',
                text='現在値(%)'
            )
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with analysis_chart_col2:
            fig2 = px.pie(
                factor_df,
                values='貢献度',
                names='要因',
                title='成功率への貢献度分布'
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # 詳細データ表示
        st.subheader("📊 成功要因詳細")
        display_factor_df = factor_df.copy()
        display_factor_df['現在値(%)'] = display_factor_df['現在値(%)'].round(1)
        display_factor_df['貢献度'] = display_factor_df['貢献度'].round(1)
        
        st.dataframe(display_factor_df, use_container_width=True)
        
        # 改善提案
        st.subheader("💡 成功率向上提案")
        
        improvement_suggestions = []
        
        for _, row in factor_df.iterrows():
            if row['現在値(%)'] < 50 and row['重要度'] >= 20:
                improvement_suggestions.append(f"🎯 **{row['要因']}**を向上（現在{row['現在値(%)']:.1f}%）: 重要度が高く改善効果大")
        
        if not improvement_suggestions:
            improvement_suggestions.append("✅ 現在の各要因は良好な水準にあります。継続的な維持を推奨します。")
        
        for suggestion in improvement_suggestions:
            st.info(suggestion)

def render_comprehensive_correlation_analysis(df):
    """総合相関分析"""
    st.subheader("🔗 総合相関分析")
    
    # 数値列の抽出
    numeric_columns = []
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64', 'bool']:
            if df[col].notna().sum() > 0:  # データがある列のみ
                numeric_columns.append(col)
    
    # bool型をint型に変換
    df_numeric = df[numeric_columns].copy()
    for col in df_numeric.columns:
        if df_numeric[col].dtype == 'bool':
            df_numeric[col] = df_numeric[col].astype(int)
    
    if len(numeric_columns) >= 2:
        correlation_col1, correlation_col2 = st.columns(2)
        
        with correlation_col1:
            # 相関行列計算
            correlation_matrix = df_numeric.corr()
            
            # ヒートマップ作成
            fig1 = px.imshow(
                correlation_matrix,
                title="特徴量相関マトリックス",
                color_continuous_scale='RdBu_r',
                aspect='auto',
                zmin=-1,
                zmax=1
            )
            
            fig1.update_layout(height=500)
            st.plotly_chart(fig1, use_container_width=True)
        
        with correlation_col2:
            # 強い相関の特定
            strong_correlations = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) > 0.3:  # 閾値を0.5から0.3に下げて有用な相関も表示
                        strong_correlations.append({
                            '変数1': correlation_matrix.columns[i],
                            '変数2': correlation_matrix.columns[j],
                            '相関係数': round(corr_value, 3),
                            '相関強度': get_correlation_strength(abs(corr_value)),
                            '方向': '正' if corr_value > 0 else '負'
                        })
            
            # 相関の強さでソート
            strong_correlations = sorted(strong_correlations, key=lambda x: abs(x['相関係数']), reverse=True)
            
            if strong_correlations:
                st.markdown("### 🔍 検出された相関関係")
                
                # 上位5件を表示
                for i, corr in enumerate(strong_correlations[:5]):
                    strength_color = get_correlation_color(abs(corr['相関係数']))
                    st.markdown(f"""
                    <div style="background: {strength_color}; padding: 10px; margin: 5px 0; border-radius: 5px; color: white;">
                        <strong>{i+1}. {corr['変数1']} ↔ {corr['変数2']}</strong><br>
                        相関係数: {corr['相関係数']:.3f} ({corr['相関強度']}・{corr['方向']}の相関)
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("明確な相関関係（|r| > 0.3）は検出されませんでした")
        
        # 相関詳細データ
        if strong_correlations:
            st.subheader("📊 相関関係詳細データ")
            correlation_df = pd.DataFrame(strong_correlations)
            st.dataframe(correlation_df, use_container_width=True)
            
            # 相関関係の解釈
            st.subheader("💡 相関関係の解釈")
            
            interpretations = []
            for corr in strong_correlations[:3]:  # 上位3件のみ解釈
                var1, var2 = corr['変数1'], corr['変数2']
                corr_val = corr['相関係数']
                direction = "正" if corr_val > 0 else "負"
                
                interpretation = generate_correlation_interpretation(var1, var2, corr_val, direction)
                interpretations.append(interpretation)
            
            for interpretation in interpretations:
                st.info(interpretation)
    else:
        st.info("相関分析に十分な数値データがありません")

def get_correlation_strength(abs_corr):
    """相関の強さを判定"""
    if abs_corr >= 0.7:
        return "強い"
    elif abs_corr >= 0.5:
        return "中程度"
    elif abs_corr >= 0.3:
        return "弱い"
    else:
        return "非常に弱い"

def get_correlation_color(abs_corr):
    """相関の強さに応じた色を返す"""
    if abs_corr >= 0.7:
        return "#DC2626"  # 強い相関: 赤
    elif abs_corr >= 0.5:
        return "#F59E0B"  # 中程度: オレンジ
    elif abs_corr >= 0.3:
        return "#10B981"  # 弱い: 緑
    else:
        return "#6B7280"  # 非常に弱い: グレー

def generate_correlation_interpretation(var1, var2, corr_val, direction):
    """相関関係の解釈を生成"""
    abs_corr = abs(corr_val)
    strength = get_correlation_strength(abs_corr)
    
    # 変数名の日本語化（簡易版）
    var_translations = {
        'shopee_suitability_score': 'Shopee適性スコア',
        'prime_confidence_score': 'Prime信頼性スコア',
        'relevance_score': '関連性スコア',
        'ship_hours': '配送時間',
        'is_prime': 'Prime商品フラグ',
        'shopee_group': 'Shopeeグループ'
    }
    
    var1_jp = var_translations.get(var1, var1)
    var2_jp = var_translations.get(var2, var2)
    
    if direction == "正":
        return f"📈 **{var1_jp}**と**{var2_jp}**の間には{strength}{direction}の相関があります（r={corr_val:.3f}）。一方が高いと他方も高くなる傾向があります。"
    else:
        return f"📉 **{var1_jp}**と**{var2_jp}**の間には{strength}{direction}の相関があります（r={corr_val:.3f}）。一方が高いと他方は低くなる傾向があります。"