import os
from dotenv import load_dotenv

# .envを読み込む（ローカル実行時のみ必要）
load_dotenv()

# === 共通設定 ===
EDINET_CODE = os.getenv("EDINET_CODE", "E35239")  # 光通信のコード
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "data/downloads")

# LINE API関連
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# アーカイブポリシー設定
ARCHIVE_POLICIES = {
    'significant_change_threshold': 1.5,  # 重要な変更とみなす閾値（%）
    'high_holding_threshold': 10.0,       # 高保有割合の閾値（%）
    'retention_periods': {
        'low_importance': 30,      # 低重要度データの保持期間（日数）
        'medium_importance': 90,   # 中重要度データの保持期間（日数）
        'high_importance': 180     # 高重要度データの保持期間（日数）
    },
    'compression_enabled': True,           # 圧縮を有効にするかどうか
    'auto_cleanup_enabled': True          # 自動クリーンアップを有効にするかどうか
}
