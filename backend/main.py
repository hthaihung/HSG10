import csv
import io
import json
import math
import os
import logging
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import Float, Integer, String, case, func, or_, select
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

PRIZE_LEVELS = ["Nhất", "Nhì", "Ba", "Khuyến khích"]
CACHE_TTL_SECONDS = 600
CACHE_PREFIX = "hsg_cache:"
LOCAL_STATS_TTL_SECONDS = 60
LOCAL_LIST_TTL_SECONDS = 20
LOCAL_CHART_TTL_SECONDS = 20
LOCAL_TOP_SCHOOLS_TTL_SECONDS = 20

_LOCAL_CACHE: dict[str, tuple[float, Any]] = {}

_RAW_DB_URL = os.environ["DATABASE_URL"]

# Đổi prefix từ driver cũ sang psycopg.
# Xử lý cả trường hợp URL chưa có prefix dialect (plain postgresql://)
# lẫn trường hợp đã có prefix driver cũ.
_DATABASE_URL = (
    _RAW_DB_URL
    .replace("postgresql+" + "asyn" + "cpg://", "postgresql+psycopg_async://")
    .replace("postgresql+psycopg://", "postgresql+psycopg_async://")
    .replace("postgresql://", "postgresql+psycopg_async://")
)
REDIS_URL = os.getenv("REDIS_URL")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
logging.basicConfig(level=logging.INFO)


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


