import os
import unicodedata
from pathlib import Path
from typing import Dict

import pandas as pd
import requests
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine, text

EXCEL_PATH = Path(__file__).resolve().parents[1] / "data" / "Tong_hop.xlsx"
DEFAULT_CLEAR_CACHE_TIMEOUT = 20


def get_env_or_fail(name: str) -> str:
    """Read required environment variable, fail fast if absent."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def normalize_sync_database_url(url: str) -> str:
    """Convert async/short Postgres URLs to psycopg2 sync URL for local uploader."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def normalize_header(value: str) -> str:
    base = unicodedata.normalize("NFKD", str(value).strip().lower())
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    return " ".join(base.split())


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map Vietnamese/variant Excel headers to canonical database column names."""
    aliases: Dict[str, str] = {
        "sbd": "sbd",
        "so bao danh": "sbd",
        "ho_ten": "ho_ten",
        "ho ten": "ho_ten",
        "ho va ten": "ho_ten",
        "ngay_sinh": "ngay_sinh",
        "ngay sinh": "ngay_sinh",
        "truong": "truong",
        "mon_thi": "mon_thi",
        "mon thi": "mon_thi",
        "mon": "mon_thi",
        "diem": "diem",
        "xep_giai": "xep_giai",
        "xep giai": "xep_giai",
        "xep hang giai": "xep_giai",
        "gioi_tinh": "gioi_tinh",
        "gioi tinh": "gioi_tinh",
    }

    renamed = {}
    for column in df.columns:
        key = normalize_header(column)
        renamed[column] = aliases.get(key, key.replace(" ", "_"))
    df = df.rename(columns=renamed)

    required = ["sbd", "ho_ten", "ngay_sinh", "truong", "mon_thi", "diem", "xep_giai", "gioi_tinh"]
    for column in required:
        if column not in df.columns:
            df[column] = None

    return df[required].copy()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean text, normalize scores, and precompute rank/percentile metrics."""
    text_cols = ["sbd", "ho_ten", "ngay_sinh", "truong", "mon_thi", "xep_giai", "gioi_tinh"]
    for col in text_cols:
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )
        df.loc[df[col].str.lower().isin({"nan", "none", "null"}), col] = ""

    df["diem"] = pd.to_numeric(df["diem"], errors="coerce").fillna(0.0).clip(lower=0.0)

    subject_group = df["mon_thi"].replace("", "Khong_ro")
    df["rank"] = (
        df.groupby(subject_group, dropna=False)["diem"]
        .rank(method="dense", ascending=False)
        .fillna(0)
        .astype(int)
    )
    df["percentile"] = (
        df.groupby(subject_group, dropna=False)["diem"]
        .rank(method="min", pct=True, ascending=False)
        .fillna(0.0)
        .mul(100)
        .round(2)
    )
    df["total_in_subject"] = df.groupby(subject_group, dropna=False)["diem"].transform("size").astype(int)

    return df


def define_students_table(metadata: MetaData) -> Table:
    """Define students table schema for bulk insert workflow."""
    return Table(
        "students",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("sbd", String(50), index=True, nullable=False),
        Column("ho_ten", String(255), index=True, nullable=False),
        Column("ngay_sinh", String(50), nullable=True),
        Column("truong", String(255), nullable=True),
        Column("mon_thi", String(120), nullable=True),
        Column("diem", Float, nullable=False, default=0.0),
        Column("xep_giai", String(80), nullable=True),
        Column("gioi_tinh", String(40), nullable=True),
        Column("percentile", Float, nullable=False, default=0.0),
        Column("rank", Integer, nullable=False, default=0),
        Column("total_in_subject", Integer, nullable=False, default=0),
    )


def bulk_upload(df: pd.DataFrame, database_url: str) -> int:
    """Truncate existing data and upload all rows in chunks."""
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    metadata = MetaData()
    students = define_students_table(metadata)

    print("Creating schema / ensuring table exists...")
    metadata.create_all(engine)

    records = df.to_dict(orient="records")
    total_rows = len(records)
    chunk_size = 2000

    with engine.begin() as conn:
        print("Clearing old data from students table...")
        conn.execute(text("TRUNCATE TABLE students RESTART IDENTITY"))
        print(f"Uploading {total_rows:,} rows to Postgres...")

        for start in range(0, total_rows, chunk_size):
            end = min(start + chunk_size, total_rows)
            conn.execute(students.insert(), records[start:end])
            print(f" - Uploaded {end:,}/{total_rows:,} rows")

    engine.dispose()
    return total_rows


def trigger_cache_clear(base_url: str, admin_api_key: str) -> None:
    """Call protected cache-clear endpoint after successful upload."""
    endpoint = f"{base_url.rstrip('/')}/api/admin/clear-cache"
    print("Clearing cache on production API...")
    response = requests.post(
        endpoint,
        headers={"X-Admin-Key": admin_api_key},
        timeout=DEFAULT_CLEAR_CACHE_TIMEOUT,
    )
    response.raise_for_status()
    print("Clearing Cache... Done!")


def main() -> None:
    print("=== HSG Insight Cloud Upload ===")
    database_url = normalize_sync_database_url(get_env_or_fail("DATABASE_URL"))
    render_api_url = get_env_or_fail("RENDER_API_URL")
    admin_api_key = get_env_or_fail("ADMIN_API_KEY")

    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}")

    print(f"Processing Excel: {EXCEL_PATH}")
    raw_df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    prepared_df = clean_dataframe(normalize_columns(raw_df))
    print(f"Rows prepared: {len(prepared_df):,}")

    inserted = bulk_upload(prepared_df, database_url)
    print(f"Upload complete: {inserted:,} rows inserted.")

    trigger_cache_clear(render_api_url, admin_api_key)
    print("All done.")


if __name__ == "__main__":
    main()
