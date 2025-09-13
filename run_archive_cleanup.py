#!/usr/bin/env python3
"""
定期的なアーカイブクリーンアップジョブ

このスクリプトは以下の処理を実行します:
1. 古いファイルのアーカイブ
2. ストレージ使用量の最適化
3. 統計情報の出力

使用方法:
    python run_archive_cleanup.py [--dry-run] [--retention-days 90]
"""

import sys
import os
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.utils.archive_manager import ArchiveManager
from src.utils.db import ReportDatabase
from src.core.notifier import send_message
from config.config import ARCHIVE_POLICIES, DOWNLOAD_DIR

def main():
    parser = argparse.ArgumentParser(description='大量保有報告書アーカイブクリーンアップ')
    parser.add_argument('--dry-run', action='store_true', 
                       help='実際の処理を実行せず、実行予定の内容のみを表示')
    parser.add_argument('--retention-days', type=int, 
                       default=ARCHIVE_POLICIES['retention_periods']['medium_importance'],
                       help='基本保持期間（日数）')
    parser.add_argument('--notify', action='store_true',
                       help='処理結果をLINEに通知')
    
    args = parser.parse_args()
    
    print("🗂️  大量保有報告書アーカイブクリーンアップを開始します")
    print(f"設定: 基本保持期間 {args.retention_days}日")
    
    if args.dry_run:
        print("⚠️  ドライランモード: 実際の処理は実行されません")
    
    try:
        # アーカイブマネージャーの初期化
        archive_manager = ArchiveManager(
            download_dir=DOWNLOAD_DIR,
            archive_dir="data/archives"
        )
        
        # 現在の統計情報を取得
        print("\n📊 処理前の統計情報:")
        before_stats = archive_manager.get_archive_statistics()
        print_statistics(before_stats)
        
        if not args.dry_run:
            # アーカイブ処理の実行
            print(f"\n🗜️  アーカイブ処理を開始します（保持期間: {args.retention_days}日）")
            archive_stats = archive_manager.archive_files_by_importance(args.retention_days)
            
            # 処理結果の表示
            print("\n✅ アーカイブ処理完了")
            print(f"   📁 アーカイブ済み: {archive_stats['archived_count']}件")
            print(f"   ❌ 失敗: {archive_stats['failed_count']}件")
            print(f"   💾 節約容量: {archive_stats['total_size_saved'] / (1024*1024):.2f} MB")
            
            # 処理後の統計情報を取得
            print("\n📊 処理後の統計情報:")
            after_stats = archive_manager.get_archive_statistics()
            print_statistics(after_stats)
            
            # LINE通知の送信
            if args.notify:
                send_cleanup_notification(archive_stats, before_stats, after_stats)
        
        else:
            # ドライラン: アーカイブ対象を表示
            print("\n🔍 アーカイブ対象の確認（ドライラン）")
            show_archive_candidates(archive_manager, args.retention_days)
    
    except Exception as e:
        error_msg = f"❌ アーカイブ処理中にエラーが発生しました: {e}"
        print(error_msg)
        
        if args.notify:
            send_message(f"🚨 アーカイブクリーンアップエラー\n\n{error_msg}")
        
        sys.exit(1)
    
    print("\n🎉 アーカイブクリーンアップが正常に完了しました")

def print_statistics(stats):
    """統計情報を見やすく表示"""
    if not stats:
        print("   統計情報を取得できませんでした")
        return
    
    location_stats = stats.get('location_stats', {})
    
    print(f"   📁 アクティブファイル: {location_stats.get('active', {}).get('count', 0)}件")
    print(f"   🗜️  アーカイブファイル: {location_stats.get('archived', {}).get('count', 0)}件")
    print(f"   💾 総アーカイブサイズ: {stats.get('total_archive_size_mb', 0):.2f} MB")
    print(f"   📦 アーカイブファイル数: {stats.get('archive_file_count', 0)}個")

def show_archive_candidates(archive_manager, retention_days):
    """アーカイブ対象のファイルを表示（ドライラン用）"""
    try:
        # データベースからアーカイブ対象を取得
        db = ReportDatabase()
        
        # アーカイブ対象をマーク（実際には更新しない）
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = db.cursor
        cursor.execute('''
        SELECT report_id, target_company, security_code, holder_name, 
               processed_at, importance_level, change_percentage
        FROM processed_reports 
        WHERE processed_at < ? 
        AND file_location = 'active'
        ORDER BY importance_level, processed_at DESC
        ''', (cutoff_date,))
        
        candidates = cursor.fetchall()
        
        if candidates:
            print(f"   🎯 アーカイブ対象: {len(candidates)}件")
            print("\n   詳細:")
            
            for i, record in enumerate(candidates[:10], 1):  # 最初の10件のみ表示
                record_dict = dict(record)
                change_str = f" ({record_dict['change_percentage']:+.2f}%)" if record_dict['change_percentage'] else ""
                print(f"   {i:2d}. {record_dict['target_company']} - {record_dict['holder_name']}")
                print(f"       重要度: {record_dict['importance_level']}, 処理日: {record_dict['processed_at']}{change_str}")
            
            if len(candidates) > 10:
                print(f"   ... 他 {len(candidates) - 10} 件")
        else:
            print("   🎯 アーカイブ対象のファイルはありません")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ アーカイブ対象の確認中にエラー: {e}")

def send_cleanup_notification(archive_stats, before_stats, after_stats):
    """クリーンアップ結果をLINEに通知"""
    try:
        message = "🗂️ アーカイブクリーンアップ完了\n\n"
        message += f"📁 アーカイブ済み: {archive_stats['archived_count']}件\n"
        message += f"💾 節約容量: {archive_stats['total_size_saved'] / (1024*1024):.1f} MB\n"
        
        if archive_stats['failed_count'] > 0:
            message += f"❌ 失敗: {archive_stats['failed_count']}件\n"
        
        # 現在の統計
        after_location_stats = after_stats.get('location_stats', {})
        active_count = after_location_stats.get('active', {}).get('count', 0)
        archived_count = after_location_stats.get('archived', {}).get('count', 0)
        
        message += f"\n📊 現在の状況:\n"
        message += f"   アクティブ: {active_count}件\n"
        message += f"   アーカイブ: {archived_count}件\n"
        message += f"   総容量: {after_stats.get('total_archive_size_mb', 0):.1f} MB"
        
        send_message(message)
        print("📱 LINE通知を送信しました")
        
    except Exception as e:
        print(f"❌ LINE通知の送信に失敗しました: {e}")

if __name__ == "__main__":
    main()
