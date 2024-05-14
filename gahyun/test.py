import sqlite3

# SQLite 데이터베이스 연결
conn = sqlite3.connect('main.db')

# 커서 생성
cursor = conn.cursor()

# 테이블 생성 쿼리
create_table_query = '''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER
)
'''

# 테이블 생성
cursor.execute(create_table_query)

# 연결 및 트랜잭션 커밋
conn.commit()

# 연결 종료
conn.close()
