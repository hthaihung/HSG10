import { useState, useEffect } from 'react';

import Header from './components/layout/Header';
import FilterBar from './components/layout/FilterBar';
import Footer from './components/layout/Footer';
import GlobalSearch from './components/layout/GlobalSearch';
import KPICards from './components/cards/KPICards';
import ScoreDistribution from './components/charts/ScoreDistribution';
import TopSchools from './components/charts/TopSchools';
import StudentTable from './components/table/StudentTable';
import CenteredProfileModal from './components/modal/CenteredProfileModal';
import { X } from 'lucide-react';

import {
  getFilters, getDashboard
} from './api/client';

export default function App() {
  const [filterOptions, setFilterOptions] = useState(null);

  // ── Initial state: ALL filters 'Tất cả' — prevents blank initial load
  const [filters, setFilters] = useState({
    mon_thi:  'Tất cả',
    truong:   'Tất cả',
    xep_giai: 'Tất cả',
    gioi_tinh:'Tất cả',
  });

  const [stats,         setStats]         = useState(null);
  const [scoreDist,     setScoreDist]     = useState(null);
  const [topSchoolsData,setTopSchoolsData] = useState(null);
  const [studentsData,  setStudentsData]  = useState(null);

  const [dashLoading, setDashLoading] = useState(true);
  const [studentsLoading, setStudentsLoading] = useState(true);
  const [apiError, setApiError] = useState(false);
  const [page, setPage] = useState(1);
  const [schoolMetric, setSchoolMetric] = useState('prizes');

  const [selectedStudent,   setSelectedStudent]   = useState(null);
  const [isTableFullscreen, setIsTableFullscreen] = useState(false);

  // Fullscreen: lock body scroll + Esc to exit
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') setIsTableFullscreen(false); };
    if (isTableFullscreen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', onKey);
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', onKey);
    };
  }, [isTableFullscreen]);

  useEffect(() => {
    getFilters().then(setFilterOptions).catch(console.error);
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setDashLoading(true);
      setStudentsLoading(true);
      setApiError(false);
      try {
        const data = await getDashboard(filters, {
          search: '',
          page,
          pageSize: 20,
          metric: schoolMetric,
        });

        setStats(data?.stats || null);
        setScoreDist(data?.chart || null);
        setTopSchoolsData(
          Array.isArray(data?.top_schools)
            ? { schools: data.top_schools }
            : (data?.top_schools || null),
        );

        if (Array.isArray(data?.students)) {
          setStudentsData({
            students: data.students,
            total: data.students.length,
            page,
            page_size: 20,
            total_pages: data.students.length > 0 ? 1 : 0,
            current_page: page,
          });
        } else {
          setStudentsData(data?.students || null);
        }
      } catch (e) {
        console.error('[App] dashboard fetch error:', e);
        setApiError(true);
      } finally {
        setDashLoading(false);
        setStudentsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [filters, page, schoolMetric]);

  useEffect(() => { setPage(1); }, [filters]);

  const hasNoData = () => !dashLoading && stats && stats.total === 0;

  const handleSchoolClick = schoolName =>
    setFilters(prev => ({ ...prev, truong: schoolName }));

  return (
    <div className="min-h-screen flex flex-col font-sans transition-colors duration-300 bg-slate-50 dark:bg-[#1b1c27] dashboard-shell">

      {/* ── Compact Header ── */}
      <Header filters={filters} />

      {/* ── Centered Filter Bar (sticky below header) ── */}
      <FilterBar filters={filters} filterOptions={filterOptions} onFilterChange={setFilters} />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 space-y-8">

        {apiError ? (
          <div className="flex flex-col items-center justify-center p-20 min-h-[50vh]">
            <div className="text-red-500 dark:text-[#f38ba8] text-lg font-bold tracking-wide">Lỗi kết nối API</div>
            <p className="text-slate-400 dark:text-[#a6adc8] text-sm mt-2">Kiểm tra lại server uvicorn ở cổng 8000.</p>
          </div>
        ) : hasNoData() ? (
          <div className="flex flex-col items-center justify-center p-20 min-h-[50vh]">
            <div className="text-[40px] mb-4 drop-shadow-lg">📭</div>
            <div className="text-slate-500 dark:text-[#a6adc8] text-lg font-medium tracking-wide">Không có dữ liệu phù hợp</div>
            <p className="text-slate-400 dark:text-[#585b70] text-sm mt-2">Vui lòng thay đổi Môn thi, Trường hoặc Giới tính</p>
          </div>
        ) : (
          <div className="space-y-8 animate-fade-in-up">

            {/* KPI Cards */}
            <section className="space-y-4">
              <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
                <div className="space-y-1">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500 dark:text-[#b9c0d5]">
                    Toàn cảnh
                  </p>
                  <h2 className="text-[26px] sm:text-[30px] font-display font-semibold tracking-tight text-slate-900 dark:text-[#eef1f7]">
                    Kết quả HSG 10
                  </h2>
                </div>
                <p className="max-w-2xl text-[13px] leading-6 text-slate-600 dark:text-[#c7cede]">
                  Nhìn nhanh thành tích, phổ điểm và nhóm trường nổi bật trong cùng một màn hình.
                </p>
              </div>
              <KPICards
                stats={stats}
                loading={dashLoading}
                filters={filters}
                scoreDist={scoreDist}
                topSchoolsData={topSchoolsData}
              />
            </section>

            {/* Charts */}
            <section className="grid grid-cols-1 xl:grid-cols-[1.15fr_0.85fr] gap-6">
              <ScoreDistribution data={scoreDist} loading={dashLoading} />
              <TopSchools
                data={topSchoolsData}
                loading={dashLoading}
                onMetricChange={setSchoolMetric}
                metric={schoolMetric}
                onSchoolClick={handleSchoolClick}
              />
            </section>

            {/* Data Table */}
            <section className="space-y-4">
              <div className="rounded-[26px] border border-[#d7e5f2]/60 dark:border-[#2c3044] bg-white/90 dark:bg-[#1c2031] shadow-[0_12px_28px_-24px_rgba(15,23,42,0.4),0_4px_12px_-6px_rgba(15,23,42,0.18)] backdrop-blur-md px-4 py-3">
                <GlobalSearch onSelectStudent={setSelectedStudent} variant="table" />
              </div>
              <div className="flex items-center justify-between px-2">
                <h3 className="text-[16px] font-display font-semibold tracking-tight text-slate-900 dark:text-[#eef1f7]">Danh sách thí sinh</h3>
              </div>
              <StudentTable
                data={studentsData}
                loading={studentsLoading}
                onPageChange={setPage}
                onRowClick={setSelectedStudent}
                isFullscreenMode={false}
                onToggleFullscreen={() => setIsTableFullscreen(true)}
              />
            </section>

          </div>
        )}
      </main>

      <Footer />

      {/* ── Fullscreen Data Grid Overlay ── */}
      {isTableFullscreen && (
        <div className="fixed inset-0 z-[9999] bg-slate-50 dark:bg-[#151620] text-slate-800 dark:text-[#d7dbe8] flex flex-col p-4 sm:p-6 overflow-hidden animate-fade-in-up">
          <div className="flex items-center gap-4 pb-4">
            <div className="text-[13px] sm:text-[14px] font-semibold text-slate-700 dark:text-[#d7dbe8] tracking-wide">
              Bảng điểm chi tiết
            </div>
            <div className="flex-1">
              <GlobalSearch
                onSelectStudent={s => { setSelectedStudent(s); setIsTableFullscreen(false); }}
                variant="fullscreen"
              />
            </div>
            <button
              onClick={() => setIsTableFullscreen(false)}
              title="Đóng (Esc)"
              className="w-9 h-9 flex items-center justify-center rounded-xl border border-slate-200/70 dark:border-[#2c3044] bg-white/90 dark:bg-[#1c2031] text-slate-500 dark:text-[#a9b0c6] hover:text-slate-700 dark:hover:text-[#eef1f7] hover:bg-slate-100 dark:hover:bg-[#2b3044] transition-colors"
            >
              <X size={16} />
            </button>
          </div>
          <div className="flex-1 min-h-0 bg-white dark:bg-[#1c2031] rounded-[28px] overflow-hidden border border-[#d7e5f2]/60 dark:border-[#2c3044] shadow-[0_14px_28px_-24px_rgba(15,23,42,0.45),0_4px_12px_-6px_rgba(15,23,42,0.18)]">
            <StudentTable
              data={studentsData}
              loading={studentsLoading}
              onPageChange={setPage}
              onRowClick={s => { setSelectedStudent(s); setIsTableFullscreen(false); }}
              isFullscreenMode={true}
              onToggleFullscreen={() => setIsTableFullscreen(false)}
            />
          </div>
        </div>
      )}

      {/* ── Centered Glassmorphism Profile Modal ── */}
      <CenteredProfileModal
        student={selectedStudent}
        onClose={() => setSelectedStudent(null)}
      />
    </div>
  );
}
