import os
import sys
from pathlib import Path

import pandas as pd
import redis
import requests
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
RENDER_API_URL = os.getenv("RENDER_API_URL", "").strip()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()

if not DATABASE_URL:
    print("LOI: Chua co DATABASE_URL.")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "data" / "Tong_hop.xlsx"


def clear_remote_cache():
    if not RENDER_API_URL or not ADMIN_API_KEY:
        return

    endpoint = f"{RENDER_API_URL.rstrip('/')}/api/admin/clear-cache"
    try:
        response = requests.post(
            endpoint,
            headers={"X-Admin-Key": ADMIN_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        print("Da goi API xoa cache tren Render.")
    except Exception as exc:
        print(f"Canh bao: goi API xoa cache that bai: {exc}")


def clear_redis_direct():
    if not REDIS_URL:
        return

    try:
        client = redis.from_url(REDIS_URL)
        client.flushdb()
        print("Da don dep cache Redis truc tiep.")
    except Exception as exc:
        print(f"Canh bao: don Redis truc tiep that bai: {exc}")


def process_and_upload():
    print("Bat dau doc du lieu tu Excel...")

    if not EXCEL_PATH.exists():
        print(f"LOI: Khong tim thay file tai {EXCEL_PATH}")
        sys.exit(1)

    raw = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=None)
    header_idx = -1
    for idx, row in raw.iterrows():
        row_text = " ".join(row.astype(str).str.lower())
        if "sbd" in row_text and "họ" in row_text and "tên" in row_text:
            header_idx = idx
            break

    if header_idx == -1:
        print("LOI: Khong tim thay dong tieu de.")
        sys.exit(1)

    raw.columns = raw.iloc[header_idx].astype(str).str.replace("\n", " ").str.strip().str.lower()
    raw = raw.iloc[header_idx + 1 :].reset_index(drop=True)

    dataset = pd.DataFrame(
        {
            "sbd": raw.get("sbd", pd.Series(dtype=str)).astype(str),
            "ho_ten": raw.get("họ và tên", pd.Series(dtype=str)).astype(str),
            "ngay_sinh": raw.get("ngày sinh", pd.Series(dtype=str)).astype(str),
            "truong": raw.get("trường", pd.Series(dtype=str)).astype(str),
            "mon_thi": raw.get("môn thi", pd.Series(dtype=str)).astype(str),
            "diem": raw.get("điểm", pd.Series(dtype=str)),
            "xep_giai": raw.get("xếp giải", pd.Series(dtype=str)).astype(str),
            "gioi_tinh": raw.get("giới tính", pd.Series(dtype=str)).astype(str),
        }
    )

    dataset["sbd"] = dataset["sbd"].str.strip()
    dataset = dataset[~dataset["sbd"].isin(["", "nan", "None", "NaN"])]
    dataset = dataset[~dataset["sbd"].astype(str).str.lower().str.contains("sbd", na=False)]

    dataset["diem"] = dataset["diem"].astype(str).str.replace(",", ".", regex=False).str.strip()
    dataset["diem"] = pd.to_numeric(dataset["diem"], errors="coerce").fillna(0.0)
    dataset["xep_giai"] = dataset["xep_giai"].str.replace(r"(?i)^giải\s+", "", regex=True).str.strip()

    for col in ["ho_ten", "ngay_sinh", "truong", "mon_thi", "gioi_tinh", "xep_giai"]:
        dataset.loc[dataset[col].str.lower() == "nan", col] = ""

    dataset["percentile"] = dataset.groupby("mon_thi")["diem"].rank(pct=True, ascending=False).fillna(0.0)
    dataset["rank"] = dataset.groupby("mon_thi")["diem"].rank(method="min", ascending=False).fillna(0).astype(int)
    dataset["total_in_subject"] = dataset.groupby("mon_thi")["diem"].transform("count").fillna(0).astype(int)

    print(f"Dang day {len(dataset)} hoc sinh len database...")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        dataset.to_sql("students", con=connection, index=False, if_exists="replace")

        print("Dang tao lai khoa chinh cho bang students...")
        connection.execute(text("ALTER TABLE students ADD COLUMN id SERIAL PRIMARY KEY;"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_sbd ON students (sbd)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_ho_ten ON students (ho_ten)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_truong ON students (truong)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_mon_thi ON students (mon_thi)"))

    print("Day du lieu len database thanh cong.")
    clear_remote_cache()
    clear_redis_direct()


if __name__ == "__main__":
    process_and_upload()
