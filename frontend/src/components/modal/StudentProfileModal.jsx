import { useState, useEffect } from 'react';
import { X, Award, BarChart3, GraduationCap, MapPin, Hash } from 'lucide-react';
import { getSubjectAverage } from '../../api/client';
import { getPrizeBadgeClass } from '../../utils/helpers';

export default function StudentProfileModal({ student, onClose }) {
  const [subjectData, setSubjectData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!student) return;
    
    // Fetch average score for this subject
    const fetchAvg = async () => {
      setLoading(true);
      try {
        const data = await getSubjectAverage(student.mon_thi);
        setSubjectData(data);
      } catch (err) {
        console.error("Lỗi lấy điểm TB môn:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAvg();

    // Prevent background scrolling
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = 'unset'; };
  }, [student]);

  if (!student) return null;

  // Storytelling / Empathy Engine Logic
  const getEmpathyMessage = (prize) => {
    const isHighPrize = ['Nhất', 'Nhì', 'Ba'].includes(prize);
    const isKK = prize === 'Khuyến khích';

    if (isHighPrize) {
      const msgs = [
        "🎉 Thật tuyệt vời! Chúc mừng bạn đã gặt hái được quả ngọt sau bao ngày cố gắng! 🌟",
        "🏆 Thành tích xuất sắc quá! Tự hào về bạn! 👏",
        "🔥 Bạn đã nỗ lực hết mình và đây là phần thưởng hoàn toàn xứng đáng! Tiếp tục tỏa sáng nhé! ✨"
      ];
      return msgs[Math.floor(Math.random() * msgs.length)];
    } else if (isKK) {
      return "✨ Chúc mừng bạn đã đạt giải! Một chút nữa thôi là chạm tới đỉnh cao rồi, cố lên cho mục tiêu tiếp theo nhé! 🎯";
    } else {
      const msgs = [
        "💖 Đừng buồn nhé, kỳ thi này chỉ là một trạm dừng chân. Bạn đã làm rất tốt rồi! Điểm số không định nghĩa con người bạn! 💪",
        "🌱 Thất bại là mẹ thành công. Cứ tiếp tục nỗ lực, chặng đường phía trước còn dài! 🌈",
        "💪 Không sao cả! Quan trọng là bạn đã dám thử sức. Lấy đây làm động lực để bứt phá lần sau nhé! Đoạn đường còn dài! ✨"
      ];
      return msgs[Math.floor(Math.random() * msgs.length)];
    }
  };

  const scoreDiff = subjectData ? (parseFloat(student.diem) - parseFloat(subjectData.average)).toFixed(1) : 0;
  const isHigher = scoreDiff > 0;
  const isEqual = scoreDiff == 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative w-full max-w-lg bg-white dark:bg-[#1e1e2e] shadow-2xl rounded-2xl overflow-hidden animate-fade-in-up border border-slate-100 dark:border-[#313244]">
        
        {/* Header Ribbon based on prize */}
        <div className={`h-3 w-full ${student.xep_giai === 'Nhất' ? 'bg-yellow-400' : student.xep_giai === 'Nhì' ? 'bg-slate-300' : student.xep_giai === 'Ba' ? 'bg-orange-400' : student.xep_giai === 'Khuyến khích' ? 'bg-green-400' : 'bg-slate-200 dark:bg-[#45475a]'}`} />
        
        {/* Close Button */}
        <button 
          onClick={onClose} 
          className="absolute top-6 right-6 p-2 rounded-full bg-slate-50 hover:bg-slate-100 text-slate-400 hover:text-slate-600 dark:bg-[#313244] dark:text-[#a6adc8] dark:hover:text-[#cdd6f4] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-8">
          <div className="flex items-start gap-5">
            <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-[#89b4fa]/10 text-indigo-500 dark:text-[#89b4fa]">
               <GraduationCap className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-[22px] font-bold text-slate-800 dark:text-[#cdd6f4] leading-tight flex items-center gap-2">
                {student.ho_ten}
              </h2>
              <p className="text-[14px] font-medium text-slate-500 dark:text-[#bac2de] mt-1 flex items-center gap-1.5 flex-wrap">
                <Hash className="w-3.5 h-3.5" /> SBD: {student.sbd} <span className="mx-1 text-slate-300 dark:text-[#45475a]">•</span>
                <MapPin className="w-3.5 h-3.5 ml-1" /> {student.truong}
              </p>
            </div>
          </div>

          <div className="mt-8 grid grid-cols-2 gap-4">
             <div className="bg-slate-50 dark:bg-[#181825] border border-slate-100 dark:border-[#313244] rounded-2xl p-5 relative overflow-hidden">
                <div className="text-[12px] font-semibold text-slate-400 dark:text-[#a6adc8] uppercase tracking-wider mb-2">Điểm Thi</div>
                <div className="text-[34px] font-black text-indigo-500 dark:text-[#89b4fa] tabular-nums leading-none tracking-tight">
                  {student.diem}
                </div>
             </div>
             <div className="bg-slate-50 dark:bg-[#181825] border border-slate-100 dark:border-[#313244] rounded-2xl p-5 flex flex-col justify-center items-start relative overflow-hidden">
                <div className="text-[12px] font-semibold text-slate-400 dark:text-[#a6adc8] uppercase tracking-wider mb-3">Xếp Giải</div>
                <span className={`${getPrizeBadgeClass(student.xep_giai)} text-[13px] px-3 py-1`}>
                  {student.xep_giai === "Không có" ? "Chưa đạt giải" : student.xep_giai}
                </span>
             </div>
          </div>

          <div className="mt-4 bg-slate-50 dark:bg-[#181825] border border-slate-100 dark:border-[#313244] rounded-2xl p-5">
             <div className="flex items-center gap-2 mb-2 text-slate-700 dark:text-[#cdd6f4] font-semibold text-[14px]">
               <BarChart3 className="w-4 h-4 text-indigo-400" />
               Phân tích chuyên sâu ({student.mon_thi})
             </div>
             {loading ? (
                <div className="text-[13px] text-slate-400 dark:text-[#a6adc8] animate-pulse">Đang tính toán phổ điểm môn thi...</div>
             ) : subjectData ? (
                <p className="text-[13.5px] text-slate-600 dark:text-[#bac2de] leading-relaxed">
                  Điểm của bạn là <span className="font-bold text-slate-800 dark:text-[#cdd6f4]">{student.diem}</span>, 
                  {isHigher ? (
                    <> cao hơn điểm trung bình chung toàn Tỉnh môn <span className="font-semibold">{student.mon_thi}</span> ({subjectData.average}) khoảng <span className="font-bold text-green-500 dark:text-[#a6e3a1]">+{scoreDiff}</span> điểm.</>
                  ) : isEqual ? (
                    <> bằng chính xác với điểm trung bình chung toàn Tỉnh môn <span className="font-semibold">{student.mon_thi}</span> ({subjectData.average}).</>
                  ) : (
                    <> thấp hơn điểm trung bình chung toàn Tỉnh môn <span className="font-semibold">{student.mon_thi}</span> ({subjectData.average}) khoảng <span className="font-bold text-red-500 dark:text-[#f38ba8]">{scoreDiff}</span> điểm.</>
                  )}
                </p>
             ) : (
                <p className="text-[13px] text-slate-400">Không có dữ liệu trung bình.</p>
             )}
          </div>

          <div className="mt-6 border-t border-slate-100 dark:border-[#313244] pt-6 flex gap-3 items-start">
             <div className="mt-1 w-8 h-8 flex-shrink-0 flex items-center justify-center rounded-full bg-slate-100 dark:bg-[#313244] text-[15px]">
               💌
             </div>
             <div>
                <p className="text-[14px] font-medium text-slate-700 dark:text-[#bac2de] leading-relaxed">
                  {getEmpathyMessage(student.xep_giai)}
                </p>
             </div>
          </div>

        </div>
      </div>
    </div>
  );
}
