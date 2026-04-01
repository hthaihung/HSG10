import os
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
import redis

# 1. SETUP MÔI TRƯỜNG
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not DATABASE_URL:
    print("❌ LỖI: Chưa có DATABASE_URL.")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "data" / "Tong_hop.xlsx"

def process_and_upload():
    print("🚀 BẮT ĐẦU ĐỌC DỮ LIỆU TỪ EXCEL...")
    
    if not EXCEL_PATH.exists():
        print(f"❌ LỖI: Không tìm thấy file tại {EXCEL_PATH}")
        sys.exit(1)

    # 1. DÒ TÌM HEADER ĐỘNG
    raw = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=None)
    header_idx = -1
    for i, row in raw.iterrows():
        row_text = " ".join(row.astype(str).str.lower())
        if "sbd" in row_text and "họ" in row_text and "tên" in row_text:
            header_idx = i
            break
            
    if header_idx == -1:
        print("❌ LỖI: Không tìm thấy dòng tiêu đề!")
        sys.exit(1)
        
    # 2. ÉP TÊN CỘT VÀ CHẶT PHẦN ĐẦU THỪA
    raw.columns = raw.iloc[header_idx].astype(str).str.replace('\n', ' ').str.strip().str.lower()
    raw = raw.iloc[header_idx + 1:].reset_index(drop=True)
    
    # 3. ĐÓNG GÓI DỮ LIỆU
    dataset = pd.DataFrame({
        "sbd": raw.get("sbd", pd.Series(dtype=str)).astype(str),
        "ho_ten": raw.get("họ và tên", pd.Series(dtype=str)).astype(str),
        "ngay_sinh": raw.get("ngày sinh", pd.Series(dtype=str)).astype(str),
        "truong": raw.get("trường", pd.Series(dtype=str)).astype(str),
        "mon_thi": raw.get("môn thi", pd.Series(dtype=str)).astype(str),
        "diem": raw.get("điểm", pd.Series(dtype=str)), 
        "xep_giai": raw.get("xếp giải", pd.Series(dtype=str)).astype(str),
        "gioi_tinh": raw.get("giới tính", pd.Series(dtype=str)).astype(str),
    })

    # 4. BỘ LỌC RÁC TỐI THƯỢNG
    dataset["sbd"] = dataset["sbd"].str.strip()
    dataset = dataset[~dataset["sbd"].isin(["", "nan", "None", "NaN"])]
    # Cắt dòng chứa chữ "sbd" bị lặp
    dataset = dataset[~dataset["sbd"].astype(str).str.lower().str.contains("sbd", na=False)]

    # 5. XỬ LÝ SỐ LIỆU
    dataset["diem"] = dataset["diem"].astype(str).str.replace(",", ".", regex=False).str.strip()
    dataset["diem"] = pd.to_numeric(dataset["diem"], errors="coerce").fillna(0.0)
    dataset["xep_giai"] = dataset["xep_giai"].str.replace(r"(?i)^giải\s+", "", regex=True).str.strip()
    
    for col in ["ho_ten", "ngay_sinh", "truong", "mon_thi", "gioi_tinh", "xep_giai"]:
        dataset.loc[dataset[col].str.lower() == "nan", col] = ""

    dataset["percentile"] = dataset.groupby("mon_thi")["diem"].rank(pct=True, ascending=False).fillna(0.0)
    dataset["rank"] = dataset.groupby("mon_thi")["diem"].rank(method="min", ascending=False).fillna(0).astype(int)
    dataset["total_in_subject"] = dataset.groupby("mon_thi")["diem"].transform("count").fillna(0).astype(int)

    print(f"☁️ Đang đẩy {len(dataset)} học sinh xịn lên Database...")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        # Lệnh replace sẽ tạo lại bảng mới
        dataset.to_sql("students", con=connection, index=False, if_exists="replace")
        
        # 🔥 ĐÂY LÀ DÒNG FIX LỖI SUPABASE CHO SẾP: Tự động thêm cột ID khóa chính
        print("🔧 Đang tạo lại Khóa chính (Primary Key) cho Supabase...")
        connection.execute(text("ALTER TABLE students ADD COLUMN id SERIAL PRIMARY KEY;"))
        
        # Tạo index
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_sbd ON students (sbd)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_ho_ten ON students (ho_ten)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_truong ON students (truong)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_mon_thi ON students (mon_thi)"))

    print("✅ Đẩy dữ liệu lên Database THÀNH CÔNG RỰC RỠ!")

    if REDIS_URL:
        try:
            r = redis.from_url(REDIS_URL)
            r.flushdb()
            print("✅ Đã dọn dẹp Cache cũ!")
        except Exception as e:
            pass

if __name__ == "__main__":
    process_and_upload()