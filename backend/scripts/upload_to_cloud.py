#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 1. TẢI BIẾN MÔI TRƯỜNG TỪ FILE .ENV (Bảo mật, không hardcode password)
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    print("❌ LỖI: Chưa có biến DATABASE_URL trong file .env")
    sys.exit(1)

# Ép dùng driver đồng bộ `psycopg` (vì script này chạy tuần tự, không cần async)
DB_URL = DB_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://")

# 2. CẤU HÌNH THÔNG SỐ
FILE_PATH = "output/Tong_hop.xlsx"  # File tổng hợp mà tool cào sinh ra
TABLE_NAME = "students"             # Tên bảng trong Database của sếp

# Mapping: Cột Excel (Tiếng Việt) -> Cột Database (Sếp tự chỉnh lại vế phải cho đúng DB nhé)
COLUMN_MAPPING = {
    "SBD": "sbd",
    "Họ và tên": "ho_ten",
    "Ngày sinh": "ngay_sinh",
    "Giới tính": "gioi_tinh",
    "Lớp": "lop",
    "Trường": "truong",
    "Môn thi": "mon_thi",
    "Điểm": "diem",
    "Xếp giải": "xep_giai"
}

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Hàm chuẩn hóa và làm sạch dữ liệu trước khi đẩy lên DB"""
    # 0. Chuẩn hóa header Excel: xóa khoảng trắng thừa
    df.columns = df.columns.str.strip()

    # 1. Đổi tên cột chuẩn xác
    df = df.rename(columns=COLUMN_MAPPING)
    
    # 2. Lọc bỏ các cột thừa (chỉ giữ lại những cột có trong DB)
    db_cols = list(COLUMN_MAPPING.values())
    df = df[[col for col in db_cols if col in df.columns]]
    
    # 3. Chuẩn hóa cột Điểm (đổi dấu phẩy thành dấu chấm, ép kiểu số thực)
    if "diem" in df.columns:
        df["diem"] = df["diem"].astype(str).str.replace(",", ".").str.replace(" ", "")
        df["diem"] = pd.to_numeric(df["diem"], errors="coerce") # Lỗi tự thành NaN
        
    # 4. Biến NaN/rỗng thành None/NULL để PostgreSQL lưu đúng kiểu dữ liệu
    df = df.replace({float("nan"): None, "": None})
    df = df.where(pd.notnull(df), None)
    
    return df

def main():
    print(f"🚀 Bắt đầu tiến trình ETL dữ liệu từ {FILE_PATH}...")

    if not os.path.exists(FILE_PATH):
        print(f"❌ LỖI: Không tìm thấy file {FILE_PATH}. Sếp chạy tool cào điểm trước nhé!")
        sys.exit(1)

    # BƯỚC 1: ĐỌC DỮ LIỆU
    print("📖 Đang đọc file Excel...")
    df = pd.read_excel(FILE_PATH)
    print(f"✅ Đã tải {len(df):,} dòng dữ liệu vào RAM.")

    # BƯỚC 2: CLEAN DATA
    print("🧹 Đang dọn dẹp và chuẩn hóa dữ liệu...")
    df = clean_data(df)

    # BƯỚC 3: KẾT NỐI DB VÀ UPLOAD
    print("🔌 Đang khởi tạo kết nối tới Supabase...")
    engine = create_engine(DB_URL, pool_pre_ping=True, echo=False)

    try:
        with engine.begin() as conn:  # Tự động Transaction: Thành công thì Commit, lỗi thì Rollback toàn bộ
            
            # --- TÙY CHỌN 1: XÓA SẠCH DATA CŨ TRƯỚC KHI NẠP MỚI ---
            # (NẾU SẾP MUỐN XÓA DATA CŨ CỦA HSG 11 ĐỂ THAY BẰNG HSG 10 THÌ BỎ COMMENT 2 DÒNG DƯỚI)
            print(f"🗑️ Đang xóa dữ liệu cũ trong bảng '{TABLE_NAME}'...")
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} RESTART IDENTITY;"))
            
            print(f"⏳ Đang Bơm dữ liệu lên bảng '{TABLE_NAME}' (Batch Insert)...")
            
            # method='multi': Gộp nhiều lệnh INSERT thành 1 câu SQL khổng lồ
            # chunksize=500: Cứ 500 dòng đẩy 1 lần, không làm tràn RAM hay timeout DB
            df.to_sql(
                name=TABLE_NAME,
                con=conn,
                if_exists="append", 
                index=False,
                method="multi",
                chunksize=500
            )
            
            print(f"🎉 THÀNH CÔNG RỰC RỠ! Đã lưu an toàn {len(df):,} học sinh vào Database.")
            
    except Exception as e:
        print(f"❌ LỖI RỒI SẾP ƠI (Transaction đã được Rollback):\n{e}")
    finally:
        engine.dispose()
        print("🔒 Đã đóng kết nối Database an toàn.")

if __name__ == "__main__":
    main()
