import { useState, useEffect } from 'react';
import { X, GraduationCap, MapPin, Hash, Trophy } from 'lucide-react';
import { getPrizeBadgeClass } from '../../utils/helpers';

export default function CenteredProfileModal({ student, onClose }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!student) { setIsVisible(false); return; }
    setTimeout(() => setIsVisible(true), 10);
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = 'unset'; };
  }, [student]);

  if (!student) return null;

  const getEmpathyMessage = (prize) => {
    const high = ['Nhất', 'Nhì', 'Ba'].includes(prize);
    if (high) {
      return [
        '🎉 Chúc mừng bạn đã gặt hái được quả ngọt sau bao ngày cố gắng! 🌟',
        '🏆 Thành tích xuất sắc quá! Tự hào về bạn! 👏',
        '🔥 Bạn đã nỗ lực hết mình và đây là phần thưởng hoàn toàn xứng đáng! ✨',
      ][Math.floor(Math.random() * 3)];
    }
    if (prize === 'Khuyến khích')
      return '✨ Chúc mừng bạn đã đạt giải! Một chút nữa thôi là chạm tới đỉnh cao rồi! 🎯';
    return [
      '💖 Đừng buồn nhé, kỳ thi này chỉ là một trạm dừng chân. Bạn đã làm rất tốt rồi! 💪',
      '🌱 Thất bại là mẹ thành công. Cứ tiếp tục nỗ lực, chặng đường phía trước còn dài! 🌈',
      '💪 Không sao cả! Lấy đây làm động lực để bứt phá lần sau nhé! ✨',
    ][Math.floor(Math.random() * 3)];
  };

  const percentileStr = student.percentile ? (student.percentile * 100).toFixed(1) : '0.0';

  return (
    <>
      {/* Backdrop with glassmorphism */}
      <div
        className={`fixed inset-0 bg-slate-900/40 dark:bg-black/60 backdrop-blur-md z-[60] flex items-center justify-center p-4 sm:p-6 transition-opacity duration-300 ${isVisible ? 'opacity-100' : 'opacity-0'}`}
        onClick={() => { setIsVisible(false); setTimeout(onClose, 300); }}
      >
        {/* Modal Card */}
        <div
          className={`bg-white dark:bg-[#1c2031] rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden shrink-0 transform transition-all duration-300 ${isVisible ? 'scale-100 opacity-100' : 'scale-95 opacity-0'}`}
          onClick={e => e.stopPropagation()}
        >
          {/* Color Ribbon */}
          <div className={`h-2.5 w-full shrink-0 ${
            student.xep_giai === 'Nhất'         ? 'bg-amber-300' :
            student.xep_giai === 'Nhì'          ? 'bg-slate-300' :
            student.xep_giai === 'Ba'           ? 'bg-orange-300' :
            student.xep_giai === 'Khuyến khích' ? 'bg-emerald-300' :
                                                  'bg-slate-200 dark:bg-[#2c3044]'
          }`} />

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-[#2c3044]">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400 dark:text-[#a9b0c6]">
              Hồ sơ thí sinh
            </h2>
            <button
              onClick={() => { setIsVisible(false); setTimeout(onClose, 300); }}
              className="p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-[#2b3044] text-slate-400 hover:text-slate-600 dark:text-[#a9b0c6] dark:hover:text-[#eef1f7] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 sm:p-8">
            {/* Identity */}
            <div className="flex items-start gap-4 sm:gap-5">
              <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-slate-100 dark:bg-[#151826] text-slate-500 dark:text-[#9bb9dd] shrink-0 shadow-inner float-animation">
                <GraduationCap className="w-7 h-7" />
              </div>
              <div className="mt-1">
                <h1 className="text-xl sm:text-2xl font-display font-semibold text-slate-900 dark:text-[#eef1f7] leading-tight">
                  {student.ho_ten}
                </h1>
                <div className="text-[13px] font-medium text-slate-500 dark:text-[#b9c0d5] mt-2 space-y-1.5">
                  <div className="flex items-center gap-2"><Hash className="w-3.5 h-3.5 shrink-0" /><span>SBD: {student.sbd}</span></div>
                  <div className="flex items-center gap-2"><MapPin className="w-3.5 h-3.5 shrink-0" /><span className="truncate">{student.truong}</span></div>
                </div>
              </div>
            </div>

            {/* Score + Prize */}
            <div className="mt-8 grid grid-cols-2 gap-4">
              <div className="bg-slate-50 dark:bg-[#151826] border border-slate-100/80 dark:border-[#2c3044] rounded-2xl p-5">
                <div className="text-[11px] font-semibold text-slate-400 dark:text-[#a9b0c6] uppercase tracking-[0.24em] mb-2">Điểm Thi</div>
                <div className="text-[36px] font-black text-[#2e6fa2] dark:text-[#9bb9dd] tabular-nums leading-none">
                  {student.diem}
                </div>
              </div>
              <div className="bg-slate-50 dark:bg-[#151826] border border-slate-100/80 dark:border-[#2c3044] rounded-2xl p-5 flex flex-col justify-center">
                <div className="text-[11px] font-semibold text-slate-400 dark:text-[#a9b0c6] uppercase tracking-[0.24em] mb-3">Thành tích</div>
                <span className={`${getPrizeBadgeClass(student.xep_giai)} self-start`}>
                  {student.xep_giai === 'Không có' ? 'Chưa đạt giải' : `Giải ${student.xep_giai}`}
                </span>
              </div>
            </div>

            {/* Percentile Block */}
            <div className="mt-4 bg-gradient-to-br from-slate-50 to-white dark:from-[#151826] dark:to-[#151826] border border-slate-100/80 dark:border-[#2c3044] rounded-2xl p-5">
              <div className="flex items-center gap-2 text-slate-700 dark:text-[#eef1f7] font-semibold text-[14px]">
                <Trophy className="w-4 h-4 text-amber-400 dark:text-[#f2b47c]" />
                Độ khó Môn {student.mon_thi}
              </div>
              <div className="mt-4 flex max-sm:flex-col justify-between items-end gap-2">
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-[#a9b0c6] font-semibold uppercase tracking-[0.24em]">Xếp hạng Điểm Tỉnh</p>
                  <div className="text-[20px] font-black tabular-nums text-slate-900 dark:text-[#eef1f7] mt-1">
                    {student.rank} <span className="text-slate-400 dark:text-[#a6adc8] text-[15px]">/ {student.total_in_subject}</span>
                  </div>
                </div>
                <div className="text-right bg-white/70 dark:bg-[#1c2031] px-3 py-1.5 rounded-lg border border-white/50 dark:border-[#2c3044]">
                  <div className="text-[10px] uppercase tracking-[0.24em] font-semibold text-slate-400 dark:text-[#a9b0c6] mb-0.5">Top Tỉnh</div>
                  <div className="text-[18px] font-black text-amber-500 dark:text-[#f2b47c] tabular-nums leading-none">
                    Top {percentileStr}%
                  </div>
                </div>
              </div>
            </div>

            {/* Empathy Engine */}
            <div className="mt-8 border-t border-slate-100/80 dark:border-[#2c3044] pt-6 flex gap-3.5 items-start">
              <div className="mt-1 w-10 h-10 flex-shrink-0 flex items-center justify-center rounded-2xl bg-slate-50 dark:bg-[#151826] border border-slate-100/80 dark:border-[#2c3044] text-[18px] shadow-sm">
                💌
              </div>
              <div>
                <div className="text-[10px] font-semibold text-slate-400 dark:text-[#6c7086] uppercase tracking-[0.24em] mb-1">AI Lời Nhắn</div>
                <p className="text-[14px] font-medium text-slate-700 dark:text-[#b9c0d5] leading-relaxed italic pr-2">
                  "{getEmpathyMessage(student.xep_giai)}"
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
