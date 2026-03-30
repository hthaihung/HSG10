function getDominantBand(bins = []) {
  if (!bins.length) return null;
  return bins.reduce((best, current) => (current.count > best.count ? current : best), bins[0]);
}

function getHeroInsight({ topSchoolsData, scoreDist, filters }) {
  const dominantBand = getDominantBand(scoreDist?.bins || []);
  const leadSchool = topSchoolsData?.schools?.[0];

  if (leadSchool && (!filters?.truong || filters.truong === 'Tất cả')) {
    return {
      label: 'NỔI BẬT',
      title: leadSchool.school,
      note: 'Trường có nhiều giải nhất',
    };
  }

  if (dominantBand) {
    return {
      label: 'PHỔ ĐIỂM',
      title: dominantBand.range,
      note: `${dominantBand.count.toLocaleString('vi-VN')} học sinh`,
    };
  }

  return {
    label: 'TỔNG SỐ GIẢI',
    title: 'Số liệu tập trung',
    note: 'Khung dữ liệu hiện tại',
  };
}

function SmallKpiCard({ card, delay }) {
  return (
    <div
      className={`group relative overflow-hidden rounded-[28px] border ${card.border} ${card.surface} p-5 shadow-[0_12px_28px_-24px_rgba(15,23,42,0.5),0_3px_10px_-6px_rgba(15,23,42,0.18)] transition-all duration-300 hover:-translate-y-1 animate-fade-in-up`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="absolute inset-x-6 top-0 h-px bg-white/50 dark:bg-white/10" />
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-600 dark:text-[#b9c0d5]">
            {card.label}
          </p>
          <div className={`text-[34px] leading-none font-black tracking-tight font-mono [font-variant-numeric:tabular-nums] ${card.valueClass}`}>
            {card.value}
          </div>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border ${card.iconBorder} ${card.iconSurface} text-[13px] font-semibold tracking-[0.18em] text-slate-500 dark:text-[#b9c0d5] shadow-inner`}>
          {card.icon}
        </div>
      </div>
    </div>
  );
}

export default function KPICards({ stats, loading, filters, scoreDist, topSchoolsData }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="card lg:col-span-8 p-8 h-[250px] rounded-[32px] animate-pulse-custom">
          <div className="skeleton h-4 w-40 mb-6 rounded-full" />
          <div className="skeleton h-16 w-48 mb-4 rounded-2xl" />
          <div className="skeleton h-4 w-full max-w-xl rounded-full" />
        </div>
        <div className="lg:col-span-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-5">
          {Array(3).fill(0).map((_, index) => (
            <div key={index} className="card p-6 h-[150px] rounded-[28px] animate-pulse-custom">
              <div className="skeleton h-3 w-20 mb-5 rounded-full" />
              <div className="skeleton h-10 w-24 mb-4 rounded-2xl" />
              <div className="skeleton h-3 w-full rounded-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const hidePassRate = ['Nhất', 'Nhì', 'Ba', 'Khuyến khích'].includes(filters?.xep_giai);
  const heroInsight = getHeroInsight({ topSchoolsData, scoreDist, filters });
  const prizeBreakdown = stats.prize_breakdown || {};
  const prizeLevels = [
    {
      key: 'Nhất',
      badgeLabel: 'Nhất',
      border: 'border-amber-200/80 dark:border-amber-300/25',
      surface: 'bg-amber-50/90 dark:bg-amber-400/10',
      labelColor: 'text-amber-500 dark:text-amber-200/80',
      countColor: 'text-amber-800 dark:text-amber-100',
    },
    {
      key: 'Nhì',
      badgeLabel: 'Nhì',
      border: 'border-slate-200/80 dark:border-slate-300/25',
      surface: 'bg-slate-50/80 dark:bg-slate-300/10',
      labelColor: 'text-slate-500 dark:text-slate-200/80',
      countColor: 'text-slate-700 dark:text-slate-100',
    },
    {
      key: 'Ba',
      badgeLabel: 'Ba',
      border: 'border-orange-200/80 dark:border-orange-300/25',
      surface: 'bg-orange-50/80 dark:bg-orange-400/10',
      labelColor: 'text-orange-500 dark:text-orange-200/80',
      countColor: 'text-orange-700 dark:text-orange-100',
    },
    {
      key: 'Khuyến khích',
      badgeLabel: 'KK',
      border: 'border-emerald-200/80 dark:border-emerald-300/25',
      surface: 'bg-emerald-50/90 dark:bg-emerald-400/10',
      labelColor: 'text-emerald-500 dark:text-emerald-200/80',
      countColor: 'text-emerald-700 dark:text-emerald-100',
    },
  ];
  const sideCards = [
    {
      key: 'total',
      label: 'Tổng thí sinh',
      value: stats.total.toLocaleString('vi-VN'),
      icon: '01',
      surface: 'bg-[#f4f0ff] dark:bg-[#23243a]',
      border: 'border-[#d9cff6]/70 dark:border-[#3a3c57]',
      iconSurface: 'bg-white/80 dark:bg-[#1c1e2d]',
      iconBorder: 'border-[#d9cff6]/70 dark:border-[#3a3c57]',
      valueClass: 'text-[#6a4fc7] dark:text-[#c9c2f6]',
    },
    {
      key: 'avg_score',
      label: 'Điểm trung bình',
      value: stats.avg_score.toFixed(1),
      icon: 'TB',
      surface: 'bg-[#eaf4fb] dark:bg-[#1f2b3c]',
      border: 'border-[#cfe3f4]/80 dark:border-[#334156]',
      iconSurface: 'bg-white/80 dark:bg-[#1c1e2d]',
      iconBorder: 'border-[#cfe3f4]/80 dark:border-[#334156]',
      valueClass: 'text-[#2e6fa2] dark:text-[#9bb9dd]',
    },
    {
      key: 'pass_rate',
      label: 'Tỷ lệ có giải',
      value: `${stats.pass_rate.toFixed(1)}%`,
      icon: '%',
      surface: 'bg-[#e9f6ef] dark:bg-[#1d2d27]',
      border: 'border-[#cbe7d7]/80 dark:border-[#30463d]',
      iconSurface: 'bg-white/80 dark:bg-[#1c1e2d]',
      iconBorder: 'border-[#cbe7d7]/80 dark:border-[#30463d]',
      valueClass: 'text-[#2f8a5a] dark:text-[#a6d9bd]',
    },
  ].filter(card => !hidePassRate || card.key !== 'pass_rate');

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <div className="lg:col-span-8 relative overflow-hidden rounded-[32px] border border-[#ead8c9]/70 dark:border-[#3c3548] bg-[linear-gradient(135deg,rgba(255,249,242,0.98)_0%,rgba(248,244,255,0.96)_55%,rgba(239,248,255,0.96)_100%)] dark:bg-[linear-gradient(135deg,rgba(44,36,38,0.98)_0%,rgba(35,33,49,0.96)_55%,rgba(24,34,44,0.96)_100%)] p-7 sm:p-8 shadow-[0_14px_32px_-24px_rgba(15,23,42,0.45),0_4px_12px_-6px_rgba(15,23,42,0.2)] transition-all duration-300 hover:-translate-y-1 animate-fade-in-up">
        <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-white/40 blur-2xl dark:bg-amber-200/8" />
        <div className="absolute bottom-0 left-0 h-28 w-28 rounded-full bg-[#9cc7e8]/16 blur-2xl dark:bg-[#8cb4d5]/10" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex-1 space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.34em] text-slate-600 dark:text-[#d7dbe8]">
              {heroInsight.label}
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <span className="text-[60px] sm:text-[72px] leading-none font-black tracking-[-0.04em] font-mono [font-variant-numeric:tabular-nums] text-[#c26b2b] dark:text-[#f2b47c]">
                {stats.total_prizes.toLocaleString('vi-VN')}
              </span>
              <span className="pb-2 text-[14px] font-semibold tracking-[0.2em] uppercase text-slate-500 dark:text-[#cbd2e6]">
                giải
              </span>
            </div>
            {heroInsight.title && (
              <p className="text-[17px] font-display font-semibold text-slate-900 dark:text-[#eef1f7]">
                {heroInsight.title}
              </p>
            )}
            {heroInsight.note && (
              <p className="text-[13px] text-slate-600 dark:text-[#c7cede]">
                {heroInsight.note}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            {prizeLevels.map(level => {
              const count = prizeBreakdown[level.key] ?? 0;
              return (
                <div
                  key={level.key}
                  className={`min-w-[110px] flex-shrink-0 rounded-[26px] border px-4 py-3 backdrop-blur-sm ${level.surface} ${level.border}`}
                >
                  <p className={`text-[10px] uppercase tracking-[0.4em] ${level.labelColor}`}>
                    {level.badgeLabel}
                  </p>
                  <p className={`text-[20px] leading-none font-black font-mono ${level.countColor}`}>
                    {count.toLocaleString('vi-VN')}
                  </p>
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 dark:text-[#bac2de]">
                    giải
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className={`lg:col-span-4 grid gap-5 ${sideCards.length === 2 ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-1' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-1'}`}>
        {sideCards.map((card, index) => (
          <SmallKpiCard key={card.key} card={card} delay={120 + (index * 90)} />
        ))}
      </div>
    </div>
  );
}
