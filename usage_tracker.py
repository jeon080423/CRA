import sqlite3
import datetime
import pandas as pd
import os

class UsageTracker:
    def __init__(self, db_path="usage_tracker.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """데이터베이스 및 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                event_type TEXT,
                section_name TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_event(self, user_id, event_type, section_name=""):
        """이벤트 로깅 (LOGIN, ACCESS 등)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usage_logs (user_id, event_type, section_name)
                VALUES (?, ?, ?)
            ''', (user_id, event_type, section_name))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Logging error: {e}")

    def get_summary_data(self):
        """관리자 대시보드용 요약 데이터 반환"""
        if not os.path.exists(self.db_path):
            return pd.DataFrame(), pd.DataFrame()

        conn = sqlite3.connect(self.db_path)
        
        # 1. 일별 로그인 추이
        df_login = pd.read_sql_query('''
            SELECT date(timestamp) as date, count(*) as count
            FROM usage_logs
            WHERE event_type = 'LOGIN'
            GROUP BY date(timestamp)
            ORDER BY date
        ''', conn)

        # 2. 섹션별 사용 현황 (당일)
        today = datetime.date.today().isoformat()
        df_section = pd.read_sql_query(f'''
            SELECT section_name, count(*) as count
            FROM usage_logs
            WHERE event_type = 'ACCESS' AND date(timestamp) = '{today}'
            GROUP BY section_name
        ''', conn)
        
        # 3. 전체 로그 (최근 100건)
        df_all = pd.read_sql_query('''
            SELECT timestamp, user_id, event_type, section_name
            FROM usage_logs
            ORDER BY timestamp DESC
            LIMIT 100
        ''', conn)

        conn.close()
        return df_login, df_section, df_all
