#!/usr/bin/env python3
"""
アーカイブ機能のテストスクリプト
LINE通知なしでアーカイブ機能をテストします
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.utils.archive_manager import ArchiveManager
from src.utils.db import ReportDatabase

def test_archive_functionality():
    """アーカイブ機能のテスト"""
    print("🧪 アーカイブ機能テスト開始")
    
    try:
        # データベース接続テスト
        print("\n1️⃣ データベース接続テスト")
        db = ReportDatabase()
        
        # 現在のレコード状況を確認
        db.cursor.execute('SELECT COUNT(*) FROM processed_reports')
        total_count = db.cursor.fetchone()[0]
        print(f"📊 総レコード数: {total_count}件")
        
        # file_locationの状況を確認
        db.cursor.execute('SELECT file_location, COUNT(*) FROM processed_reports GROUP BY file_location')
        location_stats = db.cursor.fetchall()
        print("📁 ファイル場所別統計:")
        for location, count in location_stats:
            print(f"  - {location}: {count}件")
        
        db.close()
        
        # アーカイブマネージャーのテスト
        print("\n2️⃣ アーカイブマネージャー初期化テスト")
        archive_manager = ArchiveManager(
            download_dir="data/downloads",
            archive_dir="data/archives"
        )
        print("✅ アーカイブマネージャー初期化成功")
        
        # 統計情報の取得テスト
        print("\n3️⃣ 統計情報取得テスト")
        stats = archive_manager.get_archive_statistics()
        print("📊 現在の統計情報:")
        print(f"  - アーカイブディレクトリサイズ: {stats.get('total_archive_size_mb', 0):.2f} MB")
        print(f"  - アーカイブファイル数: {stats.get('archive_file_count', 0)}個")
        
        location_stats = stats.get('location_stats', {})
        for location, data in location_stats.items():
            print(f"  - {location}: {data.get('count', 0)}件")
        
        # ドライラン: アーカイブ対象の確認
        print("\n4️⃣ アーカイブ対象の確認（ドライラン）")
        print("保持期間を1日に設定してテスト...")
        
        from datetime import datetime, timedelta
        retention_days = 1
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"カットオフ日時: {cutoff_date}")
        
        db = ReportDatabase()
        cursor = db.cursor
        cursor.execute('''
        SELECT report_id, target_company, security_code, holder_name, 
               processed_at, importance_level, file_location
        FROM processed_reports 
        WHERE processed_at < ? 
        AND file_location = 'active'
        ORDER BY processed_at DESC
        ''', (cutoff_date,))
        
        candidates = cursor.fetchall()
        print(f"🎯 アーカイブ対象: {len(candidates)}件")
        
        if candidates:
            print("\n詳細（最初の5件）:")
            for i, record in enumerate(candidates[:5], 1):
                record_dict = dict(zip([col[0] for col in cursor.description], record))
                print(f"  {i}. {record_dict['target_company']} - {record_dict['holder_name']}")
                print(f"     ID: {record_dict['report_id']}")
                print(f"     処理日: {record_dict['processed_at']}")
                print(f"     重要度: {record_dict['importance_level']}")
                print()
        
        db.close()
        
        # ダウンロードディレクトリの確認
        print("5️⃣ ダウンロードディレクトリの確認")
        download_dir = Path("data/downloads")
        if download_dir.exists():
            dirs = [d for d in download_dir.iterdir() if d.is_dir() and d.name != 'logs']
            print(f"📁 ダウンロードディレクトリ数: {len(dirs)}個")
            
            total_size = 0
            for d in dirs:
                size = sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
                total_size += size
            
            print(f"💾 総サイズ: {total_size / (1024*1024):.2f} MB")
            
            if dirs:
                print("ディレクトリ例（最初の3個）:")
                for d in dirs[:3]:
                    size = sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
                    file_count = len([f for f in d.rglob('*') if f.is_file()])
                    print(f"  - {d.name}: {file_count}ファイル, {size / 1024:.1f} KB")
        
        print("\n✅ アーカイブ機能テスト完了")
        print("\n次のステップ:")
        print("  1. 実際のアーカイブ実行: python test_archive.py --execute")
        print("  2. 本格的なアーカイブ: python run_archive_cleanup.py --dry-run")
        print("  3. 統計情報確認: python test_archive.py --stats")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def execute_archive(retention_days=1):
    """実際のアーカイブ処理を実行"""
    print(f"🗜️  実際のアーカイブ処理を実行（保持期間: {retention_days}日）")
    
    try:
        archive_manager = ArchiveManager(
            download_dir="data/downloads",
            archive_dir="data/archives"
        )
        
        # アーカイブ実行
        stats = archive_manager.archive_files_by_importance(retention_days)
        
        print("✅ アーカイブ処理完了")
        print(f"  📁 アーカイブ済み: {stats['archived_count']}件")
        print(f"  ❌ 失敗: {stats['failed_count']}件")
        print(f"  💾 節約容量: {stats['total_size_saved'] / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ アーカイブ実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_statistics():
    """統計情報を表示"""
    print("📊 システム統計情報")
    
    try:
        # データベース統計
        db = ReportDatabase()
        
        db.cursor.execute('SELECT COUNT(*) FROM processed_reports')
        total_count = db.cursor.fetchone()[0]
        
        db.cursor.execute('SELECT file_location, COUNT(*) FROM processed_reports GROUP BY file_location')
        location_stats = db.cursor.fetchall()
        
        db.cursor.execute('SELECT report_type, COUNT(*) FROM processed_reports GROUP BY report_type')
        type_stats = db.cursor.fetchall()
        
        print(f"\n📋 データベース統計:")
        print(f"  総レコード数: {total_count}件")
        
        print("  ファイル場所別:")
        for location, count in location_stats:
            print(f"    - {location}: {count}件")
        
        print("  報告書種別:")
        for report_type, count in type_stats:
            print(f"    - {report_type}: {count}件")
        
        db.close()
        
        # ファイルシステム統計
        download_dir = Path("data/downloads")
        archive_dir = Path("data/archives")
        
        print(f"\n💾 ストレージ統計:")
        
        if download_dir.exists():
            active_dirs = [d for d in download_dir.iterdir() if d.is_dir() and d.name != 'logs']
            active_size = 0
            for d in active_dirs:
                active_size += sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
            
            print(f"  アクティブファイル:")
            print(f"    - ディレクトリ数: {len(active_dirs)}個")
            print(f"    - 総サイズ: {active_size / (1024*1024):.2f} MB")
        
        if archive_dir.exists():
            archive_files = list(archive_dir.glob('**/*.tar.gz'))
            archive_size = sum(f.stat().st_size for f in archive_files)
            
            print(f"  アーカイブファイル:")
            print(f"    - ファイル数: {len(archive_files)}個")
            print(f"    - 総サイズ: {archive_size / (1024*1024):.2f} MB")
            
            if len(archive_files) > 0 and active_size > 0:
                total_size = active_size + archive_size
                print(f"  全体:")
                print(f"    - 総サイズ: {total_size / (1024*1024):.2f} MB")
                print(f"    - アーカイブ率: {(archive_size / total_size) * 100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 統計情報取得中にエラー: {e}")
        return False

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='アーカイブ機能テスト・管理')
    parser.add_argument('--execute', action='store_true', help='実際のアーカイブを実行')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    parser.add_argument('--retention-days', type=int, default=1, help='保持期間（日数）')
    
    args = parser.parse_args()
    
    if args.stats:
        success = show_statistics()
    elif args.execute:
        success = execute_archive(args.retention_days)
    else:
        success = test_archive_functionality()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
