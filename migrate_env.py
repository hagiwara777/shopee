#!/usr/bin/env python3
import os
import re

def migrate_env():
    """現在の.envから新形式に移行"""
    
    # 現在の.envを読み込み  
    old_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    old_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        print("❌ .envファイルが見つかりません")
        return False
    
    # 移行マッピング
    migration_map = {
        # 旧形式 → 新形式（SP_API_プレフィックス）
        'LWA_APP_ID': 'SP_API_LWA_APP_ID',
        'LWA_CLIENT_SECRET': 'SP_API_LWA_CLIENT_SECRET',
        'SP_API_REFRESH_TOKEN': 'SP_API_LWA_REFRESH_TOKEN',
        'REFRESH_TOKEN': 'SP_API_LWA_REFRESH_TOKEN',
        
        # AWS関連
        'AWS_ACCESS_KEY': 'SP_API_AWS_ACCESS_KEY',
        'AWS_SECRET_KEY': 'SP_API_AWS_SECRET_KEY', 
        'ROLE_ARN': 'SP_API_ROLE_ARN',
        
        # その他はそのまま
        'OPENAI_API_KEY': 'OPENAI_API_KEY',
        'GEMINI_API_KEY': 'GEMINI_API_KEY',
    }
    
    # 新しい.envファイル生成
    new_env_lines = [
        "# SP-API認証情報（python-amazon-sp-api標準形式）",
        "# 自動移行により生成",
        ""
    ]
    
    print("🔄 環境変数移行作業：")
    
    # SP-API関連
    sp_api_vars = [
        ('SP_API_LWA_APP_ID', 'LWA App ID'),
        ('SP_API_LWA_CLIENT_SECRET', 'LWA Client Secret'),
        ('SP_API_LWA_REFRESH_TOKEN', 'Refresh Token'),
        ('SP_API_AWS_ACCESS_KEY', 'AWS Access Key'),
        ('SP_API_AWS_SECRET_KEY', 'AWS Secret Key'),
        ('SP_API_ROLE_ARN', 'Role ARN')
    ]
    
    for new_key, description in sp_api_vars:
        # 旧形式から値を探す
        old_value = None
        for old_key, value in old_vars.items():
            if migration_map.get(old_key) == new_key:
                old_value = value
                break
        
        if old_value:
            new_env_lines.append(f"{new_key}={old_value}")
            print(f"   ✅ {description}: {old_key} → {new_key}")
        else:
            new_env_lines.append(f"# {new_key}=your_{new_key.lower()}_here")
            print(f"   ⚠️ {description}: 値なし（コメントアウト）")
    
    new_env_lines.extend([
        "",
        "# その他のAPI Keys",
    ])
    
    # その他のキー
    other_keys = ['OPENAI_API_KEY', 'GEMINI_API_KEY']
    for key in other_keys:
        if key in old_vars:
            new_env_lines.append(f"{key}={old_vars[key]}")
            print(f"   ✅ {key}: そのまま移行")
        else:
            new_env_lines.append(f"# {key}=your_{key.lower()}_here")
            print(f"   ⚠️ {key}: 値なし（コメントアウト）")
    
    # 新しい.envファイルに書き出し
    with open('.env', 'w') as f:
        f.write('\n'.join(new_env_lines))
    
    print(f"\n✅ .env移行完了！新しい環境変数数: {len([l for l in new_env_lines if '=' in l and not l.startswith('#')])}")
    return True

if __name__ == "__main__":
    migrate_env()
