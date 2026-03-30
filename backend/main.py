"""
HSG Insight v4.0 — Data Pipeline & Header Fix
FastAPI + Pandas in-memory pipeline.
"""

import os
import io
import math
import traceback
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI(title="HSG Insight", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Hoặc sau này đổi thành tên miền chính thức của bạn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "Tong_hop.xlsx")
df: pd.DataFrame = pd.DataFrame()

@app.on_event("startup")
def load_data():
    global df
    try:
        if not os.path.exists(DATA_PATH):
            print(f"\033[91m[ERROR] File không tồn tại: {DATA_PATH}\033[0m")
            df = pd.DataFrame()
            return

        # 1. Correct Header Extraction: header=1 skips the title row
        raw = pd.read_excel(DATA_PATH, engine="openpyxl", header=1)

        # 2. Extreme Data Sanitization (Post-load):
        # Clean Columns
        raw.columns = raw.columns.astype(str).str.strip()

        # Drop Ghost Data (Empty SBD or Name)
        drop_cols = [c for c in ['SBD', 'Họ và tên'] if c in raw.columns]
        if drop_cols:
            raw.dropna(subset=drop_cols, inplace=True)
            # Dọn luôn các dòng mà có khoảng trắng ngầm thành NaN rỗng
            for col in drop_cols:
                raw = raw[raw[col].astype(str).str.strip() != ""]

        # Clean Score (Điểm)
        if "Điểm" in raw.columns:
            raw["Điểm"] = raw["Điểm"].astype(str).str.replace(",", ".", regex=False).str.strip()
            raw["Điểm"] = pd.to_numeric(raw["Điểm"], errors="coerce").fillna(0.0)
        else:
            raw["Điểm"] = 0.0

        # Clean String Columns
        string_cols = ["Môn thi", "Trường", "Xếp giải", "Giới tính", "Họ và tên", "SBD"]
        for col in string_cols:
            if col in raw.columns:
                raw[col] = raw[col].astype(str).str.strip()
                # Replace various nulls with 'Không có'
                mask = raw[col].isin(["nan", "NaN", "None", "", "Không", "Không đạt"])
                raw.loc[mask, col] = "Không có"

        # Explicitly remove "Giải " prefix if it exists in Xếp giải
        if "Xếp giải" in raw.columns:
            raw["Xếp giải"] = raw["Xếp giải"].str.replace(r"^Giải\s+", "", regex=True).str.strip()

        # Deep Dive Analytics: Calculate Percentile ranking per Subject
        if "Môn thi" in raw.columns and "Điểm" in raw.columns:
            # Rank pct=True: returns 0.0 to 1.0 ranking. ascending=False means highest score gets rank closest to 0 (top percentage).
            raw["Percentile"] = raw.groupby("Môn thi")["Điểm"].rank(pct=True, ascending=False)
            raw["Rank"] = raw.groupby("Môn thi")["Điểm"].rank(method="min", ascending=False)
            raw["Total_in_Subject"] = raw.groupby("Môn thi")["Điểm"].transform("count")
        else:
            raw["Percentile"] = 0.0
            raw["Rank"] = 0
            raw["Total_in_Subject"] = 0

        df = raw

        # 3. Startup Debug Logs (Mandatory):
        print("\n=== HSG INSIGHT STARTUP DIAGNOSTICS ===")
        print("DETECTED COLUMNS:", df.columns.tolist())
        if "Môn thi" in df.columns:
            print("SAMPLE SUBJECTS:", df["Môn thi"].unique()[:5])
        print("TOTAL ROWS LOADED:", len(df))
        print("=======================================\n")

    except Exception:
        print(f"\033[91m[CRASH] load_data:\n{traceback.format_exc()}\033[0m")
        df = pd.DataFrame()


