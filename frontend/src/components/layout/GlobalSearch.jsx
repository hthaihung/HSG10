import { useState, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { getStudents } from '../../api/client';

export default function GlobalSearch({ onSelectStudent, variant = 'default' }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const wrapperRef = useRef(null);
  const isCompact = variant !== 'default';

  const containerClass = variant === 'default'
    ? 'relative w-full max-w-2xl mx-auto z-50 animate-fade-in-up'
    : 'relative w-full max-w-3xl mx-auto z-50';

  const inputSizeClass = variant === 'fullscreen'
    ? 'py-2.5 text-[13px] rounded-xl'
    : variant === 'table'
      ? 'py-3 text-[13.5px] rounded-2xl'
      : 'py-3.5 text-[14px] rounded-2xl';

  useEffect(() => {
    if (!query.trim()) { setResults([]); setShowDropdown(false); return; }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await getStudents({}, query, 1, 5);
        setResults(data.students || []);
        setShowDropdown(true);
      } catch (err) {
        console.error('Search error', err);
      } finally {
        setLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const handler = e => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target))
        setShowDropdown(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = student => {
    onSelectStudent(student);
    setShowDropdown(false);
    setQuery('');
  };

  return (
    <div ref={wrapperRef} className={containerClass}>
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-slate-400 dark:text-[#a9b0c6] group-focus-within:text-slate-700 dark:group-focus-within:text-[#eef1f7] transition-colors" />
        </div>
        <input
          type="text"
          className={`block w-full pl-12 pr-12 bg-white border border-slate-200/80 ${inputSizeClass} font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-200 focus:border-slate-300 dark:bg-[#121422] dark:border-[#2c3044] dark:text-[#eef1f7] dark:focus:ring-[#2c3044] transition-all dark:placeholder-[#5b6175] placeholder-slate-400`}
          placeholder="Tìm tên hoặc SBD học sinh..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => { if (query.trim() && results.length > 0) setShowDropdown(true); }}
        />
        {loading ? (
          <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
            <Loader2 className="h-5 w-5 text-slate-400 dark:text-[#9bb9dd] animate-spin" />
          </div>
        ) : !isCompact && (
          <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
            <span className="text-[11px] font-semibold text-slate-300 dark:text-[#3b3f55]">Tìm nhanh</span>
          </div>
        )}
      </div>

      {showDropdown && (
        <div className="absolute mt-2 w-full bg-white/96 dark:bg-[#151826]/95 rounded-2xl border border-slate-100/80 dark:border-[#2c3044] shadow-[0_12px_34px_-18px_rgba(15,23,42,0.35)] dark:shadow-none overflow-hidden backdrop-blur-md">
          {results.length === 0 ? (
            <div className="p-4 text-center text-[13px] font-medium text-slate-500 dark:text-[#a6adc8]">
              Không tìm thấy kết quả nào cho "{query}"
            </div>
          ) : (
            <ul className="max-h-72 overflow-y-auto py-2">
              {results.map((s, i) => (
                <li
                  key={i}
                  onClick={() => handleSelect(s)}
                  className="px-5 py-3.5 hover:bg-slate-50 dark:hover:bg-[#202335] cursor-pointer transition-colors border-b border-slate-50 last:border-0 dark:border-[#232638]"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-[14px] font-semibold text-slate-900 dark:text-[#eef1f7]">{s.ho_ten}</p>
                      <p className="text-[12px] font-medium text-slate-500 dark:text-[#b9c0d5] mt-0.5">
                        <span className="text-slate-400 dark:text-[#5b6175]">SBD:</span> {s.sbd}
                        <span className="text-slate-300 dark:text-[#3b3f55] mx-1">•</span>
                        {s.truong}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-[15px] font-bold text-[#2e6fa2] dark:text-[#9bb9dd] tabular-nums">{s.diem}</span>
                      <p className="text-[11px] font-semibold text-slate-400 dark:text-[#a9b0c6] mt-0.5">{s.mon_thi}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
