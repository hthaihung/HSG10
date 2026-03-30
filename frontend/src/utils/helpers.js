export function getPrizeBadgeClass(prize) {
  const base = "inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide whitespace-nowrap border backdrop-blur-sm";
  switch (prize) {
    case 'Nhất':
      return `${base} bg-amber-50/90 text-amber-700 border-amber-200/70 dark:bg-amber-400/10 dark:text-amber-200 dark:border-amber-300/20`;
    case 'Nhì':
      return `${base} bg-slate-100/90 text-slate-600 border-slate-200/80 dark:bg-slate-300/10 dark:text-slate-200 dark:border-slate-300/20`;
    case 'Ba':
      return `${base} bg-orange-50/90 text-orange-700 border-orange-200/70 dark:bg-orange-400/10 dark:text-orange-200 dark:border-orange-300/20`;
    case 'Khuyến khích':
      return `${base} bg-emerald-50/90 text-emerald-700 border-emerald-200/70 dark:bg-emerald-400/10 dark:text-emerald-200 dark:border-emerald-300/20`;
    default:
      return `${base} bg-slate-50 text-slate-500 border-slate-200/70 dark:bg-[#2a2e40]/60 dark:text-[#a6adc8] dark:border-[#4b4f66]/40`;
  }
}

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export const CHART_COLORS = {
  sky: '#6fb9e8',
  skyDeep: '#2e6fa2',
  skySoft: '#e5f1fb',
  mauve: '#b295f2',
  mauveSoft: '#f0ebff',
  peach: '#e39b5f',
  peachSoft: '#fff0e1',
  green: '#5fa97a',
  greenSoft: '#e7f5ee',
  textSecondary: '#4b5563',
  grid: 'rgba(160, 170, 185, 0.08)',
};

export function shortenSchoolName(name) {
  if (!name) return '';
  return name.replace('THPT Chuyên ', 'C.').replace('THPT ', '');
}
