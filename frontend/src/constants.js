// ✅ 2026-07-08: แยกออกจาก App.jsx (เดิมรวมอยู่บรรทัด 1-133) — เป็นค่าคงที่ล้วนๆ ระดับ module
// ไม่แตะ state/hook ของ DashboardV4 เลย ย้ายมาที่นี่เพื่อลดขนาด App.jsx โดยไม่กระทบการทำงาน
// (import กลับเข้า App.jsx ตามเดิมทุกตัว ไม่มีการเปลี่ยนค่าใดๆ)

export const API_URL = 'https://ai-stock-analyzer-msli.onrender.com';

// ✅ เพิ่ม 2026-07-09: fetch ที่แนบ X-Auth-Token อัตโนมัติ (ระบบ password ของ dashboard)
// token ได้จาก POST /auth/login เก็บใน localStorage — ฝั่ง backend ถ้าไม่ตั้ง DASHBOARD_PASSWORD
// ใน env = auth ปิดอยู่ (header ส่วนเกินนี้ไม่มีผลอะไร ใช้ local dev ได้ปกติ)
export const AUTH_TOKEN_KEY = 'dash_auth_token';
export const authFetch = (url, opts = {}) => fetch(url, {
  ...opts,
  headers: { ...(opts.headers || {}), 'X-Auth-Token': localStorage.getItem(AUTH_TOKEN_KEY) || '' },
});

// ✅ 2026-07-09: Reskin Phase 1 — เปลี่ยน design tokens ทั้งชุดให้ตรง UI_Preview_v1.html
// (mockup ที่ MBBook confirm) — เดิมพอร์ตแค่ layout เมื่อ 07-08 แต่สี/กระจก/ฟอนต์ยังเป็นธีมเก่า
// ค่าทุกตัว copy ตรงจาก :root ของ mockup — แก้ที่นี่ที่เดียว ไหลไปทุก component ที่ import COLORS
export const COLORS = {
  bgGradient: `radial-gradient(ellipse 900px 500px at 10% -10%, rgba(139,123,247,0.14), transparent 60%),
      radial-gradient(ellipse 700px 500px at 100% 0%, rgba(79,195,255,0.08), transparent 55%),
      #0a0e17`,
  cardBg: 'rgba(255,255,255,0.045)',        // --glass
  cardBgHover: 'rgba(255,255,255,0.075)',   // --glass-strong
  cardBorder: 'rgba(255,255,255,0.09)',     // --border
  cardBorderStrong: 'rgba(255,255,255,0.18)', // --border-strong
  text: '#f2f4fa',
  muted: 'rgba(242,244,250,0.62)',          // --text-2
  faint: 'rgba(242,244,250,0.38)',          // --text-3
  purple: '#8b7bf7',
  purple2: '#6a5cf0',                        // ปลาย gradient ม่วง
  purpleSoft: 'rgba(139,123,247,0.18)',
  purpleGradient: 'linear-gradient(135deg, #8b7bf7, #6a5cf0)',
  blue: '#4fc3ff',
  gold: '#f7ce85',
  goldDark: '#ef9f27',
  goldLight: '#f7ce85',
  goldGradient: 'linear-gradient(135deg, #f7ce85, #ef9f27)',
  green: '#33d692',
  greenSoft: 'rgba(51,214,146,0.16)',
  red: '#ff6570',
  redSoft: 'rgba(255,101,112,0.16)',
};

export const SP = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const MAX_TICKERS = 30;

// ✅ 2026-07-11: ลบ MOCK_NEWS ทิ้งทั้งก้อนแล้ว — backend #51 เสร็จ (GET /news อ่านข่าวจริงจาก
// news_cache ที่นัตตี้ prefetch รายชั่วโมง) MBBook เจอเองว่าหน้า News โชว์ข่าวปลอม 4 ข่าววนซ้ำ
// ทุกวันทั้งที่ข่าวจริงอยู่ใน DB ครบ — ห้ามเอา mock กลับมาใส่อีก ถ้าไม่มีข่าวให้โชว์ข้อความสถานะจริง

