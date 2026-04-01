import csv
import io
import json
import math
import os
import logging
import ssl
import socket
import random
from functools import wraps
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, urlparse

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import Float, Integer, String, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import QueuePool

PRIZE_LEVELS = ["Nhất", "Nhì", "Ba", "Khuyến khích"]
CACHE_TTL_SECONDS = 600
CACHE_PREFIX = "hsg_cache:"

DEFAULT_DB = "postgresql+asyncpg://postgres:postgres@localhost:5432/hsg"
DATABASE_URL_RAW = os.getenv("DATABASE_URL", DEFAULT_DB)
REDIS_URL = os.getenv("REDIS_URL")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
logging.basicConfig(level=logging.INFO)

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE


def normalize_async_database_url(url: str) -> str:
    """Force SQLAlchemy async URL format for Postgres + asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _resolve_ipv4(database_url: str) -> str:
    try:
        parsed = urlparse(database_url)
        hostname = parsed.hostname
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if not results:
            return database_url
        ipv4 = results[0][4][0]
        resolved = parsed._replace(netloc=f"{parsed.username}:{parsed.password}@{ipv4}:{parsed.port}")
        return resolved.geturl()
    except Exception:
        return database_url


def sanitize_db_url_and_connect_args(url: str) -> tuple[str, dict[str, Any]]:
    """
    Convert common Postgres SSL query args to asyncpg-compatible connect_args.
    Supabase/Render URLs often use sslmode=require.
    """
    parsed = urlsplit(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    keep_pairs: list[tuple[str, str]] = []
    connect_args: dict[str, Any] = {}

    for key, value in query_pairs:
        lowered = key.lower()
        if lowered == "sslmode" and value.lower() == "require":
            connect_args["ssl"] = "require"
            continue
        keep_pairs.append((key, value))

    cleaned_query = urlencode(keep_pairs)
    cleaned_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, cleaned_query, parsed.fragment))
    return cleaned_url, connect_args


DATABASE_URL = normalize_async_database_url(DATABASE_URL_RAW)
DATABASE_URL, _LEGACY_CONNECT_ARGS_UNUSED = sanitize_db_url_and_connect_args(DATABASE_URL)
_DATABASE_URL = _resolve_ipv4(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sbd: Mapped[str] = mapped_column(String(50), index=True)
    ho_ten: Mapped[str] = mapped_column(String(255), index=True)
    ngay_sinh: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    truong: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mon_thi: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    diem: Mapped[float] = mapped_column(Float, default=0.0)
    xep_giai: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    gioi_tinh: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    percentile: Mapped[float] = mapped_column(Float, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    total_in_subject: Mapped[int] = mapped_column(Integer, default=0)


# --- Cấu hình connect_args cho asyncpg + PgBouncer Transaction Mode ---
# statement_cache_size=0 là BẮT BUỘC. PgBouncer Transaction Mode không
# hỗ trợ named prepared statements của PostgreSQL. Nếu thiếu dòng này,
# sẽ xuất hiện lỗi "prepared statement does not exist" ngẫu nhiên.
#
# command_timeout=10: thời gian tối đa (giây) asyncpg chờ 1 query hoàn thành.
# timeout=10: thời gian tối đa (giây) asyncpg chờ thiết lập kết nối mới.
# Cả hai phải NHỎ HƠN pool_timeout (15s) để tránh collision timeout.
_POOL_RECYCLE_SECONDS = 180 + random.randint(-30, 30)

_ASYNCPG_CONNECT_ARGS = {
    "statement_cache_size": 0,
    "command_timeout": 10,
    "timeout": 12,
    "ssl": _ssl_context,
    "server_settings": {"application_name": "hsg_fastapi"},
}

# --- Lý do chọn từng tham số của QueuePool ---
#
# pool_size=2:
#   Số kết nối persistent tối đa mỗi instance Render duy trì.
#   3 instances × 2 = 6 kết nối steady-state. An toàn dưới giới hạn 15
#   của Supabase Free Tier, còn dư headroom cho max_overflow.
#
# max_overflow=1:
#   Cho phép tạo thêm tối đa 1 kết nối tạm thời khi pool đầy (burst).
#   3 instances × (2 + 1) = 9 kết nối tối đa tuyệt đối. Không bao giờ
#   chạm giới hạn 15 của Supabase.
#
# pool_recycle=180:
#   SQLAlchemy tự đóng và tạo lại kết nối sau 180 giây (3 phút).
#   PgBouncer Free Tier giết kết nối idle sau ~5 phút. Đặt recycle
#   ngắn hơn đảm bảo SQLAlchemy luôn chủ động drop trước, tránh race
#   condition khi PgBouncer đột ngột đóng kết nối phía dưới.
#
# pool_timeout=15:
#   Thời gian tối đa (giây) một request chờ lấy kết nối từ pool.
#   Phải LỚN HƠN command_timeout (10s) và timeout (10s) của asyncpg.
#   Nếu để nhỏ hơn, pool_timeout sẽ fire trước khi asyncpg có cơ hội
#   tự xử lý, gây ra lỗi giả (false timeout error).
#
# pool_pre_ping=True:
#   Gửi "SELECT 1" kiểm tra trước khi dùng kết nối từ pool. Không phải
#   silver bullet (vẫn có race condition), nhưng loại bỏ được phần lớn
#   stale connections. Giữ lại vì chi phí thấp.
#
# pool_use_lifo=True:
#   Pool dùng theo thứ tự LIFO (Last-In-First-Out). Kết nối vừa dùng
#   xong sẽ được tái sử dụng trước tiên. Điều này giữ số lượng kết nối
#   "warm" ở mức tối thiểu, cho phép các kết nối idle cũ hơn đạt đến
#   pool_recycle và bị drop sạch sẽ. Giảm đáng kể số lượng kết nối bị
#   PgBouncer kill ngầm bên dưới.
engine = create_async_engine(
    _DATABASE_URL,
    poolclass=QueuePool,
    pool_size=2,
    max_overflow=1,
    pool_recycle=_POOL_RECYCLE_SECONDS,
    pool_timeout=20,
    pool_pre_ping=True,
    pool_use_lifo=True,
    connect_args=_ASYNCPG_CONNECT_ARGS,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
SessionLocal = AsyncSessionLocal
redis_client: Optional[Redis] = None

app = FastAPI(title="HSG Insight", version="6.0")


@app.api_route("/", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "message": "Backend is running TH TH TH"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith("/api/") and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=1800, stale-while-revalidate=86400"
    return response


def is_all_value(value: Optional[str]) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in {"", "all", "tất cả"}


def fmt_score(value: float) -> str:
    if value is None or math.isnan(value):
        return "0"
    return f"{float(value):.1f}"


def build_cache_key(prefix: str, request: Request) -> str:
    if not request.query_params:
        return f"{CACHE_PREFIX}{prefix}:all"
    parts = [f"{k}_{v}" for k, v in sorted(request.query_params.items())]
    return f"{CACHE_PREFIX}{prefix}:{':'.join(parts)}"


async def get_cached_or_compute(request: Request, prefix: str, compute: Callable[[], Awaitable[Any]]) -> Any:
    global redis_client
    key = build_cache_key(prefix, request)

    if redis_client is not None:
        cached_value = await redis_client.get(key)
        if cached_value:
            return json.loads(cached_value)

    payload = await compute()

    if redis_client is not None:
        await redis_client.setex(key, CACHE_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))

    return payload


def cached(prefix: str):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if request is None:
                return await handler(*args, **kwargs)

            async def compute():
                return await handler(*args, **kwargs)

            return await get_cached_or_compute(request, prefix, compute)

        return wrapper

    return decorator


def apply_filters(query, mon_thi: Optional[str], truong: Optional[str], gioi_tinh: Optional[str], xep_giai: Optional[str]):
    if not is_all_value(mon_thi):
        query = query.where(func.lower(Student.mon_thi).like(f"%{str(mon_thi).lower()}%"))
    if not is_all_value(truong):
        query = query.where(func.lower(Student.truong).like(f"%{str(truong).lower()}%"))
    if not is_all_value(gioi_tinh):
        query = query.where(func.lower(Student.gioi_tinh).like(f"%{str(gioi_tinh).lower()}%"))
    if not is_all_value(xep_giai):
        query = query.where(func.lower(Student.xep_giai).like(f"%{str(xep_giai).lower()}%"))
    return query

#hoangthaihung
async def fetch_filtered_rows(
    session: AsyncSession,
    mon_thi: Optional[str],
    truong: Optional[str],
    gioi_tinh: Optional[str],
    xep_giai: Optional[str],
):
    query = apply_filters(select(Student), mon_thi, truong, gioi_tinh, xep_giai)
    result = await session.execute(query)
    return result.scalars().all()


def build_ticker_insights(rows: list[Student], mon_thi: Optional[str] = None) -> list[str]:
    if not rows:
        return ["Chưa có dữ liệu phù hợp."]

    total = len(rows)
    scores = [float(row.diem or 0.0) for row in rows]
    buckets: dict[str, list[str]] = {"score": [], "school": [], "subject": []}

    ranges = [(0, 10, "<10"), (10, 12, "10-12"), (12, 14, "12-14"), (14, 16, "14-16"), (16, 18, "16-18"), (18, 20.01, "18-20")]
    counts = {label: 0 for _, _, label in ranges}
    for score in scores:
        for low, high, label in ranges:
            if low <= score < high:
                counts[label] += 1
                break

    dominant_label = max(counts, key=counts.get)
    dominant_count = counts[dominant_label]
    if dominant_count > 0:
        buckets["score"].append(f"Nhóm {dominant_label} có {dominant_count} em.")

    high_count = sum(1 for score in scores if score >= 16)
    if high_count > 0:
        buckets["score"].append(f"Từ 16 điểm trở lên chiếm {round((high_count / total) * 100, 1)}%.")

    avg_score = sum(scores) / total
    if is_all_value(mon_thi):
        buckets["score"].append(f"Điểm TB hiện tại là {fmt_score(avg_score)}.")
    else:
        buckets["score"].append(f"Điểm TB môn {mon_thi} là {fmt_score(avg_score)}.")

    prize_rows = [row for row in rows if row.xep_giai in PRIZE_LEVELS]
    if prize_rows:
        school_counts: dict[str, int] = {}
        for row in prize_rows:
            school = row.truong or "Không có"
            school_counts[school] = school_counts.get(school, 0) + 1
        ranking = sorted(school_counts.items(), key=lambda item: item[1], reverse=True)
        top_school, top_count = ranking[0]
        if len(ranking) > 1:
            diff = top_count - ranking[1][1]
            if diff > 0:
                buckets["school"].append(f"{top_school} dẫn đầu với {top_count} giải (hơn vị trí thứ hai {diff} giải).")
            else:
                buckets["school"].append(f"{top_school} dẫn đầu với {top_count} giải.")
        else:
            buckets["school"].append(f"{top_school} dẫn đầu với {top_count} giải.")

    subject_scores: dict[str, list[float]] = {}
    for row in rows:
        subject = row.mon_thi or "Không có"
        subject_scores.setdefault(subject, []).append(float(row.diem or 0.0))
    if subject_scores:
        top_subject = max(subject_scores.items(), key=lambda item: sum(item[1]) / len(item[1]))
        buckets["subject"].append(f"Môn điểm TB cao nhất là {top_subject[0]}: {fmt_score(sum(top_subject[1]) / len(top_subject[1]))}.")

    ordered: list[str] = []
    for idx in range(max(len(v) for v in buckets.values())):
        for key in ["score", "school", "subject"]:
            if idx < len(buckets[key]):
                ordered.append(buckets[key][idx])

    return ordered[:9] if ordered else ["Chưa có dữ liệu phù hợp."]


async def clear_cache_namespace() -> int:
    """Delete only app cache keys, avoids wiping unrelated Redis data."""
    global redis_client
    if redis_client is None:
        return 0

    deleted = 0
    async for key in redis_client.scan_iter(match=f"{CACHE_PREFIX}*"):
        deleted += await redis_client.delete(key)
    return deleted


@app.on_event("startup")
async def startup_event():
    global redis_client
    logging.info("🚀 Web server is starting... Database will connect lazily.")

    if REDIS_URL:
        try:
            redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
            logging.info("⚡ Redis client initialized.")
        except Exception as exc:
            logging.warning(f"⚠️ Redis unavailable: {exc}")
            redis_client = None


@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    if redis_client is not None:
        await redis_client.close()


@app.get("/api/filters")
@cached("filters")
async def get_filters(request: Request):
    async with SessionLocal() as session:
        async def get_unique(column):
            query = select(column).where(column.is_not(None)).distinct().order_by(column.asc())
            result = await session.execute(query)
            values = [str(v).strip() for v in result.scalars().all() if v and str(v).strip()]
            return [v for v in values if v.lower() not in {"nan", "none", "không có"}]

        return {
            "mon_thi": await get_unique(Student.mon_thi),
            "truong": await get_unique(Student.truong),
            "gioi_tinh": await get_unique(Student.gioi_tinh),
            "xep_giai": await get_unique(Student.xep_giai),
        }


@app.get("/api/stats")
@cached("stats")
async def get_stats(
    request: Request,
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    async with SessionLocal() as session:
        base = apply_filters(select(Student), mon_thi, truong, gioi_tinh, xep_giai)

        total = int((await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one())

        if total == 0:
            return {
                "total": 0,
                "avg_score": 0.0,
                "total_prizes": 0,
                "pass_rate": 0.0,
                "prize_breakdown": {level: 0 for level in PRIZE_LEVELS},
            }

        avg_score = float((await session.execute(select(func.coalesce(func.avg(base.subquery().c.diem), 0.0)))).scalar_one())

        prize_case = case((Student.xep_giai.in_(PRIZE_LEVELS), 1), else_=0)
        prize_total_query = apply_filters(select(func.sum(prize_case)), mon_thi, truong, gioi_tinh, xep_giai)
        total_prizes = int((await session.execute(prize_total_query)).scalar() or 0)

        prize_breakdown = {level: 0 for level in PRIZE_LEVELS}
        breakdown_query = (
            select(Student.xep_giai, func.count())
            .where(Student.xep_giai.in_(PRIZE_LEVELS))
            .group_by(Student.xep_giai)
        )
        breakdown_query = apply_filters(breakdown_query, mon_thi, truong, gioi_tinh, xep_giai)
        for level, count in (await session.execute(breakdown_query)).all():
            prize_breakdown[str(level)] = int(count)

        pass_rate = round((total_prizes / total) * 100, 1)

        return {
            "total": total,
            "avg_score": round(avg_score, 2),
            "total_prizes": total_prizes,
            "pass_rate": pass_rate,
            "prize_breakdown": prize_breakdown,
        }


@app.get("/api/subject-average")
@cached("subject_average")
async def get_subject_average(
    request: Request,
    mon_thi: str = Query(...),
):
    if is_all_value(mon_thi):
        return {"mon_thi": mon_thi, "average": 0.0}

    async with SessionLocal() as session:
        query = select(func.coalesce(func.avg(Student.diem), 0.0)).where(
            func.lower(Student.mon_thi).like(f"%{str(mon_thi).lower()}%")
        )
        average = float((await session.execute(query)).scalar_one() or 0.0)
        return {"mon_thi": mon_thi, "average": round(average, 2)}


@app.get("/api/score-distribution")
@cached("score_distribution")
async def get_score_distribution(
    request: Request,
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    async with SessionLocal() as session:
        query = apply_filters(select(Student.diem), mon_thi, truong, gioi_tinh, xep_giai)
        scores = [float(v or 0.0) for v in (await session.execute(query)).scalars().all()]

        if not scores:
            return {"bins": []}

        edges = [0, 10, 12, 14, 16, 18, 20.01]
        labels = ["<10", "10-12", "12-14", "14-16", "16-18", "18-20"]
        counts = {label: 0 for label in labels}

        for score in scores:
            for idx in range(len(labels)):
                if edges[idx] <= score < edges[idx + 1]:
                    counts[labels[idx]] += 1
                    break

        return {"bins": [{"range": label, "count": counts[label]} for label in labels]}


@app.get("/api/top-schools")
@cached("top_schools")
async def get_top_schools(
    request: Request,
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    metric: str = Query("prizes"),
    limit: int = Query(10),
):
    async with SessionLocal() as session:
        if metric == "avg_score":
            query = (
                select(Student.truong, func.avg(Student.diem).label("value"))
                .group_by(Student.truong)
                .order_by(func.avg(Student.diem).desc())
                .limit(limit)
            )
            query = apply_filters(query, mon_thi, truong, gioi_tinh, xep_giai)
            rows = (await session.execute(query)).all()
            return {
                "schools": [
                    {"school": str(name), "value": round(float(value or 0.0), 2)}
                    for name, value in rows
                    if name
                ]
            }

        query = (
            select(Student.truong, func.count().label("value"))
            .where(Student.xep_giai.in_(PRIZE_LEVELS))
            .group_by(Student.truong)
            .order_by(func.count().desc())
            .limit(limit)
        )
        query = apply_filters(query, mon_thi, truong, gioi_tinh, xep_giai)
        rows = (await session.execute(query)).all()
        return {"schools": [{"school": str(name), "value": int(value)} for name, value in rows if name]}


@app.get("/api/students")
@cached("students")
async def get_students(
    request: Request,
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    search: Optional[str] = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    async with SessionLocal() as session:
        query = apply_filters(select(Student), mon_thi, truong, gioi_tinh, xep_giai)

        if search and search.strip():
            value = search.strip().lower()
            query = query.where(
                or_(
                    func.lower(Student.sbd).like(f"%{value}%"),
                    func.lower(Student.ho_ten).like(f"%{value}%"),
                )
            )

        total = int((await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one())

        if total == 0:
            return {
                "students": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
                "current_page": 1,
            }

        total_pages = math.ceil(total / page_size)
        offset = (page - 1) * page_size
        students = (await session.execute(query.order_by(Student.diem.desc()).offset(offset).limit(page_size))).scalars().all()

        records = [
            {
                "sbd": row.sbd or "Không có",
                "ho_ten": row.ho_ten or "Không có",
                "truong": row.truong or "Không có",
                "mon_thi": row.mon_thi or "Không có",
                "diem": float(row.diem or 0.0),
                "xep_giai": row.xep_giai or "Không có",
                "percentile": float(row.percentile or 0.0),
                "rank": int(row.rank or 0),
                "total_in_subject": int(row.total_in_subject or 0),
            }
            for row in students
        ]

        return {
            "students": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "current_page": page,
        }


@app.get("/api/ticker-insights")
@cached("ticker_insights")
async def get_ticker_insights(
    request: Request,
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    async with SessionLocal() as session:
        rows = await fetch_filtered_rows(session, mon_thi, truong, gioi_tinh, xep_giai)
        return {"insights": build_ticker_insights(rows, mon_thi=mon_thi)}


@app.get("/api/export")
async def export_csv(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    search: Optional[str] = Query(""),
):
    async with SessionLocal() as session:
        query = apply_filters(select(Student), mon_thi, truong, gioi_tinh, xep_giai)
        if search and search.strip():
            value = search.strip().lower()
            query = query.where(
                or_(
                    func.lower(Student.sbd).like(f"%{value}%"),
                    func.lower(Student.ho_ten).like(f"%{value}%"),
                )
            )

        rows = (await session.execute(query.order_by(Student.diem.desc()))).scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["SBD", "Họ và tên", "Ngày sinh", "Trường", "Môn thi", "Điểm", "Xếp giải"])
        for row in rows:
            writer.writerow([
                row.sbd or "",
                row.ho_ten or "",
                row.ngay_sinh or "",
                row.truong or "",
                row.mon_thi or "",
                float(row.diem or 0.0),
                row.xep_giai or "",
            ])

        payload = output.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            iter([payload]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=HSG_Insight_Export.csv"},
        )


@app.post("/api/admin/clear-cache")
async def clear_cache(
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
):
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY is not configured")
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    deleted = await clear_cache_namespace()
    return {"status": "ok", "deleted_keys": deleted}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
