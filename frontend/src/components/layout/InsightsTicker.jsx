import { useEffect, useState } from 'react';
import { Dot } from 'lucide-react';
import { getTickerInsights } from '../../api/client';

export default function InsightsTicker({ filters }) {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

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
            'Bộ lọc đã sẵn sàng.',
            'Theo dõi nhóm điểm nổi bật.',
          ]);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchTicker();
    return () => { active = false; };
  }, [filters]);

  if (loading || insights.length === 0) return null;

  return (
    <div className="w-full bg-[#232136] dark:bg-[#181825] border-b border-[#3b3251] dark:border-[#313244] py-2 overflow-hidden flex items-center shadow-[0_8px_16px_-14px_rgba(0,0,0,0.8)] relative">
      <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-[#232136] dark:from-[#181825] to-transparent z-10 pointer-events-none" />

      <div className="flex whitespace-nowrap animate-marquee">
        {insights.map((msg, index) => (
          <span
            key={`${msg}-${index}`}
            className="inline-flex items-center text-[12px] font-medium text-[#f5e0dc] dark:text-[#cdd6f4] mx-8 tracking-wide"
          >
            {msg}
            <span className="mx-6 opacity-60 text-[#bac2de] dark:text-[#a6adc8]">
              <Dot className="w-4 h-4 inline-block -mt-0.5" />
            </span>
          </span>
        ))}
      </div>

      <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-[#232136] dark:from-[#181825] to-transparent z-10 pointer-events-none" />
    </div>
  );
}
