import { useEffect, useState } from 'react';
import { Sun, Moon, Dot } from 'lucide-react';
import { getTickerInsights } from '../../api/client';

export default function Header({ filters }) {
  const [isDark, setIsDark] = useState(false);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (document.documentElement.classList.contains('dark')) {
      setIsDark(true);
    }
  }, []);

  useEffect(() => {
    let active = true;

    const fetchTicker = async () => {
      setLoading(true);
      try {
        const data = await getTickerInsights(filters);
        if (!active) return;
        const items = (data.insights || []).slice(0, 3);
        setInsights(items.length ? [...items, ...items, ...items] : []);
      } catch {
        if (active) {
          setInsights([
            'Dữ liệu đang cập nhật.',
            'Đang làm mới bộ lọc.',
            'Xem nhanh nhóm nổi bật.',
          ]);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchTicker();
    return () => { active = false; };
  }, [filters]);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    document.documentElement.classList.toggle('dark', nextDark);
  };

  return (
    <header className="sticky top-0 z-50 overflow-hidden border-b border-slate-200/70 bg-white/84 backdrop-blur-xl transition-colors duration-300 dark:border-[#2b2f42] dark:bg-[#171827]/92">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-indigo-500/5 via-transparent to-transparent" />
      <div className="noise-overlay pointer-events-none absolute inset-0 opacity-[0.08]" />

      <div className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 opacity-[0.08] dark:opacity-[0.1]">
        <svg viewBox="0 0 1440 120" className="h-14 w-full text-slate-500/60 dark:text-[#9ab6dd]/55" preserveAspectRatio="none" aria-hidden="true">
          <path
            d="M0 66h110l24-18 20 36 26-72 22 54 26 0 18-18 22 18h118l24-14 22 28 24-54 22 40h36l18-18 18 18h124l20-12 24 24 24-48 20 36h42l18-14 18 14h132l18-18 26 18 24-44 22 30h38l20-12 18 12h118l22-20 20 20 28-46 18 30h156"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <div className="relative mx-auto grid min-h-[64px] max-w-7xl grid-cols-[auto_1fr_auto] items-center gap-4 px-6 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-white/70 bg-white/70 shadow-sm dark:border-[#3a3f54] dark:bg-[#121422]/90">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className="dark:stroke-[#9fb4d8]">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div className="min-w-0">
            <div className="text-[16px] font-display font-semibold tracking-[0.02em] text-slate-900 dark:text-[#eef1f7]">
              HSG 10
            </div>
          </div>
        </div>

        <div className="group relative min-w-0 overflow-hidden rounded-full border border-white/65 bg-white/54 px-4 py-2 shadow-[0_10px_30px_-22px_rgba(15,23,42,0.5)] dark:border-[#2c3044]/70 dark:bg-[#131523]/60">
          <div className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-white via-white/75 to-transparent dark:from-[#1e1e2e] dark:via-[#1e1e2e]/80" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-white via-white/75 to-transparent dark:from-[#1e1e2e] dark:via-[#1e1e2e]/80" />

          {loading || insights.length === 0 ? (
            <div className="truncate text-center text-[12px] font-medium tracking-wide text-slate-600 dark:text-[#bac2de]">
              Đang cập nhật insight...
            </div>
          ) : (
            <div className="flex whitespace-nowrap animate-marquee-slow group-hover:[animation-play-state:paused]">
              {insights.map((msg, index) => (
                <span
                  key={`${msg}-${index}`}
                  className="inline-flex items-center text-[12px] font-medium tracking-wide text-slate-700 dark:text-[#cdd6f4] mx-8"
                >
                  {msg}
                  <span className="mx-5 text-slate-400 dark:text-[#a6adc8]">
                    <Dot className="h-4 w-4" />
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2">
          <button
            onClick={toggleTheme}
            className="rounded-xl border border-slate-200/80 bg-white/78 p-2 text-slate-600 transition-all hover:bg-white hover:border-slate-300 dark:border-[#2c3044] dark:bg-[#121422]/90 dark:text-[#cbd5f0] dark:hover:bg-[#1c1f2d]"
            title="Đổi giao diện"
          >
            {isDark ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
      </div>

      <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-indigo-400/50 to-transparent bg-[length:200%_auto] animate-gradient-x" />
    </header>
  );
}
