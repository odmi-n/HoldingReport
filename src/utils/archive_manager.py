import os
import tarfile
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from .db import ReportDatabase

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('archive_manager')

class ArchiveManager:
    def __init__(self, download_dir=None, archive_dir=None):
        """
        アーカイブ管理クラスの初期化
        Args:
            download_dir: ダウンロードディレクトリのパス
            archive_dir: アーカイブディレクトリのパス
        """
        self.download_dir = Path(download_dir) if download_dir else Path("data/downloads")
        self.archive_dir = Path(archive_dir) if archive_dir else Path("data/archives")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.db = ReportDatabase()
        
    def archive_files_by_importance(self, retention_days=90):
        """
        重要度に基づいてファイルをアーカイブ
        Args:
            retention_days: 基本保持期間（日数）
        Returns:
            dict: アーカイブ結果の統計
        """
        stats = {
            'archived_count': 0,
            'failed_count': 0,
            'total_size_saved': 0
        }
        
        try:
            # データベースでアーカイブ対象をマーク
            archived_count = self.db.archive_old_files(retention_days)
            logger.info(f"{archived_count}件のレコードがアーカイブ対象としてマークされました")
            
            # アーカイブ対象のファイルを取得
            archived_records = self._get_archived_records()
            
            for record in archived_records:
                try:
                    # 実際のディレクトリを探す
                    source_dir = self._find_source_directory(record)
                    if not source_dir:
                        logger.warning(f"対応するディレクトリが見つかりません: {record['report_id']}")
                        continue
                    
                    if source_dir.exists():
                        # アーカイブの実行
                        archive_success, size_saved = self._create_archive(record, source_dir)
                        
                        if archive_success:
                            stats['archived_count'] += 1
                            stats['total_size_saved'] += size_saved
                            
                            # 元ファイルを削除
                            shutil.rmtree(source_dir)
                            logger.info(f"アーカイブ完了: {doc_id}")
                        else:
                            stats['failed_count'] += 1
                    else:
                        logger.warning(f"ソースディレクトリが見つかりません: {source_dir}")
                        
                except Exception as e:
                    logger.error(f"アーカイブ処理中にエラー: {e}")
                    stats['failed_count'] += 1
            
            logger.info(f"アーカイブ処理完了 - 成功: {stats['archived_count']}件, 失敗: {stats['failed_count']}件")
            logger.info(f"節約されたディスク容量: {stats['total_size_saved'] / (1024*1024):.2f} MB")
            
        except Exception as e:
            logger.error(f"アーカイブ処理中にエラー: {e}")
        
        finally:
            self.db.close()
        
        return stats
    
    def _get_archived_records(self):
        """アーカイブ対象のレコードを取得"""
        try:
            cursor = self.db.cursor
            cursor.execute("""
            SELECT * FROM processed_reports 
            WHERE file_location = 'archived'
            ORDER BY processed_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"アーカイブ対象レコード取得エラー: {e}")
            return []
    
    def _find_source_directory(self, record):
        """
        レコードに対応する実際のソースディレクトリを探す
        Args:
            record: データベースレコード
        Returns:
            Path: 見つかったディレクトリのパス、見つからない場合はNone
        """
        try:
            # 既存の全ディレクトリを取得（logsディレクトリを除く）
            existing_dirs = [d for d in self.download_dir.iterdir() 
                           if d.is_dir() and d.name != 'logs']
            
            # まず、report_idから直接一致を試す
            report_id_parts = record['report_id'].split('_')
            possible_ids = [report_id_parts[0], record['report_id']]  # 企業コードや完全なID
            
            for possible_id in possible_ids:
                matching_dir = self.download_dir / possible_id
                if matching_dir.exists():
                    return matching_dir
            
            # 直接一致しない場合は、タイムスタンプで近いものを探す
            # processed_atから日付を抽出
            processed_date = record['processed_at'][:10]  # YYYY-MM-DD
            
            # 各ディレクトリの作成日時をチェック
            best_match = None
            min_time_diff = float('inf')
            
            for dir_path in existing_dirs:
                try:
                    # ディレクトリの作成時刻
                    dir_mtime = datetime.fromtimestamp(dir_path.stat().st_mtime)
                    dir_date = dir_mtime.strftime('%Y-%m-%d')
                    
                    # 処理日と近いディレクトリを探す
                    if dir_date == processed_date:
                        # 同じ日付のディレクトリ内にXBRLファイルがあるかチェック
                        if self._contains_relevant_xbrl(dir_path, record):
                            return dir_path
                        
                        # 時刻の差を計算
                        processed_time = datetime.strptime(record['processed_at'], '%Y-%m-%d %H:%M:%S')
                        time_diff = abs((dir_mtime - processed_time).total_seconds())
                        
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            best_match = dir_path
                
                except Exception as e:
                    logger.debug(f"ディレクトリチェック中にエラー: {dir_path} - {e}")
                    continue
            
            if best_match:
                logger.info(f"時刻ベースでマッチング: {record['report_id']} -> {best_match.name}")
                return best_match
            
            logger.warning(f"対応するディレクトリが見つかりませんでした: {record['report_id']}")
            return None
            
        except Exception as e:
            logger.error(f"ディレクトリ検索中にエラー: {e}")
            return None
    
    def _contains_relevant_xbrl(self, dir_path, record):
        """
        ディレクトリに関連するXBRLファイルが含まれているかチェック
        Args:
            dir_path: チェック対象のディレクトリ
            record: データベースレコード
        Returns:
            bool: 関連ファイルが含まれているかどうか
        """
        try:
            # XBRLディレクトリ内のファイルをチェック
            xbrl_dir = dir_path / "XBRL" / "PublicDoc"
            if not xbrl_dir.exists():
                return False
            
            # ヘッダーファイルや本文ファイルの存在をチェック
            header_files = list(xbrl_dir.glob('*header*.htm*'))
            honbun_files = list(xbrl_dir.glob('*honbun*.htm*'))
            
            return len(header_files) > 0 and len(honbun_files) > 0
            
        except Exception as e:
            logger.debug(f"XBRLファイルチェック中にエラー: {e}")
            return False
    
    def _create_archive(self, record, source_dir):
        """
        個別のアーカイブファイルを作成
        Args:
            record: データベースレコード
            source_dir: ソースディレクトリのパス
        Returns:
            tuple: (成功フラグ, 節約されたサイズ)
        """
        try:
            # アーカイブファイル名の生成
            year_month = record['processed_at'][:7]  # YYYY-MM
            archive_subdir = self.archive_dir / year_month
            archive_subdir.mkdir(parents=True, exist_ok=True)
            
            archive_filename = f"{record['report_id']}.tar.gz"
            archive_path = archive_subdir / archive_filename
            
            # 元ファイルサイズを計算
            original_size = self._get_directory_size(source_dir)
            
            # メタデータの準備
            metadata = {
                'report_info': record,
                'archive_date': datetime.now().isoformat(),
                'original_path': str(source_dir),
                'original_size': original_size,
                'archive_reason': self._get_archive_reason(record)
            }
            
            # アーカイブの作成
            with tarfile.open(archive_path, 'w:gz') as tar:
                # メインディレクトリを追加
                tar.add(source_dir, arcname=source_dir.name)
                
                # メタデータファイルを一時作成して追加
                metadata_file = source_dir.parent / f"{source_dir.name}_metadata.json"
                import json
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                tar.add(metadata_file, arcname=f"{source_dir.name}_metadata.json")
                metadata_file.unlink()  # 一時ファイルを削除
            
            # 圧縮後のサイズ
            compressed_size = archive_path.stat().st_size
            size_saved = original_size - compressed_size
            
            # データベースのfile_locationを更新
            self.db.cursor.execute("""
            UPDATE processed_reports 
            SET file_location = ? 
            WHERE report_id = ?
            """, (str(archive_path), record['report_id']))
            self.db.conn.commit()
            
            logger.info(f"アーカイブ作成完了: {archive_path}")
            logger.info(f"圧縮率: {(size_saved/original_size)*100:.1f}% ({original_size} -> {compressed_size} bytes)")
            
            return True, size_saved
            
        except Exception as e:
            logger.error(f"アーカイブ作成エラー: {e}")
            return False, 0
    
    def _get_directory_size(self, directory):
        """ディレクトリのサイズを計算"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def _get_archive_reason(self, record):
        """アーカイブ理由を生成"""
        if record['report_type'] == '変更報告書' and record['change_percentage']:
            return f"変更幅: {record['change_percentage']:+.2f}%"
        elif record['holding_ratio_after']:
            return f"保有割合: {record['holding_ratio_after']:.2f}%"
        else:
            return f"重要度レベル: {record['importance_level']}"
    
    def restore_from_archive(self, report_id):
        """
        アーカイブからファイルを復元
        Args:
            report_id: 復元対象の報告書ID
        Returns:
            bool: 復元の成功/失敗
        """
        try:
            # データベースからアーカイブ場所を取得
            cursor = self.db.cursor
            cursor.execute("""
            SELECT file_location FROM processed_reports 
            WHERE report_id = ? AND file_location LIKE '%.tar.gz'
            """, (report_id,))
            
            result = cursor.fetchone()
            if not result:
                logger.error(f"アーカイブファイルが見つかりません: {report_id}")
                return False
            
            archive_path = Path(result[0])
            if not archive_path.exists():
                logger.error(f"アーカイブファイルが存在しません: {archive_path}")
                return False
            
            # 復元先ディレクトリ
            restore_dir = self.download_dir
            
            # アーカイブを展開
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(restore_dir)
            
            # データベースのfile_locationを更新
            cursor.execute("""
            UPDATE processed_reports 
            SET file_location = 'active' 
            WHERE report_id = ?
            """, (report_id,))
            self.db.conn.commit()
            
            logger.info(f"復元完了: {report_id}")
            return True
            
        except Exception as e:
            logger.error(f"復元処理中にエラー: {e}")
            return False
    
    def get_archive_statistics(self):
        """アーカイブの統計情報を取得"""
        try:
            cursor = self.db.cursor
            
            # 基本統計
            cursor.execute("""
            SELECT 
                file_location,
                COUNT(*) as count,
                AVG(importance_level) as avg_importance
            FROM processed_reports 
            GROUP BY file_location
            """)
            
            location_stats = {}
            for row in cursor.fetchall():
                location_stats[row[0]] = {
                    'count': row[1],
                    'avg_importance': row[2]
                }
            
            # アーカイブサイズの計算
            total_archive_size = 0
            archive_count = 0
            
            for archive_file in self.archive_dir.glob('**/*.tar.gz'):
                total_archive_size += archive_file.stat().st_size
                archive_count += 1
            
            return {
                'location_stats': location_stats,
                'total_archive_size_mb': total_archive_size / (1024 * 1024),
                'archive_file_count': archive_count
            }
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            return {}

# 使用例とテスト用のメイン関数
if __name__ == "__main__":
    archive_manager = ArchiveManager()
    
    # アーカイブ実行
    stats = archive_manager.archive_files_by_importance(retention_days=30)
    print(f"アーカイブ統計: {stats}")
    
    # 統計情報の表示
    archive_stats = archive_manager.get_archive_statistics()
    print(f"アーカイブ統計情報: {archive_stats}")