def apply_filters(
    data: pd.DataFrame,
    mon_thi: Optional[str] = None,
    truong: Optional[str] = None,
    gioi_tinh: Optional[str] = None,
    xep_giai: Optional[str] = None,
) -> pd.DataFrame:
    if data.empty:
        return data.copy()
        
    filtered = data.copy()

    # 4. Safe Filtering Logic (.str.contains)
    def safe_filter(frame: pd.DataFrame, col: str, val: Optional[str]) -> pd.DataFrame:
        if not val or str(val).lower() in ("all", "tất cả", ""):
            return frame
        if col not in frame.columns:
            return frame
        # Drop naive exact match, use substring match safe for NaN
        return frame[frame[col].astype(str).str.contains(str(val).strip(), case=False, na=False, regex=False)]

    filtered = safe_filter(filtered, "Môn thi", mon_thi)
    filtered = safe_filter(filtered, "Trường", truong)
    filtered = safe_filter(filtered, "Giới tính", gioi_tinh)
    filtered = safe_filter(filtered, "Xếp giải", xep_giai)
    
    return filtered


PRIZE_LEVELS = ["Nhất", "Nhì", "Ba", "Khuyến khích"]


def is_all_value(value: Optional[str]) -> bool:
    return not value or str(value).lower() in ("all", "tất cả", "")


def get_prize_mask(frame: pd.DataFrame) -> pd.Series:
    if "Xếp giải" not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame["Xếp giải"].isin(PRIZE_LEVELS)


def fmt_score(value: float) -> str:
    if pd.isna(value):
        return "0"
    return f"{float(value):.1f}"


