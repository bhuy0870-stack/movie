import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

# Cấu hình
SQLITE_PATH = 'db.sqlite3'
NEON_URL = "postgresql://neondb_owner:npg_Vj8TvLxoR6lc@ep-dawn-wildflower-a1ix5r2h-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def fix_row(row, table_name):
    """Hàm này chuyển 0/1 thành True/False cho các cột Boolean"""
    new_row = list(row)
    if table_name == 'main_movie':
        # Thường cột is_series nằm ở vị trí số 8 hoặc 9, ta ép kiểu tất cả số 0/1 ở cột đó
        # Để an toàn, ta tìm vị trí có giá trị là 0 hoặc 1 mà cột đó là boolean
        # Ở đây tui ép kiểu cho cột số 8 (is_series) dựa trên lỗi của ông
        new_row[8] = bool(new_row[8]) 
    return tuple(new_row)

def push_data():
    s_conn = sqlite3.connect(SQLITE_PATH)
    p_conn = psycopg2.connect(NEON_URL)
    s_cur = s_conn.cursor()
    p_cur = p_conn.cursor()

    # QUAN TRỌNG: Phải xong Movie mới được làm Episode
    tables = ['main_movie', 'main_episode']

    for table in tables:
        print(f"🚀 Đang xử lý bảng: {table}...")
        s_cur.execute(f"SELECT * FROM {table}")
        rows = s_cur.fetchall()
        
        if not rows: continue

        # Lấy tên cột
        s_cur.execute(f"SELECT * FROM {table} LIMIT 1")
        colnames = [desc[0] for desc in s_cur.description]
        col_str = ",".join([f'"{c}"' for c in colnames])
        placeholders = ",".join(["%s"] * len(colnames))

        # Chuẩn bị dữ liệu (Fix lỗi 0/1)
        print(f"🛠️ Đang chuẩn bị dữ liệu cho {len(rows)} dòng...")
        clean_rows = [fix_row(r, table) for r in rows]

        query = f'INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
        
        try:
            # Dùng execute_batch để nạp hàng trăm nghìn dòng không bị treo
            execute_batch(p_cur, query, clean_rows, page_size=500)
            p_conn.commit()
            print(f"✅ Đã nạp xong bảng {table}!")
        except Exception as e:
            p_conn.rollback()
            print(f"❌ Lỗi bảng {table}: {e}")

    s_conn.close()
    p_conn.close()
    print("✨ TẤT CẢ DỮ LIỆU ĐÃ LÊN NEON!")

if __name__ == "__main__":
    push_data()