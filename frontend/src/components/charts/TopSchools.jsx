import { useEffect, useState, useRef } from 'react';
import { Bar, getElementAtEvent } from 'react-chartjs-2';
import { CHART_COLORS, shortenSchoolName } from '../../utils/helpers';

function getSchoolInsight(schools = [], metric = 'prizes') {
  if (!schools.length) return null;

  const first = schools[0];
  const second = schools[1];
  const gap = second ? first.value - second.value : first.value;
  const label = second && gap > 0 ? 'Cao nhất' : 'Dẫn đầu';
  const metricLabel = metric === 'prizes' ? 'giải' : 'điểm TB';

  return {
    label,
    detail: `${first.school}: ${first.value.toLocaleString('vi-VN')} ${metricLabel}${second ? `, hơn ${gap.toLocaleString('vi-VN')}` : ''}.`,
  };
}

export default function TopSchools({ data, loading, onMetricChange, metric, onSchoolClick }) {
  const [isDark, setIsDark] = useState(false);
  const chartRef = useRef();

  useEffect(() => {
    const updateTheme = () => setIsDark(document.documentElement.classList.contains('dark'));
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    updateTheme();
    return () => observer.disconnect();
  }, []);

  const handleOnClick = event => {
    if (!chartRef.current || !data?.schools || !onSchoolClick) return;
    const elements = getElementAtEvent(chartRef.current, event);
    if (elements.length > 0) {
      onSchoolClick(data.schools[elements[0].index].school);
    }
  };

  if (loading || !data?.schools) {
    return (
      <div className="card p-6 h-[360px] rounded-[30px]">
        <div className="skeleton h-4 w-40 mb-6 rounded-full" />
        <div className="skeleton h-5 w-72 mb-5 rounded-full" />
        <div className="skeleton h-[230px] rounded-[24px]" />
      </div>
    );
  }

  const { schools } = data;
  if (!schools || schools.length === 0) {
    return (
      <div className="card p-6 h-[360px] rounded-[30px] flex items-center justify-center">
        <span className="text-slate-500 dark:text-[#bac2de] font-medium transition-colors">Không có dữ liệu phù hợp</span>
      </div>
    );
  }

  const insight = getSchoolInsight(schools, metric);
  const chartData = {
    labels: schools.map(school => shortenSchoolName(school.school)),
    datasets: [
      {
        label: metric === 'prizes' ? 'Số giải' : 'Điểm TB',
        data: schools.map(school => school.value),
        backgroundColor: schools.map((_, index) => {
          if (index === 0) return isDark ? '#f2b47c' : CHART_COLORS.peach;
          if (index < 3) return isDark ? '#bfa4f0' : CHART_COLORS.mauve;
          return isDark ? '#9bb9dd' : CHART_COLORS.sky;
        }),
        hoverBackgroundColor: schools.map((_, index) => {
          if (index === 0) return isDark ? '#f7c99f' : '#d78c4f';
          if (index < 3) return isDark ? '#d2bff6' : '#9a84ea';
          return isDark ? '#b7cbe6' : CHART_COLORS.skyDeep;
        }),
        borderRadius: 10,
        borderSkipped: false,
        barThickness: 14,
      },
    ],
  };

  const options = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    onClick: handleOnClick,
    onHover: (event, elements) => {
      event.native.target.style.cursor = elements[0] ? 'pointer' : 'default';
    },
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
          title: context => schools[context[0].dataIndex].school,
          afterBody: context => {
            const index = context[0].dataIndex;
            if (index === 0) return ['Cao nhất'];
            if (index < 3) return ['Top 3 nổi bật'];
            return ['Nền so sánh'];
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: CHART_COLORS.grid,
          drawBorder: false,
        },
        ticks: {
          font: { family: 'Manrope', size: 11, weight: '600' },
          color: isDark ? '#a9b0c6' : '#4b5563',
        },
        border: { display: false },
        beginAtZero: true,
      },
      y: {
        grid: { display: false },
        ticks: {
          align: 'right',
          crossAlign: 'near',
          font: { family: 'Manrope', size: 11, weight: '700' },
          color: isDark ? '#d7dbe8' : '#1f2937',
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
            Trường học
          </p>
          <h3 className="text-[22px] font-display font-semibold tracking-tight text-slate-900 dark:text-[#eef1f7]">
            Top trường
          </h3>
          <p className="max-w-xl text-[13px] leading-6 text-slate-600 dark:text-[#c7cede]">
            Highlight top 3 trường dẫn đầu.
          </p>
        </div>
        <div className="flex rounded-2xl border border-white/70 dark:border-white/10 bg-white/76 dark:bg-[#151826]/60 p-1 backdrop-blur-sm">
          <button
            onClick={() => onMetricChange('prizes')}
            className={`px-3.5 py-2 rounded-xl text-[12px] font-bold transition-colors ${
              metric === 'prizes'
                ? 'bg-[#fff0e5] text-[#c26b2b] dark:bg-[#2f241f] dark:text-[#f2b47c]'
                : 'text-slate-600 dark:text-[#a9b0c6]'
            }`}
          >
            Số giải
          </button>
          <button
            onClick={() => onMetricChange('avg_score')}
            className={`px-3.5 py-2 rounded-xl text-[12px] font-bold transition-colors ${
              metric === 'avg_score'
                ? 'bg-[#e6f1fb] text-[#2e6fa2] dark:bg-[#1f2a3c] dark:text-[#9bb9dd]'
                : 'text-slate-600 dark:text-[#a9b0c6]'
            }`}
          >
            Điểm TB
          </button>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-white/70 dark:border-white/10 bg-white/76 dark:bg-[#151826]/60 px-4 py-3 backdrop-blur-sm">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-[#b9c0d5]">
          {insight?.label}
        </p>
        <p className="mt-2 text-[13px] leading-5 font-semibold text-slate-900 dark:text-[#eef1f7]">
          {insight?.detail}
        </p>
      </div>

      <div className="relative mt-5 h-[210px] rounded-[24px] border border-white/70 dark:border-white/8 bg-white/78 dark:bg-[#131b27] p-4">
        <Bar ref={chartRef} data={chartData} options={options} />
      </div>
    </div>
  );
}