def build_ticker_insights(
    filt: pd.DataFrame,
    mon_thi: Optional[str] = None,
) -> list[str]:
    if filt.empty:
        return ["Chưa có dữ liệu phù hợp."]

    total = len(filt)
    buckets = {
        "score": [],
        "school": [],
        "gender": [],
        "subject": [],
        "fun": [],
    }

    if "Điểm" in filt.columns:
        edges = [0, 10, 12, 14, 16, 18, 20.01]
        labels = ["<10", "10-12", "12-14", "14-16", "16-18", "18-20"]
        scored = filt.copy()
        scored["_bin"] = pd.cut(scored["Điểm"], bins=edges, labels=labels, right=False)
        bin_counts = scored["_bin"].value_counts().reindex(labels, fill_value=0)
        dominant_bin = bin_counts.idxmax()
        dominant_count = int(bin_counts.max())
        if dominant_count > 0:
            buckets["score"].append(f"🎯 Nhóm {dominant_bin} có {dominant_count} em.")

        high_count = int((scored["Điểm"] >= 16).sum())
        if high_count > 0:
            high_pct = round((high_count / total) * 100, 1)
            buckets["score"].append(f"🎯 Từ 16 điểm trở lên chiếm {high_pct}%.")

        avg_score = scored["Điểm"].mean()
        if not math.isnan(avg_score):
            if is_all_value(mon_thi):
                buckets["score"].append(f"🎯 Điểm TB hiện tại là {fmt_score(avg_score)}.")
            else:
                buckets["score"].append(f"🎯 Điểm TB môn {mon_thi} là {fmt_score(avg_score)}.")

    if "Trường" in filt.columns and filt["Trường"].nunique() > 0:
        prize_df = filt[get_prize_mask(filt)]
        if not prize_df.empty:
            school_prizes = prize_df.groupby("Trường").size().sort_values(ascending=False)
            top_school = school_prizes.index[0]
            top_count = int(school_prizes.iloc[0])
            diff = (
                top_count - int(school_prizes.iloc[1])
                if len(school_prizes) > 1
                else None
            )
            message = f"🌟 {top_school} dẫn đầu với {top_count} giải"
            if diff and diff > 0:
                message += f" (hơn vị trí thứ hai {diff} giải)"
            message += "."
            buckets["school"].append(message)

        if "Điểm" in filt.columns:
            school_avg = filt.groupby("Trường")["Điểm"].mean().sort_values(ascending=False).head(3)
            if not school_avg.empty:
                top_names = ", ".join([str(name) for name in school_avg.index.tolist()])
                buckets["school"].append(f"🌟 Top điểm TB: {top_names}.")

    if "Giới tính" in filt.columns:
        prize_df = filt[get_prize_mask(filt)]
        gender_total = filt["Giới tính"].value_counts()
        if not prize_df.empty:
            gender_pass = prize_df["Giới tính"].value_counts()
            if all(gender in gender_total and gender_total[gender] > 0 for gender in ["Nữ", "Nam"]):
                female_rate = round((gender_pass.get("Nữ", 0) / gender_total["Nữ"]) * 100, 1)
                male_rate = round((gender_pass.get("Nam", 0) / gender_total["Nam"]) * 100, 1)
                buckets["gender"].append(
                    f"💡 Nữ đạt giải {female_rate}%, nam {male_rate}%."
                )

        if "Điểm" in filt.columns:
            segment = filt[(filt["Điểm"] >= 14) & (filt["Điểm"] < 16)]
            if not segment.empty:
                segment_gender = segment["Giới tính"].value_counts()
                diff = int(segment_gender.get("Nữ", 0) - segment_gender.get("Nam", 0))
                if diff > 0:
                    buckets["gender"].append(f"💡 Nhóm 14-16 có nữ nhiều hơn {diff} em.")
                elif diff < 0:
                    buckets["gender"].append(f"💡 Nhóm 14-16 có nam nhiều hơn {abs(diff)} em.")

    if "Môn thi" in filt.columns and filt["Môn thi"].nunique() > 0:
        if "Điểm" in filt.columns:
            subject_avg = filt.groupby("Môn thi")["Điểm"].mean().sort_values(ascending=False)
            if not subject_avg.empty:
                top_subject = subject_avg.index[0]
                top_avg = subject_avg.iloc[0]
                buckets["subject"].append(
                    f"📚 Môn điểm TB cao nhất là {top_subject}: {fmt_score(top_avg)}."
                )

            subject_spread = filt.groupby("Môn thi")["Điểm"].agg(lambda series: series.max() - series.min())
            subject_spread = subject_spread.sort_values(ascending=False)
            if not subject_spread.empty:
                spread_subject = subject_spread.index[0]
                spread_value = subject_spread.iloc[0]
                buckets["subject"].append(
                    f"📚 {spread_subject} có biên độ {fmt_score(spread_value)} điểm."
                )

        prize_df = filt[get_prize_mask(filt)]
        if not prize_df.empty and "Môn thi" in prize_df.columns:
            subject_prizes = prize_df.groupby("Môn thi").size().sort_values(ascending=False)
            if not subject_prizes.empty:
                top_prize_subject = subject_prizes.index[0]
                top_prize_count = int(subject_prizes.iloc[0])
                buckets["subject"].append(
                    f"📚 Môn nhiều giải nhất là {top_prize_subject}: {top_prize_count} giải."
                )

    if "Điểm" in filt.columns:
        top_row = filt.sort_values("Điểm", ascending=False).iloc[0]
        top_id = str(top_row.get("SBD", "")).strip() if "SBD" in filt.columns else ""
        top_label = f"SBD {top_id}" if top_id else "Một thí sinh"
        buckets["fun"].append(f"🤔 {top_label} đạt cao nhất: {fmt_score(top_row['Điểm'])}.")

        rounded_scores = filt["Điểm"].round(1)
        if not rounded_scores.empty:
            mode_scores = rounded_scores.mode()
            if not mode_scores.empty:
                mode_score = float(mode_scores.iloc[0])
                mode_count = int((rounded_scores == mode_score).sum())
                buckets["fun"].append(
                    f"🤔 Có {mode_count} em cùng ở mức {fmt_score(mode_score)}."
                )

    ordered_categories = ["score", "school", "gender", "subject", "fun"]
    max_items = max((len(items) for items in buckets.values()), default=0)
    ordered: list[str] = []
    for index in range(max_items):
        for category in ordered_categories:
            if index < len(buckets[category]):
                ordered.append(buckets[category][index])

    return ordered[:9] or ["Chưa có dữ liệu phù hợp."]


