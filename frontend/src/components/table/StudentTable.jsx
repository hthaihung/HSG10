import { ChevronLeft, ChevronRight, Users, Maximize } from 'lucide-react';
import { getPrizeBadgeClass } from '../../utils/helpers';

export default function StudentTable({ data, loading, onPageChange, onRowClick, isFullscreenMode, onToggleFullscreen }) {

  if (loading || !data) {
    return (
      <div className="card w-full overflow-hidden rounded-2xl dark:bg-[#313244]">
      <div className="p-6 border-b border-slate-100/80 dark:border-[#2c3044] flex justify-between items-center">
          <div className="skeleton h-5 w-48 rounded" />
          <div className="skeleton h-9 w-24 rounded-lg" />
        </div>
        <div className="p-6">
          {Array(8).fill(0).map((_, i) => (
            <div key={i} className="skeleton h-12 w-full mb-3 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const { students = [], total = 0, page = 1, total_pages = 0 } = data;
  const fullscreenColumns = [
    { key: 'SBD', className: 'w-[96px]' },
    { key: 'Họ và tên', className: 'min-w-[180px]' },
    { key: 'Trường', className: 'min-w-[160px]' },
    { key: 'Môn thi', className: 'min-w-[120px]' },
    { key: 'Điểm', className: 'w-[84px]' },
    { key: 'Thành tích', className: 'min-w-[120px]' },
  ];

  // ── Fullscreen mode: fixed overlay, max table height, search bar restored in caller
  if (isFullscreenMode) {
    return (
      <div className="flex flex-col w-full h-full bg-slate-50 dark:bg-[#1e1e2e] text-slate-800 dark:text-[#cdd6f4] overflow-hidden">
        {/* Table fills rest */}
        <div className="flex-1 min-h-0 overflow-auto">
          <table className="w-full text-left border-collapse min-h-full">
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-slate-200/80 dark:border-[#2c3044] bg-slate-100/80 dark:bg-[#151826] backdrop-blur-md">
                {fullscreenColumns.map(col => (
                  <th
                    key={col.key}
                    className={`px-4 py-2.5 text-[10px] font-semibold text-slate-500 dark:text-[#b9c0d5] uppercase tracking-[0.2em] whitespace-nowrap ${col.className}`}
                  >
                    {col.key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {students.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-24 text-center text-slate-400 dark:text-[#a6adc8] text-[14px] font-medium">
                    📭 Chưa có thí sinh nào trong danh sách
                  </td>
                </tr>
              ) : students.map((s, i) => (
                <tr
                  key={i}
                  onClick={() => onRowClick(s)}
                  className="border-b border-slate-100/80 dark:border-[#232638] hover:bg-white dark:hover:bg-[#202335] cursor-pointer transition-colors group"
                >
                  <td className="px-4 py-2.5 text-[13px] text-slate-500 dark:text-[#b9c0d5] font-mono font-medium w-[96px]">{s.sbd}</td>
                  <td className="px-4 py-2.5 text-[13px] text-slate-900 dark:text-[#eef1f7] font-semibold whitespace-nowrap group-hover:text-slate-800 dark:group-hover:text-[#f0f2fa] transition-colors min-w-[180px]">{s.ho_ten}</td>
                  <td className="px-4 py-2.5 text-[12.5px] text-slate-600 dark:text-[#b9c0d5] font-medium whitespace-nowrap min-w-[160px]">{s.truong}</td>
                  <td className="px-4 py-2.5 text-[12.5px] text-slate-600 dark:text-[#b9c0d5] font-medium whitespace-nowrap min-w-[120px]">{s.mon_thi}</td>
                  <td className="px-4 py-2.5 text-[13px] text-[#2e6fa2] dark:text-[#9bb9dd] font-black tabular-nums w-[84px]">{s.diem}</td>
                  <td className="px-4 py-2.5 min-w-[120px]">
                    <span className={`${getPrizeBadgeClass(s.xep_giai)} text-[11px] px-2 py-0.5`}>
                      {s.xep_giai === 'Không có' ? 'Chưa đạt giải' : s.xep_giai}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total_pages > 1 && (
          <div className="px-4 py-2.5 border-t border-slate-200 dark:border-[#2c3044] flex items-center justify-between bg-slate-100/60 dark:bg-[#151826] shrink-0">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-[#b9c0d5] hover:bg-slate-200 dark:hover:bg-[#2b3044] rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" /> Trước
            </button>
            <span className="text-[12px] text-slate-500 dark:text-[#a9b0c6] font-semibold">
              {total.toLocaleString('vi-VN')} thí sinh · Trang {page}/{total_pages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= total_pages}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-[#b9c0d5] hover:bg-slate-200 dark:hover:bg-[#2b3044] rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Sau <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    );
  }

  // ── Normal (embedded) mode
  return (
    <div className="card w-full overflow-hidden rounded-2xl dark:bg-[#232638] transition-all duration-300 flex flex-col min-h-[520px] lg:min-h-[60vh]">
      <div className="p-5 border-b border-slate-100/80 dark:border-[#2c3044] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 flex items-center justify-center bg-slate-100 text-slate-500 rounded-xl dark:bg-[#151826] dark:text-[#9bb9dd]">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-[16px] font-display font-semibold text-slate-900 dark:text-[#eef1f7]">Bảng điểm chi tiết</h3>
            <p className="text-[13px] font-medium text-slate-500 dark:text-[#a9b0c6] mt-0.5">
              {total.toLocaleString('vi-VN')} thí sinh · Trang {total_pages > 0 ? page : 0}/{total_pages}
            </p>
          </div>
        </div>
        <div className="flex w-full sm:w-auto items-center gap-2">
          <button
            onClick={onToggleFullscreen}
            title="Phóng to toàn màn hình"
            className="flex items-center gap-1.5 px-4 py-2.5 bg-white border border-slate-200/80 rounded-xl text-[13px] font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-800 dark:bg-[#151826] dark:border-[#2c3044] dark:text-[#b9c0d5] dark:hover:bg-[#1f2232] dark:hover:text-[#eef1f7] transition-all"
          >
            <Maximize size={16} />
            <span className="hidden sm:inline">Phóng to</span>
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100/80 dark:border-[#2c3044] bg-slate-50/60 dark:bg-[#151826]/60">
              {['SBD','Họ và tên','Trường','Môn thi','Điểm','Thành tích'].map(h => (
                <th key={h} className="px-5 py-3 text-[11px] font-semibold text-slate-500 dark:text-[#b9c0d5] uppercase tracking-[0.2em] whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-20 text-center text-slate-400 dark:text-[#a6adc8] text-[14px] font-medium">
                  📭 Chưa có thí sinh nào trong danh sách
                </td>
              </tr>
            ) : students.map((s, i) => (
              <tr
                key={i}
                onClick={() => onRowClick(s)}
                className="border-b border-slate-50/70 dark:border-[#232638] hover:bg-slate-50/70 dark:hover:bg-[#202335] cursor-pointer transition-colors group"
              >
                <td className="px-5 py-3 text-[14px] text-slate-500 font-mono font-medium dark:text-[#b9c0d5]">{s.sbd}</td>
                <td className="px-5 py-3 text-[14px] text-slate-900 font-semibold whitespace-nowrap dark:text-[#eef1f7] group-hover:text-slate-800 dark:group-hover:text-[#f0f2fa] transition-colors">{s.ho_ten}</td>
                <td className="px-5 py-3 text-[13.5px] text-slate-500 font-medium whitespace-nowrap dark:text-[#b9c0d5]">{s.truong}</td>
                <td className="px-5 py-3 text-[13.5px] text-slate-500 font-medium whitespace-nowrap dark:text-[#b9c0d5]">{s.mon_thi}</td>
                <td className="px-5 py-3 text-[15px] text-[#2e6fa2] font-black tabular-nums dark:text-[#9bb9dd]">{s.diem}</td>
                <td className="px-5 py-3">
                  <span className={`${getPrizeBadgeClass(s.xep_giai)} text-[12px] px-2.5 py-1`}>
                    {s.xep_giai === 'Không có' ? 'Chưa đạt giải' : s.xep_giai}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {total_pages > 1 && (
        <div className="px-5 py-3 border-t border-slate-100/80 dark:border-[#2c3044] flex items-center justify-between bg-white/90 dark:bg-[#1c2031]">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12.5px] font-semibold text-slate-600 hover:bg-slate-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed dark:text-[#b9c0d5] dark:hover:bg-[#2b3044] transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Trước
          </button>

          <div className="flex bg-slate-50 dark:bg-[#151826] p-1 rounded-xl hidden sm:flex">
            {Array.from({ length: total_pages }, (_, i) => i + 1)
              .filter(p => p === 1 || p === total_pages || Math.abs(p - page) <= 1)
              .map((p, idx, arr) => (
                <div key={p} className="flex items-center">
                  {idx > 0 && p - arr[idx - 1] > 1 && (
                    <span className="px-2 text-slate-400 text-[12px] font-bold">...</span>
                  )}
                  <button
                    onClick={() => onPageChange(p)}
                    className={`w-8 h-8 flex items-center justify-center rounded-lg text-[12.5px] font-bold transition-colors ${
                      p === page
                        ? 'bg-white shadow-sm text-slate-900 dark:bg-[#2b3044] dark:text-[#eef1f7]'
                        : 'text-slate-500 hover:bg-white/50 dark:text-[#a9b0c6] dark:hover:bg-[#1f2232]'
                    }`}
                  >{p}</button>
                </div>
              ))}
          </div>

          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= total_pages}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12.5px] font-semibold text-slate-600 hover:bg-slate-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed dark:text-[#b9c0d5] dark:hover:bg-[#2b3044] transition-colors"
          >
            Sau <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
