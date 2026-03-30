"""
Generate realistic sample HSG (Học sinh giỏi) competition data.
Run this script once to create the Excel file for development.
"""
import pandas as pd
import random
import os
from datetime import date, timedelta

random.seed(42)

SCHOOLS = [
    "THPT Chuyên Lê Hồng Phong", "THPT Chuyên Trần Đại Nghĩa",
    "THPT Nguyễn Thượng Hiền", "THPT Gia Định", "THPT Bùi Thị Xuân",
    "THPT Chuyên Lê Quý Đôn", "THPT Nguyễn Thị Minh Khai",
    "THPT Trần Phú", "THPT Mạc Đĩnh Chi", "THPT Nguyễn Du",
    "THPT Hùng Vương", "THPT Marie Curie", "THPT Lương Thế Vinh",
    "THPT Nguyễn Hữu Huân", "THPT Võ Thị Sáu"
]

SUBJECTS = ["Toán", "Vật lý", "Hóa học", "Sinh học", "Tin học",
            "Ngữ văn", "Lịch sử", "Địa lý", "Tiếng Anh"]

HO_NAM = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan",
           "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương"]
DEM = ["Văn", "Thị", "Minh", "Đức", "Thanh", "Hoàng", "Quốc",
       "Ngọc", "Phương", "Hữu", "Thành", "Bảo", "Anh", "Hải", "Tuấn"]
TEN_NAM = ["An", "Bình", "Cường", "Đạt", "Dũng", "Hải", "Hùng",
           "Khoa", "Long", "Minh", "Nam", "Phúc", "Quân", "Sơn",
           "Thắng", "Toàn", "Trung", "Tú", "Tuấn", "Vinh"]
TEN_NU = ["Anh", "Chi", "Dung", "Hà", "Hạnh", "Hương", "Lan",
          "Linh", "Mai", "My", "Nga", "Ngọc", "Như", "Phương",
          "Thảo", "Trang", "Trinh", "Vân", "Vy", "Yến"]

NOI_SINH = ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Bình Dương",
            "Đồng Nai", "Cần Thơ", "Hải Phòng", "Khánh Hòa",
            "Thừa Thiên Huế", "Nghệ An", "Thanh Hóa", "Long An"]

YEARS = [2023, 2024, 2025]

LOP_OPTIONS = ["10", "11", "12"]


def generate_name(gender: str) -> str:
    ho = random.choice(HO_NAM)
    dem = random.choice(DEM)
    if gender == "Nam":
        ten = random.choice(TEN_NAM)
    else:
        ten = random.choice(TEN_NU)
    return f"{ho} {dem} {ten}"


def score_to_result(score: float, subject: str) -> tuple[str, str]:
    """Determine Kết quả and Xếp giải based on score."""
    if score >= 18:
        return "Đạt giải", "Nhất"
    elif score >= 16:
        return "Đạt giải", "Nhì"
    elif score >= 14:
        return "Đạt giải", "Ba"
    elif score >= 12:
        return "Đạt giải", "Khuyến khích"
    else:
        return "Không đạt giải", "Không"


def generate_data(n_records: int = 300) -> pd.DataFrame:
    records = []
    for i in range(1, n_records + 1):
        year = random.choice(YEARS)
        gender = random.choice(["Nam", "Nữ"])
        name = generate_name(gender)
        school = random.choice(SCHOOLS)
        subject = random.choice(SUBJECTS)
        lop = random.choice(LOP_OPTIONS)

        # Generate birthday (age 15-18)
        birth_year = year - random.randint(15, 18)
        birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))

        # Score distribution: slight right skew for realism
        base = random.gauss(13.5, 3.0)
        score = round(max(5.0, min(20.0, base)), 1)

        ket_qua, xep_giai = score_to_result(score, subject)

        sbd = f"{year % 100:02d}{subject[:2].upper()}{i:04d}"

        records.append({
            "STT": i,
            "SBD": sbd,
            "Họ và tên": name,
            "Ngày sinh": birth_date.strftime("%d/%m/%Y"),
            "Nơi sinh": random.choice(NOI_SINH),
            "Giới tính": gender,
            "Lớp": lop,
            "Trường": school,
            "Môn thi": subject,
            "Điểm": score,
            "Kết quả": ket_qua,
            "Xếp giải": xep_giai,
            "Năm thi": year
        })

    df = pd.DataFrame(records)
    # Re-index STT
    df["STT"] = range(1, len(df) + 1)
    return df


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, "hsg_data.xlsx")

    df = generate_data(300)
    df.to_excel(filepath, index=False, engine="openpyxl")
    print(f"✅ Generated {len(df)} records → {filepath}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Schools: {df['Trường'].nunique()}")
    print(f"   Subjects: {df['Môn thi'].nunique()}")
    print(f"   Score range: {df['Điểm'].min()} - {df['Điểm'].max()}")
    print(f"   Prize distribution:")
    print(df["Xếp giải"].value_counts().to_string())
