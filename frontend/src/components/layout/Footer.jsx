import { useState } from 'react';

export default function Footer() {
  return (
    <footer className="mt-12 pb-6 border-t border-slate-100/80 dark:border-[#2c3044]">
      <div className="max-w-7xl mx-auto px-6 pt-6 flex flex-col items-center justify-center gap-1.5">
        <p className="text-[12.5px] font-medium text-slate-500 dark:text-[#a9b0c6] text-center transition-colors">
          Nền tảng Phân tích &amp; Tra cứu Điểm thi HSG 10 tỉnh Hà Tĩnh
        </p>
        <p className="text-[11px] text-slate-400 dark:text-[#5b6175] text-center transition-colors">
          © thaihung — Dữ liệu được thu thập và xử lý bởi thaihung
        </p>
      </div>
    </footer>
  );
}