@app.get("/api/filters")
def get_filters():
    try:
        def get_unique(col: str):
            if df.empty or col not in df.columns:
                return []
            vals = df[col].astype(str).str.strip().unique()
            return sorted([v for v in vals if v and v.lower() not in ("nan", "none", "", "không có")])

        return {
            "mon_thi": get_unique("Môn thi"),
            "truong": get_unique("Trường"),
            "gioi_tinh": get_unique("Giới tính"),
            "xep_giai": get_unique("Xếp giải"),
        }
    except Exception as e:
        print(f"LỖI CRASH API /api/filters:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/subject-average")
def get_subject_average(mon_thi: str = Query(...)):
    try:
        if df.empty or "Điểm" not in df.columns or "Môn thi" not in df.columns:
            return {"mon_thi": mon_thi, "average": 0.0}

        # Lọc chính xác học sinh thi môn này (không dùng các filter khác)
        mask = df["Môn thi"].astype(str).str.contains(str(mon_thi).strip(), case=False, na=False, regex=False)
        subset = df[mask]
        
        if subset.empty:
            return {"mon_thi": mon_thi, "average": 0.0}
            
        avg = float(subset["Điểm"].mean())
        if math.isnan(avg):
            avg = 0.0
            
        return {"mon_thi": mon_thi, "average": round(avg, 2)}
    except Exception as e:
        print(f"LỖI CRASH API /api/subject-average:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/insights")
