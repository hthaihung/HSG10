export default function FilterBar({ filters, filterOptions, onFilterChange }) {
  // Order: Môn thi → Trường → Mức giải → Giới tính
  const FILTERS = [
    { key: 'mon_thi',  label: 'Tất cả môn',      icon: '📚' },
    { key: 'truong',   label: 'Tất cả trường',    icon: '🏫' },
    { key: 'xep_giai', label: 'Kết quả giải',    icon: '🏅' },
    { key: 'gioi_tinh',label: 'Tất cả giới tính', icon: '👤' },
  ];

  const handleChange = (key, val) => {
    onFilterChange({ ...filters, [key]: val });
  };

  return (
    <div className="bg-white/78 backdrop-blur-xl border-b border-slate-200/70 z-40 sticky top-16 shadow-[0_8px_18px_-16px_rgba(15,23,42,0.35)] transition-colors duration-300 dark:bg-[#191b29]/84 dark:border-[#2c3044] dark:shadow-none">
      <div className="max-w-7xl mx-auto px-6 py-4 flex justify-center items-center gap-4 flex-wrap">
        {FILTERS.map(f => {
          const options = filterOptions?.[f.key] || [];
          return (
            <div key={f.key} className="relative flex items-center">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[15px] pointer-events-none z-10">
                {f.icon}
              </span>
              <select
                className="filter-select !pl-10 !pr-10 !py-2.5 !rounded-xl !bg-slate-50 border-slate-200/80 shadow-sm hover:!bg-white dark:!bg-[#141623] dark:border-[#2c3044] dark:text-[#cbd5f0] dark:hover:!bg-[#1d2030] transition-all cursor-pointer font-semibold text-[13px] text-slate-700"
                value={filters[f.key]}
                onChange={e => handleChange(f.key, e.target.value)}
              >
                <option value="Tất cả">{f.label}</option>
                {options.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
}
