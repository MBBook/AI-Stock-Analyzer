// ✅ 2026-07-08: แยกออกจาก App.jsx (เดิมรวมอยู่บรรทัด 1-133) — เป็นค่าคงที่ล้วนๆ ระดับ module
// ไม่แตะ state/hook ของ DashboardV4 เลย ย้ายมาที่นี่เพื่อลดขนาด App.jsx โดยไม่กระทบการทำงาน
// (import กลับเข้า App.jsx ตามเดิมทุกตัว ไม่มีการเปลี่ยนค่าใดๆ)

export const API_URL = 'https://ai-stock-analyzer-msli.onrender.com';

export const COLORS = {
  bgGradient: 'linear-gradient(160deg, #0B1130 0%, #050714 100%)',
  cardBg: 'rgba(148,163,184,0.08)',
  cardBgHover: 'rgba(148,163,184,0.13)',
  cardBorder: 'rgba(148,163,184,0.14)',
  text: '#E7ECF5',
  muted: '#94A3B8',
  faint: '#5B6478',
  purple: '#A855F7',
  purpleSoft: 'rgba(168,85,247,0.16)',
  gold: '#F5C46B',
  goldDark: '#EF9F27',
  goldLight: '#F7CE85',
  green: '#97C459',
  greenSoft: 'rgba(151,196,89,0.16)',
  red: '#E24B4A',
  redSoft: 'rgba(226,75,74,0.16)',
};

export const SP = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const MAX_TICKERS = 30;

// ⚠️ MOCK DATA — News tab backend (task #51 ใน Pending.md) ยังไม่ได้สร้าง (ยังไม่มี NewsArticle
// table/endpoint จริง) ข้อมูลด้านล่างนี้ใช้แค่โชว์ดีไซน์/pagination ให้ครบตาม mockup เท่านั้น
// ห้ามอ้างว่าเป็นข่าวจริง — ต่อ API จริงทันทีที่ backend #51 เสร็จ (แทนที่ MOCK_NEWS ทั้งก้อนนี้)
const MOCK_NEWS_TEMPLATES = [
  { tickers: ['NVDA', 'IONQ'], headline: 'NVIDIA ประกาศความร่วมมือด้านควอนตัมคอมพิวติ้งกับพันธมิตรรายใหม่', sentiment: 'Positive', impact: 'สูง', source: 'Bloomberg', body: 'ข่าวสัญญาควอนตัมคอมพิวติ้งกับ NVIDIA หนุนราคาระยะสั้น โมเมนตัมยังเป็นขาขึ้นจากปริมาณซื้อขาย นักวิเคราะห์มองเป็นบวกต่อ supply chain ทั้งกลุ่ม' },
  { tickers: ['MU'], headline: 'Micron เผชิญแรงกดดันราคาชิปหน่วยความจำจากคู่แข่งจีน', sentiment: 'Negative', impact: 'ปานกลาง', source: 'Bloomberg', body: 'ผู้ผลิตชิปจีนหลายรายเพิ่มกำลังการผลิต NAND flash อย่างรวดเร็ว ส่งผลให้ราคาตลาดโลกมีแนวโน้มปรับตัวลงในไตรมาสหน้า แต่นักวิเคราะห์บางส่วนมองว่ามาจาก data center AI จะช่วยพยุงราคาส่วนหนึ่ง' },
  { tickers: ['WDC'], headline: 'Western Digital รายงานผลประกอบการดีกว่าคาดจาก demand data center', sentiment: 'Positive', impact: 'ปานกลาง', source: 'CNBC', body: 'รายได้จากกลุ่ม enterprise storage เติบโตต่อเนื่อง หนุนจาก investment ด้าน AI infrastructure ของ hyperscaler รายใหญ่ ราคาหุ้นตอบรับเชิงบวกหลังประกาศงบ' },
  { tickers: ['NBIS'], headline: 'Nebius ขยายกำลังการผลิต GPU cloud รองรับดีมานด์ AI training', sentiment: 'Neutral', impact: 'ต่ำ', source: 'Yahoo Finance', body: 'บริษัทประกาศแผนลงทุนเพิ่มศูนย์ข้อมูลใหม่ในยุโรป นักวิเคราะห์มองเป็นกลางเนื่องจากต้องรอดูอัตราการใช้งานจริงก่อนประเมินผลตอบแทน' },
];
// ✅ แก้ 2026-07-05 (รอบ 8): MBBook ทักท้วงว่าวันที่โดดไปมา — เดิม date คำนวณจาก `(i % 7) + 1` วนซ้ำ
// ไม่เกี่ยวกับลำดับ index เลย แล้ว list ก็ไม่เคย sort ตามวันที่เลย เลยดูสุ่ม แก้โดยให้แต่ละข่าวมี
// timestamp จริง (ms) ไล่ย้อนหลังจาก "ตอนนี้" ทุกๆ 7 ชม. (id ยิ่งมาก ยิ่งเก่า) แล้วให้ NewsList
// sort ตาม timestamp ใหม่→เก่าเสมอ (ไม่พึ่งลำดับ array ตรงๆ กันพลาดถ้ามีข่าวแทรกเข้ามาไม่เรียงในอนาคต)
export const MOCK_NEWS = Array.from({ length: 24 }, (_, i) => {
  const t = MOCK_NEWS_TEMPLATES[i % MOCK_NEWS_TEMPLATES.length];
  const ts = new Date(Date.now() - i * 7 * 60 * 60 * 1000);
  return {
    id: i + 1, ...t, timestamp: ts.getTime(),
    date: `${ts.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })} · ${ts.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}`,
  };
});