// ✅ 2026-07-11 Reskin Phase 2 ข้อ 5: สีประจำหุ้น — palette + hash function ตรงจาก mockup
// (AVATAR_COLORS/avatarColor ใน UI_Preview_v1.html) ticker เดิมได้สีเดิมเสมอ
export const AVATAR_COLORS = ['#8b7bf7', '#4fc3ff', '#ef9f27', '#33d692', '#ff6570', '#c084fc', '#38bdf8'];
export const avatarColor = (t) => {
  let h = 0;
  for (let i = 0; i < t.length; i++) h += t.charCodeAt(i);
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
};

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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+Thai:wght@400;600;700;800&display=swap');
  * { box-sizing: border-box; }
  body { font-family: 'Inter','Noto Sans Thai',-apple-system,BlinkMacSystemFont,sans-serif; -webkit-font-smoothing: antialiased; }
  .num { font-variant-numeric: tabular-nums; }
  button { font-family: inherit; }
  /* ✅ 2026-07-09 Reskin Phase 2 ข้อ 3: เงาชุด .gold-btn จาก mockup แทน claymorphism เดิม
     (เงาทองฟุ้งข้างล่าง + ไฮไลต์ขาวขอบบน + เงาเข้มขอบล่างด้านใน) hover แค่ scale ไม่เปลี่ยนเงา */
  .clay-btn {
    transition: transform 0.15s cubic-bezier(.34,1.56,.64,1);
    box-shadow: 0 10px 22px -9px rgba(239,159,39,0.6), inset 0 1px 0 rgba(255,255,255,0.55), inset 0 -3px 5px rgba(140,74,3,0.35);
  }
  .clay-btn:hover { transform: scale(1.06); }
  .clay-btn:active { transform: scale(0.92); }
  .press-btn { transition: transform 0.12s ease; }
  .press-btn:active { transform: scale(0.94); }
  .nav-btn { transition: transform 0.15s ease, background-color 0.15s ease; }
  .nav-btn:hover:not(.nav-btn-active) { transform: translateY(-2px); background-color: rgba(139,123,247,0.12); }
  .glass-row { transition: transform 0.15s ease, background-color 0.15s ease, opacity 0.2s ease; cursor: pointer; }
  .glass-row:hover { transform: translateY(-1px); background-color: ${COLORS.cardBgHover}; }
  .glass-row:active { transform: scale(0.98); }
  /* ✅ 2026-07-11 Reskin Phase 2 ข้อ 7: แถวตาราง dtable ตาม mockup — hover 0.05 ไม่ลอยขึ้น
     (!important เพื่อชนะ zebra ที่เป็น inline style บนแถว) */
  .trow { transition: background-color 0.15s ease; cursor: pointer; }
  .trow:hover { background-color: rgba(255,255,255,0.05) !important; }
  .trow:active { transform: scale(0.995); }
  .icon-btn { transition: transform 0.15s ease, background-color 0.15s ease; }
  .icon-btn:hover { background-color: rgba(139,123,247,0.14); }
  .icon-btn:active { transform: scale(0.9); }
  .modal-backdrop { transition: opacity 0.28s ease; }
  .pill-btn { transition: transform 0.12s ease; }
  .pill-btn:active { transform: scale(0.92); }
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.25); border-radius: 8px; }

  /* ✅ 2026-07-11: skeleton loading — copy ตรงจาก mockup .skeleton/@shimmer (UX baseline ใน
     Redesign Prompt v2/v3: ห้ามจอว่าง/spinner เปล่าตอนโหลด) */
  .skeleton {
    background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 37%, rgba(255,255,255,0.04) 63%);
    background-size: 400% 100%;
    animation: shimmer 1.4s ease infinite;
    border-radius: 12px;
  }
  @keyframes shimmer {
    0% { background-position: 100% 0; }
    100% { background-position: 0 0; }
  }

  /* ✅ 2026-07-11 Reskin Phase 2 ข้อ 9: จุดทอง "New" ที่ footer การ์ดข่าว — pulse 2 ครั้งตอน
     mount แล้วหยุดนิ่ง (mockup .newdot.pulseonce — ห้ามกะพริบต่อเนื่อง ตามที่ confirm 07-07) */
  @keyframes pulseonce {
    0% { box-shadow: 0 0 0 0 rgba(239,159,39,0.55); }
    70% { box-shadow: 0 0 0 7px rgba(239,159,39,0); }
    100% { box-shadow: 0 0 0 0 rgba(239,159,39,0); }
  }
  .newdot-pulse { animation: pulseonce 1.1s ease-out 2; }

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
