import { useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import { CHART_COLORS } from '../../utils/helpers';

function getStudentBinIndex(score) {
  if (score < 10) return 0;
  if (score < 12) return 1;
  if (score < 14) return 2;
  if (score < 16) return 3;
  if (score < 18) return 4;
  return 5;
}

export default function SubjectHistogram({ bins, studentScore, subject }) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const updateTheme = () => setIsDark(document.documentElement.classList.contains('dark'));
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    updateTheme();
    return () => observer.disconnect();
  }, []);

  if (!bins || bins.length === 0) {
    return (
      <div className="card p-6 h-[340px] rounded-[30px] flex items-center justify-center">
        <span className="text-slate-500 dark:text-[#bac2de] font-medium transition-colors">Đang tải phổ điểm...</span>
      </div>
    );
  }

  const studentBinIndex = getStudentBinIndex(parseFloat(studentScore));
  const chartData = {
    labels: bins.map(bin => bin.range),
    datasets: [
      {
        label: 'Số lượng thí sinh',
        data: bins.map(bin => bin.count),
        backgroundColor: bins.map((_, index) =>
          index === studentBinIndex
            ? (isDark ? '#fab387' : CHART_COLORS.peach)
            : (isDark ? '#6a85aa' : '#a9d8ff')
        ),
        hoverBackgroundColor: bins.map((_, index) =>
          index === studentBinIndex
            ? (isDark ? '#f9e2af' : '#e78a3f')
            : (isDark ? '#89dceb' : CHART_COLORS.sky)
        ),
        borderRadius: 10,
        borderSkipped: false,
        maxBarThickness: 38,
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
        titleFont: { family: 'Plus Jakarta Sans', size: 13, weight: '700' },
        bodyFont: { family: 'Plus Jakarta Sans', size: 12, weight: '600' },
        displayColors: false,
        callbacks: {
          afterBody: context => (
            context[0].dataIndex === studentBinIndex
              ? [`Điểm của học sinh: ${studentScore}`]
              : ['Nền tham chiếu toàn môn']
          ),
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
          color: isDark ? '#bac2de' : '#526072',
        },
        border: { display: false },
      },
      y: {
        grid: {
          color: CHART_COLORS.grid,
          drawBorder: false,
        },
        ticks: {
          font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
          color: isDark ? '#a6adc8' : '#526072',
          maxTicksLimit: 6,
        },
        border: { display: false },
      },
    },
  };

  return (
    <div className="group overflow-hidden rounded-[30px] border border-[#cdd6f4]/40 dark:border-[#45475a]/70 bg-[#edf6ff] dark:bg-[#1f2f43] p-6 shadow-[0_2px_15px_-3px_rgba(0,0,0,0.07),0_10px_20px_-2px_rgba(0,0,0,0.04)] transition-all duration-300 hover:-translate-y-1">
      <p className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#2f6db2] dark:text-[#89dceb]">
        Subject Lens
      </p>
      <h3 className="mt-2 text-[20px] font-black tracking-tight text-slate-900 dark:text-[#f5e0dc]">
        Phổ điểm chuyên sâu môn {subject}
      </h3>
      <p className="mt-2 text-[13.5px] leading-6 text-slate-700 dark:text-[#cdd6f4]">
        Cột được tô nổi biểu diễn đúng dải điểm của học sinh trong bối cảnh toàn bộ môn thi.
      </p>
      <div className="relative mt-5 h-[210px] rounded-[24px] border border-white/60 dark:border-white/8 bg-white/72 dark:bg-[#192635] p-4">
        <Bar data={chartData} options={options} />
      </div>
    </div>
  );
}