// ⚠️ ชื่อเต็มบริษัท — backend ยังไม่มี field นี้ (ดู Pending.md gap) ใส่ไว้เป็น fallback ฝั่ง client
// เฉพาะบริษัทที่รู้จริง (ข้อมูลสาธารณะทั่วไป ไม่ใช่การเดา) — ticker ที่ไม่อยู่ใน dict นี้จะโชว์แค่ ticker
// เฉยๆ ไม่ fabricate ชื่อขึ้นมา ต่อ field จริงจาก backend ทีหลังแล้วลบ dict นี้ทิ้งได้เลย
export const COMPANY_NAMES = {
  NVDA: 'NVIDIA Corporation', IONQ: 'IonQ, Inc.', MU: 'Micron Technology, Inc.',
  WDC: 'Western Digital Corporation', NBIS: 'Nebius Group N.V.', META: 'Meta Platforms, Inc.',
  AAPL: 'Apple Inc.', MSFT: 'Microsoft Corporation', GOOGL: 'Alphabet Inc.', AMZN: 'Amazon.com, Inc.',
  TSLA: 'Tesla, Inc.', AMD: 'Advanced Micro Devices, Inc.', ORCL: 'Oracle Corporation',
};

export const GLOBAL_CSS = `
  * { box-sizing: border-box; }
  button { font-family: inherit; }
  .clay-btn {
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 4px 4px 9px rgba(0,0,0,0.45), -3px -3px 7px rgba(255,224,168,0.25), inset 1px 1px 2px rgba(255,255,255,0.35);
  }
  .clay-btn:hover { transform: scale(1.06); box-shadow: 6px 6px 14px rgba(0,0,0,0.5), -4px -4px 10px rgba(255,224,168,0.3), inset 1px 1px 2px rgba(255,255,255,0.4); }
  .clay-btn:active { transform: scale(0.92); box-shadow: 2px 2px 5px rgba(0,0,0,0.5), -1px -1px 3px rgba(255,224,168,0.2), inset 2px 2px 4px rgba(0,0,0,0.3); }
  .press-btn { transition: transform 0.12s ease; }
  .press-btn:active { transform: scale(0.94); }
  .nav-btn { transition: transform 0.15s ease, background-color 0.15s ease; }
  .nav-btn:hover:not(.nav-btn-active) { transform: translateY(-2px); background-color: rgba(168,85,247,0.12); }
  .glass-row { transition: transform 0.15s ease, background-color 0.15s ease; cursor: pointer; }
  .glass-row:hover { transform: translateY(-1px); background-color: ${COLORS.cardBgHover}; }
  .glass-row:active { transform: scale(0.98); }
  .icon-btn { transition: transform 0.15s ease, background-color 0.15s ease; }
  .icon-btn:hover { background-color: rgba(168,85,247,0.14); }
  .icon-btn:active { transform: scale(0.9); }
  .modal-backdrop { transition: opacity 0.28s ease; }
  .pill-btn { transition: transform 0.12s ease; }
  .pill-btn:active { transform: scale(0.92); }
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.25); border-radius: 8px; }

  @keyframes pulseBadge {
    0% { transform: scale(1); }
    40% { transform: scale(1.18); }
    100% { transform: scale(1); }
  }
  .signal-pulse { animation: pulseBadge 0.45s ease; display: inline-block; }

  @keyframes barGrow {
    from { transform: scaleY(0); }
    to { transform: scaleY(1); }
  }
  .chart-bar { transform-origin: bottom; animation: barGrow 0.45s cubic-bezier(.34,1.2,.64,1); transition: height 0.3s ease; }

  @keyframes lineDraw {
    from { stroke-dashoffset: 2000; }
    to { stroke-dashoffset: 0; }
  }
  .line-draw { stroke-dasharray: 2000; animation: lineDraw 1.1s ease forwards; }

  @keyframes toastUp {
    from { transform: translate(-50%, 20px); opacity: 0; }
    to { transform: translate(-50%, 0); opacity: 1; }
  }
  @keyframes toastDown {
    from { transform: translate(-50%, 0); opacity: 1; }
    to { transform: translate(-50%, 20px); opacity: 0; }
  }
  .toast-in { animation: toastUp 0.28s cubic-bezier(.34,1.4,.64,1) forwards; }
  .toast-out { animation: toastDown 0.22s ease forwards; }
`;
