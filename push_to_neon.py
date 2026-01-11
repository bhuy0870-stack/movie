import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

# Cấu hình
SQLITE_PATH = 'db.sqlite3'
NEON_URL = "postgresql://neondb_owner:npg_Vj8TvLxoR6lc@ep-dawn-wildflower-a1ix5r2h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def push_data():
    s_conn = sqlite3.connect(SQLITE_PATH)
    p_conn = psycopg2.connect(NEON_URL)
    s_cur = s_conn.cursor()
    p_cur = p_conn.cursor()

    tables = ['main_movie', 'main_episode']

    for table in tables:
        print(f"🚀 Đang xử lý bảng: {table}...")
        
        # 1. Lấy dữ liệu và tên cột từ SQLite
        s_cur.execute(f"SELECT * FROM {table}")
        rows = s_cur.fetchall()
        colnames = [desc[0] for desc in s_cur.description]
        
        if not rows: continue

        # 2. Tìm vị trí cột 'is_series' để ép kiểu
        is_series_idx = None
        if 'is_series' in colnames:
            is_series_idx = colnames.index('is_series')
            print(f"🔍 Đã tìm thấy cột 'is_series' tại vị trí: {is_series_idx}")

        # 3. Chuẩn bị dữ liệu sạch
        clean_rows = []
        for r in rows:
            new_row = list(r)
            if is_series_idx is not None:
                # Chuyển 0/1 thành True/False đúng kiểu Postgres cần
                new_row[is_series_idx] = True if new_row[is_series_idx] == 1 else False
            clean_rows.append(tuple(new_row))

        # 4. Tạo câu lệnh SQL
        col_str = ",".join([f'"{c}"' for c in colnames])
        placeholders = ",".join(["%s"] * len(colnames))
        query = f'INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
        
        print(f"📦 Đang nạp {len(clean_rows)} dòng...")
        try:
            # Chia nhỏ để nạp cho an toàn
            execute_batch(p_cur, query, clean_rows, page_size=200)
            p_conn.commit()
            print(f"✅ Thành công bảng {table}!")
        except Exception as e:
            p_conn.rollback()
            print(f"❌ Lỗi bảng {table}: {e}")

    s_conn.close()
    p_conn.close()
    print("✨ XONG RỒI! KIỂM TRA WEB ĐI HUY ƠI!")

if __name__ == "__main__":
    push_data()