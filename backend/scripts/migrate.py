import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

PRIZE_LEVELS = ["Nhất", "Nhì", "Ba", "Khuyến khích"]

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "data" / "Tong_hop.xlsx"
SQLITE_PATH = BASE_DIR / "data" / "students.db"


def normalize_strings(series: pd.Series) -> pd.Series:
    clean = series.astype(str).str.strip()
    clean = clean.replace({"nan": "", "NaN": "", "None": ""})
    return clean.fillna("")


def migrate() -> None:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}")

    raw = pd.read_excel(EXCEL_PATH, engine="openpyxl", header=1)
    raw.columns = raw.columns.astype(str).str.strip()

    drop_cols = [c for c in ["SBD", "Họ và tên"] if c in raw.columns]
    if drop_cols:
        raw.dropna(subset=drop_cols, inplace=True)
        for column in drop_cols:
            raw = raw[raw[column].astype(str).str.strip() != ""]

    if "Điểm" in raw.columns:
        raw["Điểm"] = (
            raw["Điểm"].astype(str).str.replace(",", ".", regex=False).str.strip()
        )
        raw["Điểm"] = pd.to_numeric(raw["Điểm"], errors="coerce").fillna(0.0)
    else:
        raw["Điểm"] = 0.0

    for column in ["Môn thi", "Trường", "Xếp giải", "Giới tính", "Họ và tên", "SBD", "Ngày sinh"]:
        if column in raw.columns:
            raw[column] = normalize_strings(raw[column])

    if "Xếp giải" in raw.columns:
        raw["Xếp giải"] = raw["Xếp giải"].str.replace(r"^Giải\s+", "", regex=True)

    if "Môn thi" in raw.columns and "Điểm" in raw.columns:
        raw["Percentile"] = raw.groupby("Môn thi")["Điểm"].rank(pct=True, ascending=False)
        raw["Rank"] = raw.groupby("Môn thi")["Điểm"].rank(method="min", ascending=False)
        raw["Total_in_Subject"] = raw.groupby("Môn thi")["Điểm"].transform("count")
    else:
        raw["Percentile"] = 0.0
        raw["Rank"] = 0
        raw["Total_in_Subject"] = 0

    dataset = pd.DataFrame(
        {
            "sbd": raw.get("SBD", "").astype(str),
            "ho_ten": raw.get("Họ và tên", "").astype(str),
            "ngay_sinh": raw.get("Ngày sinh", "").astype(str),
            "truong": raw.get("Trường", "").astype(str),
            "mon_thi": raw.get("Môn thi", "").astype(str),
            "diem": pd.to_numeric(raw.get("Điểm", 0.0), errors="coerce").fillna(0.0),
            "xep_giai": raw.get("Xếp giải", "").astype(str),
            "gioi_tinh": raw.get("Giới tính", "").astype(str),
            "percentile": pd.to_numeric(raw.get("Percentile", 0.0), errors="coerce").fillna(0.0),
            "rank": pd.to_numeric(raw.get("Rank", 0), errors="coerce").fillna(0).astype(int),
            "total_in_subject": pd.to_numeric(raw.get("Total_in_Subject", 0), errors="coerce").fillna(0).astype(int),
        }
    )

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()

    engine = create_engine(f"sqlite:///{SQLITE_PATH}")

    with engine.begin() as connection:
        dataset.to_sql("students", con=connection, index=False, if_exists="replace")
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_sbd ON students (sbd)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_ho_ten ON students (ho_ten)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_truong ON students (truong)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_mon_thi ON students (mon_thi)"))

    print(f"Migration completed. Rows: {len(dataset)}")
    print(f"SQLite DB: {SQLITE_PATH}")


if __name__ == "__main__":
    migrate()