def get_insights(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)
        if filt.empty:
            return {"insights": ["Chưa có đủ dữ liệu để phân tích thông minh."]}

        insights = []

        # Determine if we are focusing on a single school
        school_focused = truong and str(truong).lower() not in ("all", "tất cả")

        # Insight 1: Trùm Trường vs Thủ khoa Trường
        if school_focused:
            if "Điểm" in filt.columns and "Họ và tên" in filt.columns and "Môn thi" in filt.columns:
                max_idx = filt["Điểm"].idxmax()
                if pd.notna(max_idx):
                    best_student = filt.loc[max_idx]
                    insights.append(f"👑 Thủ khoa trường là {best_student.get('Họ và tên', '')} với {best_student.get('Điểm', 0)} điểm môn {best_student.get('Môn thi', '')}")
        else:
            if "Trường" in filt.columns and "Xếp giải" in filt.columns:
                prizes = filt[filt["Xếp giải"].isin(["Nhất", "Nhì", "Ba", "Khuyến khích"])]
                if not prizes.empty:
                    top_school = prizes.groupby("Trường").size().idxmax()
                    
                    nhat = prizes[prizes["Xếp giải"] == "Nhất"]
                    if not nhat.empty:
                        nhat_cnt = nhat.groupby("Trường").size().get(top_school, 0)
                        if nhat_cnt > 0:
                            insights.append(f"🔥 Trường {top_school} dẫn đầu với {nhat_cnt} giải Nhất")
                        else:
                            top_count = prizes.groupby("Trường").size().max()
                            insights.append(f"🔥 Trường {top_school} dẫn đầu với {top_count} giải thưởng các loại")
                    else:
                        top_count = prizes.groupby("Trường").size().max()
                        insights.append(f"🔥 Trường {top_school} dẫn đầu với {top_count} giải thưởng các loại")

        # Insight 2: Khúc phổ điểm tập trung nhất (Mode Segment)
        if "Điểm" in filt.columns:
            edges = [0, 10, 12, 14, 16, 18, 20.01]
            labels = ["Dưới 10", "10-12", "12-14", "14-16", "16-18", "18-20"]
            binned = pd.cut(filt["Điểm"], bins=edges, labels=labels, right=False)
            mode_segment = binned.mode()
            if not mode_segment.empty:
                subj_text = f" trong môn {mon_thi}" if mon_thi and str(mon_thi).lower() not in ("all", "tất cả") else ""
                school_text = f" tại trường này" if school_focused else ""
                insights.append(f"🎯 Nhóm điểm [{mode_segment[0]}] chiếm đa số{subj_text}{school_text}")

        # Insight 3: Điểm trung bình cao nhất hoặc môn "khoai" nhất
        if not mon_thi or str(mon_thi).lower() in ("all", "tất cả"):
            if "Môn thi" in filt.columns and "Điểm" in filt.columns:
                avg_grp = filt.groupby("Môn thi")["Điểm"].mean()
                if not avg_grp.empty:
                    if school_focused:
                        lowest_m = avg_grp.idxmin()
                        lowest_avg = avg_grp.min()
                        insights.append(f"⚡ Môn thi thử thách nhất của trường là {lowest_m} (TB: {round(lowest_avg, 2)} điểm)")
                    else:
                        top_m = avg_grp.idxmax()
                        top_avg = avg_grp.max()
                        insights.append(f"🌟 Điểm trung bình cao nhất toàn tỉnh thuộc về môn {top_m} ({round(top_avg, 2)} điểm)")
        else:
            if "Điểm" in filt.columns:
                avg_val = filt["Điểm"].mean()
                if not math.isnan(avg_val):
                    pfix = "Trường này" if school_focused else "Môn"
                    insights.append(f"🌟 {pfix} {mon_thi} có phổ điểm trung bình {round(avg_val, 2)}")
                    
        # Insight 4: Giới tính
        if "Giới tính" in filt.columns and "Xếp giải" in filt.columns:
            pass_df = filt[filt["Xếp giải"].isin(["Nhất", "Nhì", "Ba", "Khuyến khích"])]
            if not pass_df.empty:
                gender_pass = pass_df["Giới tính"].value_counts()
                gender_total = filt["Giới tính"].value_counts()
                if "Nữ" in gender_pass and "Nam" in gender_pass and "Nữ" in gender_total and "Nam" in gender_total:
                    rate_f = gender_pass["Nữ"] / gender_total["Nữ"]
                    rate_m = gender_pass["Nam"] / gender_total["Nam"]
                    if rate_f > rate_m:
                        diff = round((rate_f - rate_m) * 100, 1)
                        insights.append(f"👩 Tỷ lệ đạt giải của nữ cao hơn nam {diff}%")
                    elif rate_m > rate_f:
                        diff = round((rate_m - rate_f) * 100, 1)
                        insights.append(f"👨 Tỷ lệ đạt giải của nam cao hơn nữ {diff}%")

        if not insights:
            insights = ["Hệ thống đang thu thập thêm dữ liệu để đánh giá."]

        return {"insights": insights}
    except Exception as e:
        print(f"LỖI CRASH /api/insights:\n{traceback.format_exc()}")
        return {"insights": ["Hệ thống phân tích thông minh đang tạm nghỉ."]}


@app.get("/api/ticker-insights")
def get_ticker_insights(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)
        return {"insights": build_ticker_insights(filt, mon_thi=mon_thi)}
    except Exception as e:
        print(f"LỖI CRASH /api/ticker-insights:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/advanced/compare-schools")