engine = create_async_engine(
    _DATABASE_URL,
    pool_size=2,
    max_overflow=0,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
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


def _build_local_key(
    mon_thi: Optional[str],
    truong: Optional[str],
    gioi_tinh: Optional[str],
    xep_giai: Optional[str],
    search: str = "",
) -> str:
    return f"{mon_thi}:{truong}:{gioi_tinh}:{xep_giai}:{search}"


def _get_local_cache(cache_key: str) -> Any:
    payload = _LOCAL_CACHE.get(cache_key)
    if not payload:
        return None
    expires_at, value = payload
    if expires_at <= time.time():
        _LOCAL_CACHE.pop(cache_key, None)
        return None
    return value


def _set_local_cache(cache_key: str, value: Any, ttl_seconds: int) -> None:
    _LOCAL_CACHE[cache_key] = (time.time() + ttl_seconds, value)


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


async def fetch_score_bins(
    session: AsyncSession,
    mon_thi: Optional[str],
    truong: Optional[str],
    gioi_tinh: Optional[str],
    xep_giai: Optional[str],
) -> list[dict[str, int]]:
    labels = ["<10", "10-12", "12-14", "14-16", "16-18", "18-20"]
    counts = {label: 0 for label in labels}

    bucket = case(
        (Student.diem < 10, "<10"),
        (Student.diem < 12, "10-12"),
        (Student.diem < 14, "12-14"),
        (Student.diem < 16, "14-16"),
        (Student.diem < 18, "16-18"),
        else_="18-20",
    ).label("bucket")

    bucket_query = apply_filters(
        select(bucket, func.count(Student.id)).group_by(bucket),
        mon_thi,
        truong,
        gioi_tinh,
        xep_giai,
    )
    for label, count in (await session.execute(bucket_query)).all():
        if label in counts:
            counts[str(label)] = int(count)

    return [{"range": label, "count": counts[label]} for label in labels]


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
    stats_cache_key = f"stats:{_build_local_key(mon_thi, truong, gioi_tinh, xep_giai)}"
    cached_stats = _get_local_cache(stats_cache_key)
    if cached_stats is not None:
        return cached_stats

    async with SessionLocal() as session:
        aggregate_query = apply_filters(
            select(
                func.count(Student.id),
                func.coalesce(func.avg(Student.diem), 0.0),
                func.coalesce(func.sum(case((Student.xep_giai.in_(PRIZE_LEVELS), 1), else_=0)), 0),
            ),
            mon_thi,
            truong,
            gioi_tinh,
            xep_giai,
        )
        total, avg_score, total_prizes = (await session.execute(aggregate_query)).one()
        total = int(total or 0)
        avg_score = float(avg_score or 0.0)
        total_prizes = int(total_prizes or 0)

        if total == 0:
            payload = {
                "total": 0,
                "avg_score": 0.0,
                "total_prizes": 0,
                "pass_rate": 0.0,
                "prize_breakdown": {level: 0 for level in PRIZE_LEVELS},
            }
            _set_local_cache(stats_cache_key, payload, LOCAL_STATS_TTL_SECONDS)
            return payload

        prize_breakdown = {level: 0 for level in PRIZE_LEVELS}
        breakdown_query = (
            select(Student.xep_giai, func.count())
            .where(Student.xep_giai.in_(PRIZE_LEVELS))
            .group_by(Student.xep_giai)
        )
        breakdown_query = apply_filters(breakdown_query, mon_thi, truong, gioi_tinh, xep_giai)
        for level, count in (await session.execute(breakdown_query)).all():
            prize_breakdown[str(level)] = int(count)

        raw_rate = (total_prizes / total) * 100 if total else 0.0
        pass_rate = round(min(100.0, raw_rate), 1)

        payload = {
            "total": total,
            "avg_score": round(avg_score, 2),
            "total_prizes": total_prizes,
            "pass_rate": pass_rate,
            "prize_breakdown": prize_breakdown,
        }
        _set_local_cache(stats_cache_key, payload, LOCAL_STATS_TTL_SECONDS)
        return payload


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
        bins = await fetch_score_bins(session, mon_thi, truong, gioi_tinh, xep_giai)
        return {"bins": bins}


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
    students_cache_key = f"students:{_build_local_key(mon_thi, truong, gioi_tinh, xep_giai, search or '')}:{page}:{page_size}"
    cached_students = _get_local_cache(students_cache_key)
    if cached_students is not None:
        return cached_students

    async with SessionLocal() as session:
        query = apply_filters(select(Student), mon_thi, truong, gioi_tinh, xep_giai)
        count_query = apply_filters(select(func.count()), mon_thi, truong, gioi_tinh, xep_giai)

        if search and search.strip():
            value = search.strip().lower()
            search_clause = or_(
                func.lower(Student.sbd).like(f"%{value}%"),
                func.lower(Student.ho_ten).like(f"%{value}%"),
            )
            query = query.where(search_clause)
            count_query = count_query.where(search_clause)

        total = int((await session.execute(count_query)).scalar_one())

        if total == 0:
            payload = {
                "students": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
                "current_page": 1,
            }
            _set_local_cache(students_cache_key, payload, LOCAL_LIST_TTL_SECONDS)
            return payload

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

        payload = {
            "students": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "current_page": page,
        }
        _set_local_cache(students_cache_key, payload, LOCAL_LIST_TTL_SECONDS)
        return payload


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


@app.get("/dashboard")
@app.get("/api/dashboard")
async def get_dashboard(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    search: Optional[str] = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    metric: str = Query("prizes"),
    limit: int = Query(10, ge=1, le=50),
):
    base_key = _build_local_key(mon_thi, truong, gioi_tinh, xep_giai, search or "")
    stats_cache_key = f"dashboard:stats:{base_key}"
    students_cache_key = f"dashboard:students:{base_key}:{page}:{page_size}"
    chart_cache_key = f"dashboard:chart:{base_key}"
    top_cache_key = f"dashboard:top:{base_key}:{metric}:{limit}"

    async with SessionLocal() as session:
        stats_payload = _get_local_cache(stats_cache_key)
        if stats_payload is None:
            aggregate_query = apply_filters(
                select(
                    func.count(Student.id),
                    func.coalesce(func.avg(Student.diem), 0.0),
                    func.coalesce(func.sum(case((Student.xep_giai.in_(PRIZE_LEVELS), 1), else_=0)), 0),
                ),
                mon_thi,
                truong,
                gioi_tinh,
                xep_giai,
            )
            total, avg_score, total_prizes = (await session.execute(aggregate_query)).one()
            total = int(total or 0)
            avg_score = float(avg_score or 0.0)
            total_prizes = int(total_prizes or 0)

            prize_breakdown = {level: 0 for level in PRIZE_LEVELS}
            if total > 0:
                breakdown_query = (
                    select(Student.xep_giai, func.count())
                    .where(Student.xep_giai.in_(PRIZE_LEVELS))
                    .group_by(Student.xep_giai)
                )
                breakdown_query = apply_filters(breakdown_query, mon_thi, truong, gioi_tinh, xep_giai)
                for level, count in (await session.execute(breakdown_query)).all():
                    prize_breakdown[str(level)] = int(count)

            raw_rate = (total_prizes / total) * 100 if total else 0.0
            stats_payload = {
                "total": total,
                "avg_score": round(avg_score, 2),
                "total_prizes": total_prizes,
                "pass_rate": round(min(100.0, raw_rate), 1),
                "prize_breakdown": prize_breakdown,
            }
            _set_local_cache(stats_cache_key, stats_payload, LOCAL_STATS_TTL_SECONDS)

        students_payload = _get_local_cache(students_cache_key)
        if students_payload is None:
            students_query = apply_filters(select(Student), mon_thi, truong, gioi_tinh, xep_giai)
            if search and search.strip():
                value = search.strip().lower()
                students_query = students_query.where(
                    or_(
                        func.lower(Student.sbd).like(f"%{value}%"),
                        func.lower(Student.ho_ten).like(f"%{value}%"),
                    )
                )

            offset = (page - 1) * page_size
            student_rows = (
                await session.execute(
                    students_query.order_by(Student.diem.desc()).offset(offset).limit(page_size)
                )
            ).scalars().all()
            students_payload = [
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
                for row in student_rows
            ]
            _set_local_cache(students_cache_key, students_payload, LOCAL_LIST_TTL_SECONDS)

        chart_payload = _get_local_cache(chart_cache_key)
        if chart_payload is None:
            chart_payload = {"bins": await fetch_score_bins(session, mon_thi, truong, gioi_tinh, xep_giai)}
            _set_local_cache(chart_cache_key, chart_payload, LOCAL_CHART_TTL_SECONDS)

        top_schools_payload = _get_local_cache(top_cache_key)
        if top_schools_payload is None:
            if metric == "avg_score":
                top_query = (
                    select(Student.truong, func.avg(Student.diem).label("value"))
                    .group_by(Student.truong)
                    .order_by(func.avg(Student.diem).desc())
                    .limit(limit)
                )
                top_query = apply_filters(top_query, mon_thi, truong, gioi_tinh, xep_giai)
                rows = (await session.execute(top_query)).all()
                schools = [
                    {"school": str(name), "value": round(float(value or 0.0), 2)}
                    for name, value in rows
                    if name
                ]
            else:
                top_query = (
                    select(Student.truong, func.count().label("value"))
                    .where(Student.xep_giai.in_(PRIZE_LEVELS))
                    .group_by(Student.truong)
                    .order_by(func.count().desc())
                    .limit(limit)
                )
                top_query = apply_filters(top_query, mon_thi, truong, gioi_tinh, xep_giai)
                rows = (await session.execute(top_query)).all()
                schools = [{"school": str(name), "value": int(value)} for name, value in rows if name]

            top_schools_payload = schools
            _set_local_cache(top_cache_key, top_schools_payload, LOCAL_TOP_SCHOOLS_TTL_SECONDS)

    return {
        "stats": stats_payload,
        "students": students_payload,
        "chart": chart_payload,
        "top_schools": top_schools_payload,
    }


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
