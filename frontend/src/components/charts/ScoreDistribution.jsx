import { useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import { CHART_COLORS } from '../../utils/helpers';

function getDistributionInsight(bins = []) {
  if (!bins.length) return null;

  const total = bins.reduce((sum, bin) => sum + bin.count, 0);
  const dominant = bins.reduce((best, current) => (current.count > best.count ? current : best), bins[0]);
  const share = total > 0 ? (dominant.count / total) * 100 : 0;
  const label = share >= 30 ? 'Chiếm đa số' : dominant.range === '18-20' ? 'Cao nhất' : 'Đột biến';

  return {
    label,
    detail: `${dominant.range}: ${dominant.count.toLocaleString('vi-VN')} em, ${share.toFixed(1)}%.`,
    dominantRange: dominant.range,
  };
}

export default function ScoreDistribution({ data, loading }) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const updateTheme = () => setIsDark(document.documentElement.classList.contains('dark'));
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    updateTheme();
    return () => observer.disconnect();
  }, []);

  if (loading || !data?.bins) {
    return (
      <div className="card p-6 h-[360px] rounded-[30px]">
        <div className="skeleton h-4 w-40 mb-6 rounded-full" />
        <div className="skeleton h-5 w-64 mb-5 rounded-full" />
        <div className="skeleton h-[230px] rounded-[24px]" />
      </div>
    );
  }

  const { bins } = data;
  if (!bins || bins.length === 0) {
    return (
      <div className="card p-6 h-[360px] rounded-[30px] flex items-center justify-center">
        <span className="text-slate-500 dark:text-[#bac2de] font-medium transition-colors">Không có dữ liệu phù hợp</span>
      </div>
    );
  }

  const insight = getDistributionInsight(bins);
  const chartData = {
    labels: bins.map(bin => bin.range),
    datasets: [
      {
        label: 'Số lượng thí sinh',
        data: bins.map(bin => bin.count),
        backgroundColor: bins.map(bin =>
          bin.range === insight?.dominantRange
            ? (isDark ? '#9bb9dd' : CHART_COLORS.sky)
            : (isDark ? '#4f678a' : CHART_COLORS.skySoft)
        ),
        hoverBackgroundColor: bins.map(bin =>
          bin.range === insight?.dominantRange
            ? (isDark ? '#b7cbe6' : CHART_COLORS.skyDeep)
            : (isDark ? '#6781a6' : '#9cc9ed')
        ),
        borderRadius: 10,
        borderSkipped: false,
        maxBarThickness: 42,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: isDark ? '#181825' : '#ffffff',
        titleColor: isDark ? '#f5e0dc' : '#0f172a',
        bodyColor: isDark ? '#cdd6f4' : '#334155',
        borderColor: isDark ? '#45475a' : '#d8e8ff',
        borderWidth: 1,
        padding: 12,
        titleFont: { family: 'Manrope', size: 13, weight: '700' },
        bodyFont: { family: 'Manrope', size: 12, weight: '600' },
        displayColors: false,
        callbacks: {
          afterBody: context => {
            const point = bins[context[0].dataIndex];
            if (!point) return [];
            if (point.range === insight?.dominantRange) return [insight.label];
            return ['Theo dõi nền phân bố'];
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { family: 'Manrope', size: 11, weight: '600' },
          color: isDark ? '#b9c0d5' : '#4b5563',
        },
        border: { display: false },
      },
      y: {
        grid: {
          color: CHART_COLORS.grid,
          drawBorder: false,
        },
        ticks: {
          font: { family: 'Manrope', size: 11, weight: '600' },
          color: isDark ? '#a9b0c6' : '#4b5563',
          maxTicksLimit: 6,
        },
        border: { display: false },
      },
    },
  };

  return (
    <div className="group relative overflow-hidden rounded-[30px] border border-[#d7e5f2]/60 dark:border-[#313a52] bg-[#f1f6fb] dark:bg-[#1b2636] p-6 shadow-[0_14px_28px_-24px_rgba(15,23,42,0.45),0_4px_12px_-6px_rgba(15,23,42,0.18)] transition-all duration-300 hover:-translate-y-1">
      <div className="absolute inset-x-0 top-0 h-20 bg-gradient-to-b from-white/40 to-transparent dark:from-white/5" />
      <div className="relative flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#2e6fa2] dark:text-[#9bb9dd]">
            Phổ điểm
          </p>
          <h3 className="text-[22px] font-display font-semibold tracking-tight text-slate-900 dark:text-[#eef1f7]">
            Phổ điểm thi
          </h3>
          <p className="max-w-xl text-[13px] leading-6 text-slate-600 dark:text-[#c7cede]">
            Nhìn nhanh nhóm điểm đông nhất.
          </p>
        </div>
        {insight && (
          <div className="shrink-0 rounded-2xl border border-white/70 dark:border-white/10 bg-white/76 dark:bg-[#151826]/60 px-4 py-3 backdrop-blur-sm">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-[#b9c0d5]">
              {insight.label}
            </p>
            <p className="mt-2 text-[13px] leading-5 font-semibold text-slate-900 dark:text-[#eef1f7]">
              {insight.detail}
            </p>
          </div>
        )}
      </div>

      <div className="relative mt-6 h-[235px] rounded-[24px] border border-white/70 dark:border-white/8 bg-white/78 dark:bg-[#131b27] p-4">
        <Bar data={chartData} options={options} />
      </div>
    </div>
  );
}