def compare_schools(
    school1: str = Query(...),
    school2: str = Query(...),
):
    try:
        res = {"school1": {"name": school1}, "school2": {"name": school2}}
        
        def get_school_stats(school_name):
            s_df = df[df["Trường"].astype(str).str.contains(str(school_name).strip(), case=False, na=False, regex=False)]
            if s_df.empty:
                return {"total": 0, "avg": 0.0, "prizes_total": 0, "dist": {}, "top_students": []}
            
            avg = float(s_df["Điểm"].mean()) if "Điểm" in s_df.columns else 0.0
            if math.isnan(avg): avg = 0.0
            
            prizes = 0
            dist = {"Nhất": 0, "Nhì": 0, "Ba": 0, "Khuyến khích": 0}
            if "Xếp giải" in s_df.columns:
                p_df = s_df[s_df["Xếp giải"].isin(dist.keys())]
                prizes = len(p_df)
                counts = p_df["Xếp giải"].value_counts().to_dict()
                for k in dist.keys(): dist[k] = counts.get(k, 0)
                
            top_students = []
            if "Điểm" in s_df.columns:
                top_df = s_df.sort_values("Điểm", ascending=False).head(3)
                for _, r in top_df.iterrows():
                    top_students.append({
                        "name": str(r.get("Họ và tên", "Không có")),
                        "score": float(r.get("Điểm", 0.0)),
                        "subject": str(r.get("Môn thi", "Không có")),
                        "prize": str(r.get("Xếp giải", "Không có"))
                    })
                    
            return {"total": len(s_df), "avg": round(avg, 2), "prizes_total": prizes, "dist": dist, "top_students": top_students}
            
        res["school1"]["stats"] = get_school_stats(school1)
        res["school2"]["stats"] = get_school_stats(school2)
        
        return res
    except Exception as e:
        print(f"LỖI CRASH /api/advanced/compare-schools:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/stats")
def get_stats(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)
        total = len(filt)
        if total == 0:
            empty_breakdown = {level: 0 for level in PRIZE_LEVELS}
            return {
                "total": 0,
                "avg_score": 0.0,
                "total_prizes": 0,
                "pass_rate": 0.0,
                "prize_breakdown": empty_breakdown,
            }

        avg_score = float(filt["Điểm"].mean()) if "Điểm" in filt.columns else 0.0
        if math.isnan(avg_score):
            avg_score = 0.0

        prizes = 0
        prize_breakdown = {level: 0 for level in PRIZE_LEVELS}
        if "Xếp giải" in filt.columns:
            level_counts = filt["Xếp giải"].value_counts()
            for level in PRIZE_LEVELS:
                prize_breakdown[level] = int(level_counts.get(level, 0))
            prizes = sum(prize_breakdown.values())
        pass_rate = round((prizes / total) * 100, 1) if total > 0 else 0.0

        return {
            "total": total,
            "avg_score": round(avg_score, 2),
            "total_prizes": prizes,
            "pass_rate": pass_rate,
            "prize_breakdown": prize_breakdown,
        }
    except Exception as e:
        print(f"LỖI CRASH API /api/stats:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/score-distribution")
def get_score_distribution(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)
        if filt.empty or "Điểm" not in filt.columns:
            return {"bins": []}

        edges = [0, 10, 12, 14, 16, 18, 20.01]
        labels = ["<10", "10-12", "12-14", "14-16", "16-18", "18-20"]

        fc = filt.copy()
        fc["_bin"] = pd.cut(fc["Điểm"], bins=edges, labels=labels, right=False)
        counts = fc["_bin"].value_counts().reindex(labels, fill_value=0)

        return {"bins": [{"range": lbl, "count": int(counts[lbl])} for lbl in labels]}
    except Exception as e:
        print(f"LỖI CRASH API /api/score-distribution:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/top-schools")
