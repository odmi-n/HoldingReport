#!/usr/bin/env python3
"""
EDINET大量保有報告書スクレイピング実行スクリプト
"""

import sys
import os
import datetime

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 個別にモジュールをインポートして実行
def main():
    print("🚀 [main] 自動通知処理を開始します")
    
    # モジュールのインポート
    from src.core.hikariget import fetch_reports
    from src.core.parser import parse_and_filter_reports
    from src.core.notifier import send_line_message
    from src.utils.db import ReportDatabase
    from config.config import DOWNLOAD_DIR
    
    def check_database():
        """データベースの状態を確認"""
        print("🔍 データベース接続をチェック中...")
        try:
            db = ReportDatabase()
            report_counts = db.get_report_counts_by_type()
            total = sum(report_counts.values())
            print(f"✅ データベース接続成功: 合計{total}件のレコード")
            
            # レポートタイプごとの件数を表示
            for report_type, count in report_counts.items():
                print(f"  - {report_type}: {count}件")
            
            # 最新の5件を表示
            reports = db.search_reports(limit=5)
            if reports:
                print("\n📋 最新の5件:")
                for report in reports:
                    print(f"  - {report['target_company']} ({report['security_code']}) - {report['report_type']} - {report['processed_at']}")
            
            db.close()
            return True
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            return False

    # データベース接続を確認
    check_database()

    # 過去7日分の日付を検索（大量保有報告書は毎日提出されるわけではないため）
    from datetime import timedelta
    
    today = datetime.date.today()
    dates_to_search = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    print(f"📥 [main] 過去7日分の報告書を検索します: {dates_to_search[0]} ～ {dates_to_search[-1]}")
    
    # 1. EDINETから各日付のZipファイルを取得
    for target_date in dates_to_search:
        print(f"📥 [main] {target_date}の報告書を取得中...")
        fetch_reports(target_date)

    # 2. 解凍・パース・メッセージ整形（再通知除外もここで実施）
    print("🗂️ [main] ファイル解析中...")
    messages = parse_and_filter_reports(DOWNLOAD_DIR)

    # 3. 通知処理
    print("📡 [main] LINE通知を開始...")
    for message in messages:
        send_line_message(message)

    print("✅ [main] 全ての処理が完了しました。")

if __name__ == "__main__":
    main()