def get_top_schools(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    metric: str = Query("prizes"),
    limit: int = Query(10),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)
        if filt.empty or "Trường" not in filt.columns:
            return {"schools": []}

        if metric == "avg_score" and "Điểm" in filt.columns:
            grp = filt.groupby("Trường")["Điểm"].mean()
            grp = grp.fillna(0.0).round(2).sort_values(ascending=False).head(limit)
            return {"schools": [{"school": str(n), "value": float(v)} for n, v in grp.items()]}
        else:
            prize_df = filt[filt["Xếp giải"].isin(["Nhất", "Nhì", "Ba", "Khuyến khích"])]
            if prize_df.empty:
                return {"schools": []}
            grp = prize_df.groupby("Trường").size().sort_values(ascending=False).head(limit)
            return {"schools": [{"school": str(n), "value": int(v)} for n, v in grp.items()]}
    except Exception as e:
        print(f"LỖI CRASH API /api/top-schools:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/students")
def get_students(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    search: Optional[str] = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)

        if search and str(search).strip():
            q = str(search).strip()
            mask = pd.Series(False, index=filt.index)
            if "SBD" in filt.columns:
                mask = mask | filt["SBD"].astype(str).str.contains(q, case=False, na=False, regex=False)
            if "Họ và tên" in filt.columns:
                mask = mask | filt["Họ và tên"].astype(str).str.contains(q, case=False, na=False, regex=False)
            filt = filt[mask]

        total = len(filt)
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 0

        if total == 0:
            return {
                "students": [], 
                "total": 0, 
                "page": 1, 
                "page_size": page_size, 
                "total_pages": 0,
                "current_page": 1
            }

        if "Điểm" in filt.columns:
            filt = filt.sort_values("Điểm", ascending=False)

        start = (page - 1) * page_size
        page_df = filt.iloc[start: start + page_size]

        records = []
        for _, row in page_df.iterrows():
            d = float(row.get("Điểm", 0)) if not pd.isna(row.get("Điểm", 0)) else 0.0
            if math.isnan(d): d = 0.0
            
            records.append({
                "sbd":      str(row.get("SBD", "Không có")).strip(),
                "ho_ten":   str(row.get("Họ và tên", "Không có")).strip(),
                "truong":   str(row.get("Trường", "Không có")).strip(),
                "mon_thi":  str(row.get("Môn thi", "Không có")).strip(),
                "diem":     d,
                "xep_giai": str(row.get("Xếp giải", "Không có")).strip(),
                "percentile": float(row.get("Percentile", 0.0)),
                "rank": int(row.get("Rank", 0)),
                "total_in_subject": int(row.get("Total_in_Subject", 0)),
            })

        return {
            "students": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "current_page": page
        }
    except Exception as e:
        print(f"LỖI CRASH API /api/students:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/export")
def export_csv(
    mon_thi: Optional[str] = Query(None),
    truong: Optional[str] = Query(None),
    gioi_tinh: Optional[str] = Query(None),
    xep_giai: Optional[str] = Query(None),
    search: Optional[str] = Query(""),
):
    try:
        filt = apply_filters(df, mon_thi, truong, gioi_tinh, xep_giai)

        if search and str(search).strip():
            q = str(search).strip()
            mask = pd.Series(False, index=filt.index)
            if "SBD" in filt.columns:
                mask = mask | filt["SBD"].astype(str).str.contains(q, case=False, na=False, regex=False)
            if "Họ và tên" in filt.columns:
                mask = mask | filt["Họ và tên"].astype(str).str.contains(q, case=False, na=False, regex=False)
            filt = filt[mask]

        if "Điểm" in filt.columns:
            filt = filt.sort_values("Điểm", ascending=False)

        export_cols = [c for c in ["SBD", "Họ và tên", "Ngày sinh", "Trường", "Môn thi", "Điểm", "Xếp giải"] if c in filt.columns]
        out = filt[export_cols].copy() if not filt.empty else pd.DataFrame(columns=export_cols)

        buf = io.StringIO()
        out.to_csv(buf, index=False)
        payload = buf.getvalue().encode("utf-8-sig")

        return StreamingResponse(
            iter([payload]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=HSG_Insight_Export.csv"},
        )
    except Exception as e:
        print(f"LỖI CRASH API /api/export:\n{traceback.format_exc()}")
        raise HTTPException(500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
