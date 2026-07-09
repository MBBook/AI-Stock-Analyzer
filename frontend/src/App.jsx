import React, { useState, useEffect, useRef } from 'react';
import {
  Briefcase, TrendingUp, Settings, Newspaper,
  Plus, Trash2, Upload, Search, Check, Camera, Info, X,
  ChevronDown, ChevronLeft, ChevronRight, Filter, ArrowUpDown, Eye, EyeOff,
} from 'lucide-react';
// ✅ 2026-07-08: ย้ายค่าคงที่ (COLORS/SP/MOCK_NEWS/COMPANY_NAMES/GLOBAL_CSS/API_URL) ไป constants.js
// แยกแล้ว (ลดขนาดไฟล์นี้ — ไม่กระทบ logic ใดๆ ค่าเดิมทุกตัว แค่ import แทนการประกาศตรงนี้)
import { API_URL, COLORS, SP, MAX_TICKERS, MOCK_NEWS, COMPANY_NAMES, GLOBAL_CSS, authFetch, AUTH_TOKEN_KEY } from './constants';

// ✅ REBUILD 2026-07-05 (รอบ 2): เขียนใหม่ทั้งไฟล์ตาม 3_CowContext/UI_Spec.md ที่ MBBook confirm
// ทีละจุดผ่านรูปจริง (ไม่ใช่แค่สรุปจากความจำแล้ว) — รอบแรกที่ทำไปพลาดหลายจุด (ไม่มีกราฟ, THB
// เป็น toggle แทนที่จะโชว์คู่กัน, +Trade ลอยบัง, ปุ่ม/หัวข้อไม่ตรง) ดู UI_Spec.md ก่อนแก้ไฟล์นี้เสมอ
//
// กติกาเดิมที่ต้องรักษาไว้ (เจอบั๊กมาแล้ว): ห้ามเรียก helper "component" เป็น JSX tag
// (เช่น <Foo/>) เพราะ function ถูกสร้างใหม่ทุก re-render ของ DashboardV4 → React มองเป็นคนละ
// component type ทุกครั้ง → unmount/remount ทั้ง subtree (input เสีย focus ตอนพิมพ์) ให้เรียกเป็น
// function ตรงๆ เท่านั้น เช่น Foo() ไม่ใช่ <Foo/> — เพราะเหตุผลเดียวกัน ห้ามเรียก useState/useEffect
// (React hooks) จากภายใน helper function พวกนี้แบบมีเงื่อนไข (conditional) เด็ดขาด เนื่องจากมันไม่ใช่
// component จริง แค่ function ที่ถูกเรียกกลางฟังก์ชัน render ของ DashboardV4 เอง — ถ้ามีเงื่อนไขว่าจะ
// เรียกหรือไม่เรียก (เช่น สลับ tab) แล้วข้างในมี hook จะกลายเป็น "conditional hook call" ทันที (ผิดกฎ
// Rules of Hooks) ด้วยเหตุนี้ animation "count-up ตัวเลข" (ที่คุยไว้ใน mockup) จึงถูกงดไว้ก่อนในรอบนี้
// (ต้องทำที่ state ระดับบนสุดของ DashboardV4 เท่านั้นถึงจะปลอดภัย) — pulse บน badge ใช้วิธี
// key-remount + CSS keyframe แทน (ไม่ต้องใช้ hook เลยเลี่ยงปัญหานี้ได้)

export default function DashboardV4() {
  // ✅ เพิ่ม 2026-07-09: ระบบ password — token อยู่ localStorage, ไม่มี token = เห็นแค่หน้า login
  // (state ทั้ง 3 ตัวอยู่ top-level เสมอตามกฎ Rules of Hooks — ห้ามย้ายเข้า helper)
  const [authToken, setAuthToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY) || '');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginState, setLoginState] = useState({ busy: false, error: null });
  const [activeTab, setActiveTab] = useState('portfolio');
  const [stocks, setStocks] = useState([]);
  const [newTicker, setNewTicker] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [tradeTicker, setTradeTicker] = useState('');
  const [tradeAction, setTradeAction] = useState('BUY');
  const [tradeShares, setTradeShares] = useState('');
  const [tradePrice, setTradePrice] = useState('');
  const [tradeSubmitting, setTradeSubmitting] = useState(false);
  const [tradeMessage, setTradeMessage] = useState(null);
  const [tradeImageFile, setTradeImageFile] = useState(null);
  const [tradeImagePreview, setTradeImagePreview] = useState(null);
  const [tradeParsing, setTradeParsing] = useState(false);
  const [tradeParseMessage, setTradeParseMessage] = useState(null);
  const [addingTicker, setAddingTicker] = useState(false);
  const [portfolioData, setPortfolioData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [portfolioHistory, setPortfolioHistory] = useState(null);
  const [nikSuggestions, setNikSuggestions] = useState(null);
  // ✅ 2026-07-09: ตัด costSummary/reportList/loading ฝั่งอ่านออก (ESLint no-unused-vars ทำ
  // Vercel build fail) — setter ยังถูกเรียกใน fetch อยู่ = ดึงข้อมูลมาแล้วไม่ได้แสดง เป็นเศษจาก
  // รอบรื้อ UI 07-08 — จดใน Pending แล้ว (พิจารณาลบ fetch ทิ้งหรือเอาข้อมูลกลับมาโชว์)
  const [, setCostSummary] = useState(null);
  const [, setReportList] = useState(null);
  const [roiSummary, setRoiSummary] = useState(null);

  // Portfolio chart controls
  // ✅ แก้ 2026-07-08: ตัด 'daily' ออก (% รายวัน noise เกินไป เทียบเป้า 13%/เดือน, 15%/ปี ไม่ได้จริง
  // ตามที่ MBBook สรุป) เปลี่ยนเป็น monthly/yearly/cumulative — ทั้งสามปุ่มใช้ return_pct ตัวเดียวกัน
  // (ROI สะสม ณ จุดนั้นจริง จาก agents.py::portfolio_return_history) แค่ downsample ความถี่ต่างกัน
  // ตามที่ MBBook ยืนยัน (เป้าคือเช็คว่าปิดเดือน/ปีนั้นๆ ROI สะสมถึงเป้าหรือยัง ไม่ใช่กำไรเฉพาะเดือนนั้น)
  // ตัด date-range dropdown ของ Portfolio ออกด้วย เพราะ Monthly/Yearly มีช่วงตายตัว (6 เดือนล่าสุด /
  // ทุกปีที่มีข้อมูล) ไม่ต้องเลือกช่วงเองแล้ว
  const [periodMode, setPeriodMode] = useState('monthly'); // 'monthly' | 'yearly' | 'cumulative'

  // ✅ เพิ่ม 2026-07-05 (รอบ 5, Finding 2): period/date-range แยกชุดสำหรับกราฟต้นทุนใน System tab
  // (คนละ state กับกราฟ Portfolio เพื่อไม่ให้ผูกกันโดยไม่ตั้งใจ)
  const [costPeriodMode, setCostPeriodMode] = useState('daily');
  const [costDateRangeMode, setCostDateRangeMode] = useState('7d');
  const [costCustomStart, setCostCustomStart] = useState('');
  const [costCustomEnd, setCostCustomEnd] = useState('');
  const [costDateDropdownOpen, setCostDateDropdownOpen] = useState(false);

  // News pagination
  const [newsPage, setNewsPage] = useState(1);
  const NEWS_PAGE_SIZE = 10;

  // ✅ เพิ่ม 2026-07-05 (รอบ 10): MBBook ขอลองจำลองข่าวใหม่เข้ามาเพื่อทดสอบป้าย "New" + ปุ่ม
  // "อ่านทั้งหมด" — เก็บใน state แยกจาก MOCK_NEWS (ค่าคงที่ ไม่แก้โดยตรง) แล้วรวมกันตอนแสดงผล
  // ลบทิ้งได้เลยทั้งก้อนตอนต่อ backend ข่าวจริง (#51) พร้อมกับ MOCK_NEWS
  const [extraNews, setExtraNews] = useState([]);

  // ✅ เพิ่ม 2026-07-05 (รอบ 8): ติดตามว่าข่าวไหนยังไม่ถูกเปิดอ่าน (popup) — โชว์ป้าย "New" สีทอง
  // เก็บลง localStorage ด้วย (ไม่ใช่แค่ React state) เพื่อให้จำได้ข้ามการ reload หน้าเว็บ ไม่งั้นทุกครั้ง
  // ที่ MBBook รีเฟรชหน้าจะเห็น "New" ขึ้นใหม่หมดทั้งที่อ่านไปแล้ว
  const [readNewsIds, setReadNewsIds] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('ai_stock_read_news_ids') || '[]')); }
    catch { return new Set(); }
  });
  const markNewsRead = (id) => {
    setReadNewsIds(prev => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      try { localStorage.setItem('ai_stock_read_news_ids', JSON.stringify([...next])); } catch { /* ignore */ }
      return next;
    });
  };
  // ✅ เพิ่ม 2026-07-05 (รอบ 10): ข่าวจริงทั้งหมดที่ต้องแสดง = MOCK_NEWS (คงที่) + extraNews (ที่
  // จำลองเพิ่มเข้ามาระหว่างทดสอบ) — ใช้ฟังก์ชันนี้แทนการอ้าง MOCK_NEWS ตรงๆ ทุกจุดที่เกี่ยวกับการนับ/
  // แสดงผล เพื่อให้ข่าวจำลองใหม่ถูกนับรวมด้วยเสมอ
  const getAllNews = () => [...MOCK_NEWS, ...extraNews];

  // ✅ เพิ่ม 2026-07-05 (รอบ 9): ปุ่ม "อ่านทั้งหมด" — MBBook ขอไว้เผื่อระบบข่าวจริง (#51) ต่อเสร็จ
  // แล้วมีข่าวเป็นร้อย จะได้ไม่ต้องกดเข้า popup ทีละอันเพื่อ mark อ่าน
  const markAllNewsRead = () => {
    setReadNewsIds(prev => {
      const next = new Set(prev);
      getAllNews().forEach(a => next.add(a.id));
      try { localStorage.setItem('ai_stock_read_news_ids', JSON.stringify([...next])); } catch { /* ignore */ }
      return next;
    });
    showToast('ทำเครื่องหมายว่าอ่านแล้วทั้งหมด');
  };

  // ✅ เพิ่ม 2026-07-05 (รอบ 10): ปุ่มทดสอบ — จำลองข่าวใหม่เข้ามาตอนนี้ (timestamp = ปัจจุบัน) เพื่อให้
  // MBBook เช็คได้ว่า (1) ข่าวใหม่ขึ้นบนสุดจริงไหม (2) มีป้าย "New" สีทองไหม (3) กด "อ่านทั้งหมด" แล้ว
  // ป้ายหายไปด้วยไหม — เป็นเครื่องมือทดสอบชั่วคราว ลบทิ้งได้พร้อม MOCK_NEWS ตอนต่อ backend จริง (#51)
  const addTestNews = () => {
    const now = new Date();
    const testId = -Date.now(); // ใช้เลขติดลบกันชนกับ id ของ MOCK_NEWS (1-24) แน่นอน
    const newArticle = {
      id: testId,
      tickers: ['NVDA'],
      headline: `[ทดสอบ] ข่าวจำลองเข้ามาใหม่ตอน ${now.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`,
      sentiment: 'Neutral',
      impact: 'ต่ำ',
      source: 'Test',
      body: 'ข่าวนี้สร้างขึ้นเพื่อทดสอบระบบเรียงลำดับตามเวลาและป้าย "New" เท่านั้น ไม่ใช่ข่าวจริง จะหายไปเองถ้ารีเฟรชหน้าเว็บ (ไม่ได้บันทึกลง backend)',
      timestamp: now.getTime(),
      date: `${now.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })} · ${now.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}`,
    };
    setExtraNews(prev => [...prev, newArticle]);
    setNewsPage(1);
    showToast('เพิ่มข่าวทดสอบแล้ว — ดูบนสุดของหน้า News');
  };

  // Toast
  const [toast, setToast] = useState(null); // { text, phase: 'in'|'out' }
  const toastTimerRef = useRef(null);

  const showToast = (text) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ text, phase: 'in' });
    toastTimerRef.current = setTimeout(() => {
      setToast(t => (t ? { ...t, phase: 'out' } : t));
      setTimeout(() => setToast(null), 250);
    }, 2400);
  };

  // Generic popup — { type: 'trade'|'stockDetail'|'newsDetail'|'addTicker'|'confirmDelete', data, phase, originRect }
  const [popup, setPopup] = useState(null);

  // ✅ เพิ่ม 2026-07-07: ปุ่มซ่อนตัวเลขเงิน (สำหรับเวลาเปิดจอให้คนอื่นดู) — mask เฉพาะตัวเลขที่เกี่ยวกับ
  // การถือครอง/พอร์ตจริง (KPI, HoldingsTable, HoldingCard, popup ต้นทุนตอนถือหุ้น) ไม่ mask ราคาตลาด
  // ของ Tickers เพราะเป็นข้อมูลสาธารณะ ไม่ใช่ข้อมูลส่วนตัว
  const [hideAmounts, setHideAmounts] = useState(false);
  const MASK = '••••••';

  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const openPopup = (type, data, triggerEl) => {
    const rect = triggerEl.getBoundingClientRect();
    setPopup({ type, data, phase: 'opening', originRect: rect });
    // ✅ แก้บั๊ก 2026-07-05 (รอบ 4): double-rAF เดิมบางทีไม่ได้ paint frame แรก (opening) จริงก่อนสลับ
    // เป็น open เพราะ React 18 batch update ใน rAF callback ด้วย ทำให้ popup ไม่เห็น animation ขยาย
    // จากการ์ดจริง (โผล่มาที่ตำแหน่งสุดท้ายเลย) — เปลี่ยนเป็น setTimeout (macrotask, รอ paint แน่นอน)
    setTimeout(() => {
      setPopup(p => (p && p.type === type ? { ...p, phase: 'open' } : p));
    }, 20);
  };

  // เปิด popup ยืนยันลบ "จากภายใน" popup รายละเอียดหุ้นอีกที (ไม่ใช่เปิดจากการ์ด) — ข้าม animation
  // ขยายจากการ์ด (ไม่มี origin element ให้อ้างอิงในเคสนี้) เปิดตรงกลางจอทันที
  const openConfirmDeleteFromDetail = (ticker) => {
    setPopup({ type: 'confirmDelete', data: { ticker }, phase: 'open', originRect: { top: window.innerHeight / 2, left: window.innerWidth / 2, width: 0, height: 0 } });
  };

  const closePopup = () => {
    setPopup(p => (p ? { ...p, phase: 'closing' } : p));
    setTimeout(() => setPopup(null), 300);
  };

  // ===== Style helpers =====
  // ⚠️ แก้บั๊ก 2026-07-08: MBBook ทักว่าทั้งหน้าเว็บดูใหญ่/หลวมผิดสัดส่วนเทียบกับ mockup — root cause
  // จริง: เดิม `page` มีแค่ `maxWidth: '100vw'` ซึ่งไม่ได้จำกัดความกว้างอะไรเลย (แค่กันล้นจอ) เนื้อหาทั้งหมด
  // เลยยืดเต็มความกว้างหน้าจอเสมอ ต่างจาก mockup ที่มี `.desktop-shell{max-width:1180px}` คุมไว้เสมอ —
  // แก้โดยแยกเป็น 2 ชั้น: `pageBg` (พื้นหลัง เต็มจอเสมอ ไม่จำกัดความกว้าง) กับ `pageContent` (เนื้อหาจริง
  // จำกัดความกว้างสูงสุด 1180px เท่า mockup + จัดกึ่งกลางด้วย margin auto บน Desktop เท่านั้น — Mobile
  // ยังคงเต็มความกว้างจอเหมือนเดิมเพราะมือถือจอไม่กว้างพอที่จะมีปัญหานี้)
  const DESKTOP_MAX_W = 1180;
  const styles = {
    pageBg: {
      background: COLORS.bgGradient, minHeight: '100vh',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', system-ui, sans-serif",
      overflowX: 'hidden', boxSizing: 'border-box', color: COLORS.text,
    },
    pageContent: {
      maxWidth: isMobile ? '100%' : DESKTOP_MAX_W,
      margin: isMobile ? 0 : '0 auto',
      padding: isMobile ? SP.md : SP.xl,
      paddingBottom: isMobile ? 90 : SP.xl,
      boxSizing: 'border-box',
    },
    card: {
      backgroundColor: COLORS.cardBg,
      border: `1px solid ${COLORS.cardBorder}`,
      borderRadius: 18,
      padding: isMobile ? SP.lg : SP.xl,
    },
    cardTight: {
      backgroundColor: COLORS.cardBg,
      border: `1px solid ${COLORS.cardBorder}`,
      borderRadius: 16,
      padding: SP.lg,
    },
    // ✅ แก้ 2026-07-05 (รอบ 6): MBBook ทักท้วงว่าตัวหนังสือฝั่ง Desktop เล็กไปทุกตัว — เดิม
    // sectionTitle/label ใช้ค่าคงที่เดียวกันทั้ง mobile/desktop ทั้งที่จอ desktop กว้างกว่ามาก
    // ควรอ่านง่ายกว่า ไม่ใช่เท่ากัน ปรับให้ใหญ่ขึ้นเฉพาะ desktop (styles สร้างใหม่ทุก render อยู่แล้ว
    // เพราะอยู่ใน DashboardV4 จึงอ่าน isMobile ได้ตรงนี้เลย ไม่ต้องแก้ทีละจุด)
    sectionTitle: { fontSize: isMobile ? 15 : 18, fontWeight: 600, color: COLORS.text, margin: 0 },
    label: { color: COLORS.muted, fontSize: isMobile ? 12 : 13.5, display: 'block', marginBottom: SP.xs },
    input: {
      width: '100%', boxSizing: 'border-box',
      padding: isMobile ? '12px 14px' : '12px 14px',
      backgroundColor: 'rgba(148,163,184,0.08)',
      color: COLORS.text,
      border: `1px solid ${COLORS.cardBorder}`,
      borderRadius: 10,
      fontSize: isMobile ? 16 : 15.5,
      minHeight: isMobile ? 46 : 44,
    },
    stack: (gap) => ({ display: 'flex', flexDirection: 'column', gap: gap ?? SP.lg }),
    row: (gap) => ({ display: 'flex', alignItems: 'center', gap: gap ?? SP.sm }),
  };

  const clayGoldStyle = (extra = {}) => ({
    background: `linear-gradient(145deg, ${COLORS.goldLight}, ${COLORS.goldDark})`,
    color: '#3A2405',
    border: 'none',
    borderRadius: 14,
    fontWeight: 700,
    cursor: 'pointer',
    ...extra,
  });

  const btn = (variant = 'primary', extra = {}) => {
    const base = {
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: SP.xs,
      padding: isMobile ? '13px 18px' : '10px 16px',
      minHeight: isMobile ? 46 : 'auto',
      borderRadius: 12,
      fontSize: isMobile ? 15 : 14,
      fontWeight: 600,
      cursor: 'pointer',
      border: '1px solid transparent',
    };
    const variants = {
      primary: { backgroundColor: COLORS.purple, color: '#fff' },
      success: { backgroundColor: COLORS.green, color: '#0B1130' },
      danger: { backgroundColor: COLORS.red, color: '#0B1130' },
      ghost: { backgroundColor: 'transparent', color: COLORS.muted, border: `1px solid ${COLORS.cardBorder}` },
      outline: { backgroundColor: 'transparent', color: COLORS.purple, border: `1px solid ${COLORS.purple}` },
    };
    return { ...base, ...variants[variant], ...extra };
  };

  const tabs = [
    { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
    { id: 'tickers', label: 'Tickers', icon: TrendingUp },
    { id: 'news', label: 'News', icon: Newspaper },
    { id: 'system', label: 'System', icon: Settings },
  ];

  useEffect(() => {
    fetchStocks();
    fetchPortfolio();
    fetchHistory();
    fetchPortfolioHistory();
    fetchNikSuggestions();
    fetchCostSummary();
    fetchReports();
    fetchRoiSummary();
    // ✅ auto-refresh ตามที่แนะนำและ MBBook รับได้: poll ทุก 5 นาทีตอนแอปเปิดอยู่ (ไม่ทุกวินาที
    // เพื่อประหยัด request) — mobile ใช้ pull-to-refresh เพิ่มเติม (ดูฟังก์ชัน handlePullRefresh)
    const poll = setInterval(() => {
      fetchStocks();
      fetchPortfolio();
    }, 5 * 60 * 1000);
    return () => clearInterval(poll);
  }, []);

  const fetchStocks = async () => {
    try {
      const response = await authFetch(`${API_URL}/stocks`);
      const data = await response.json();
      setStocks(data.stocks || []);
    } catch (error) {
      console.error('Error fetching stocks:', error);
    }
  };

  const fetchPortfolio = async () => {
    try {
      const response = await authFetch(`${API_URL}/portfolio`);
      const data = await response.json();
      setPortfolioData(data);
    } catch (error) {
      console.error('Error fetching portfolio:', error);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await authFetch(`${API_URL}/workflow/history?limit=30`);
      const data = await response.json();
      setHistoryData(data);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  // ✅ ใช้สำหรับกราฟแท่ง Monthly/Yearly + กราฟเส้น Cumulative (ดึงเต็มไว้ก่อน แล้ว slice/group ฝั่ง
  // client ตาม periodMode เพื่อสลับมุมมองได้ทันทีไม่ต้องยิง API ใหม่ — ดู getChartPoints)
  const fetchPortfolioHistory = async () => {
    try {
      const response = await authFetch(`${API_URL}/roi/portfolio-history`);
      const data = await response.json();
      if (!data.error) setPortfolioHistory(data);
    } catch (error) {
      console.error('Error fetching portfolio history:', error);
    }
  };

  const fetchNikSuggestions = async () => {
    try {
      const response = await authFetch(`${API_URL}/nik/suggestions`);
      const data = await response.json();
      setNikSuggestions(data);
    } catch (error) {
      console.error('Error fetching nik suggestions:', error);
    }
  };

  const fetchCostSummary = async () => {
    try {
      const response = await authFetch(`${API_URL}/costs/summary`);
      const data = await response.json();
      setCostSummary(data);
    } catch (error) {
      console.error('Error fetching cost summary:', error);
    }
  };

  const fetchReports = async () => {
    try {
      const response = await authFetch(`${API_URL}/workflow/reports?limit=7`);
      const data = await response.json();
      setReportList(data);
    } catch (error) {
      console.error('Error fetching reports:', error);
    }
  };

  // ✅ เพิ่ม 2026-07-05 (รอบ 4): endpoint นี้มีอยู่แล้วตั้งแต่ Phase 1 evaluation (task #40) แต่รอบ
  // rebuild System tab ที่แล้วลืมต่อเข้า UI เลย — MBBook ทักว่า "ไม่มี win rate @14/@30 Day"
  const fetchRoiSummary = async () => {
    try {
      const response = await authFetch(`${API_URL}/roi/summary`);
      const data = await response.json();
      setRoiSummary(data);
    } catch (error) {
      console.error('Error fetching roi summary:', error);
    }
  };

  const handleAddStock = async () => {
    if (!newTicker.trim()) return;
    if (stocks.length >= MAX_TICKERS) {
      setTradeParseMessage(null);
      showToast(`เพิ่มไม่ได้ — ระบบรองรับสูงสุด ${MAX_TICKERS} tickers (ปัจจุบัน ${stocks.length}/${MAX_TICKERS})`);
      return;
    }
    setAddingTicker(true);
    try {
      const response = await authFetch(`${API_URL}/stocks?ticker=${newTicker.toUpperCase()}`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'added' || data.status === 'exists') {
        setNewTicker('');
        fetchStocks();
        closePopup();
        showToast(`เพิ่ม ${data.ticker || newTicker.toUpperCase()} สำเร็จ`);
      }
    } catch (error) {
      console.error('Error adding stock:', error);
    }
    setAddingTicker(false);
  };

  const handleRemoveStock = async (ticker) => {
    try {
      await authFetch(`${API_URL}/stocks/${ticker}`, { method: 'DELETE' });
      fetchStocks();
      closePopup();
      showToast(`ลบ ${ticker} ออกจากรายการแล้ว`);
    } catch (error) {
      console.error('Error removing stock:', error);
    }
  };

  const handleSelectTradeImage = (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setTradeImageFile(file);
    setTradeImagePreview(URL.createObjectURL(file));
    setTradeParseMessage(null);
  };

  const handleParseTradeImage = async () => {
    if (!tradeImageFile) {
      setTradeParseMessage({ type: 'error', text: 'เลือกรูปสลิปก่อนครับ' });
      return;
    }
    setTradeParsing(true);
    setTradeParseMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', tradeImageFile);
      const response = await authFetch(`${API_URL}/trade-parse-image`, { method: 'POST', body: formData });
      const data = await response.json();
      if (data.status === 'parsed') {
        setTradeTicker(data.ticker || '');
        setTradeAction(data.action === 'SELL' ? 'SELL' : 'BUY');
        setTradeShares(data.shares != null ? String(data.shares) : '');
        setTradePrice(data.price != null ? String(data.price) : '');
        setTradeParseMessage({ type: 'success', text: 'อ่านรูปแล้ว — ตรวจทานข้อมูลด้านล่างก่อนกดบันทึก' });
      } else {
        setTradeParseMessage({ type: 'error', text: `อ่านรูปไม่สำเร็จ: ${data.message || 'ไม่ทราบสาเหตุ'} — กรอกมือแทนได้` });
      }
    } catch (error) {
      setTradeParseMessage({ type: 'error', text: `เชื่อมต่อไม่ได้: ${error.message}` });
    }
    setTradeParsing(false);
  };

  const resetTradeForm = () => {
    setTradeTicker('');
    setTradeShares('');
    setTradePrice('');
    setTradeImageFile(null);
    setTradeImagePreview(null);
    setTradeParseMessage(null);
    setTradeMessage(null);
  };

  const handleSubmitTrade = async () => {
    const ticker = tradeTicker.trim().toUpperCase();
    const shares = parseFloat(tradeShares);
    const price = parseFloat(tradePrice);

    if (!ticker) { setTradeMessage({ type: 'error', text: 'กรอกชื่อหุ้นก่อนครับ' }); return; }
    if (!shares || shares <= 0) { setTradeMessage({ type: 'error', text: 'จำนวนหุ้นต้องมากกว่า 0 (ใส่ทศนิยมได้ เช่น 0.1874433)' }); return; }
    if (!price || price <= 0) { setTradeMessage({ type: 'error', text: 'ราคาต้องมากกว่า 0' }); return; }

    setTradeSubmitting(true);
    setTradeMessage(null);
    try {
      const params = new URLSearchParams({ ticker, action: tradeAction, shares: String(shares), price: String(price) });
      const response = await authFetch(`${API_URL}/trade-update?${params}`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'recorded') {
        fetchPortfolio();
        closePopup();
        resetTradeForm();
        showToast(`บันทึกรายการสำเร็จ: ${tradeAction === 'BUY' ? 'ซื้อ' : 'ขาย'} ${ticker} ${shares} หุ้น @ $${price}`);
      } else {
        setTradeMessage({ type: 'error', text: `เกิดข้อผิดพลาด: ${JSON.stringify(data)}` });
      }
    } catch (error) {
      setTradeMessage({ type: 'error', text: `เชื่อมต่อไม่ได้: ${error.message}` });
    }
    setTradeSubmitting(false);
  };

  const filteredStocks = stocks.filter(s => s.ticker.toLowerCase().includes(searchTerm.toLowerCase()));

  // ===== Format helpers =====
  const fmtUSD = (v) => (v == null ? '—' : `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })}`);
  const fmtTHB = (v) => (v == null ? null : `฿${Number(v).toLocaleString('th-TH', { maximumFractionDigits: 0 })}`);
  const fmtMarketCap = (m) => {
    if (m == null) return '—';
    if (m >= 1e6) return `$${(m / 1e6).toFixed(2)}T`;
    if (m >= 1e3) return `$${(m / 1e3).toFixed(1)}B`;
    return `$${m.toFixed(0)}M`;
  };
  const signalColor = (sig) => sig === 'BUY' ? COLORS.green : sig === 'SELL' ? COLORS.red : COLORS.muted;
  const signalBgColor = (sig) => sig === 'BUY' ? COLORS.greenSoft : sig === 'SELL' ? COLORS.redSoft : 'rgba(148,163,184,0.14)';
  const signalLabel = (sig) => sig === 'BUY' ? 'BUY' : sig === 'SELL' ? 'SELL' : 'HOLD';

  // ✅ ตาม UI_Spec.md ข้อ 4: THB เป็นตัวหลัก (ใหญ่/เด่น) USD เป็นตัวรอง (เล็ก/เทา) โชว์คู่กันเสมอ
  // ไม่ใช่ปุ่ม toggle สลับสกุลแบบรอบแรกที่ทำผิดไป
  const MoneyDual = ({ thb, usd, mainSize = 18, mainColor, mainWeight = 800 }) => (
    <div>
      <p style={{ margin: 0, fontSize: mainSize, fontWeight: mainWeight, color: mainColor || COLORS.text }}>
        {hideAmounts ? `฿${MASK}` : (thb != null ? fmtTHB(thb) : `${fmtUSD(usd)} (รออัตราแลกเปลี่ยน)`)}
      </p>
      {thb != null && (
        <p style={{ margin: '2px 0 0 0', fontSize: Math.max(12.5, mainSize - 7), color: COLORS.muted }}>
          {hideAmounts ? `≈ $${MASK}` : `≈ ${fmtUSD(usd)}`}
        </p>
      )}
    </div>
  );

  // ✅ เพิ่ม 2026-07-05 (รอบ 5, Finding 8): day-change ระดับ "พอร์ตรวม" คำนวณได้จริงจาก
  // portfolioHistory.daily (snapshot รายวันที่มีอยู่แล้ว) — ต่างจาก day-change ระดับรายหุ้นซึ่งยังไม่มี
  // ข้อมูลราคาปิดเมื่อวานเก็บแยกต่อ ticker (ยัง fabricate ไม่ได้ อันนั้นยังเป็น gap อยู่)
  const getPortfolioDayChange = () => {
    const daily = portfolioHistory?.daily || [];
    if (daily.length < 2) return null;
    const today = daily[daily.length - 1];
    const yesterday = daily[daily.length - 2];
    if (!yesterday.total_value) return null;
    const diffUsd = today.total_value - yesterday.total_value;
    return { diffUsd, pct: (diffUsd / yesterday.total_value) * 100 };
  };

  // return_pct ของ snapshot ล่าสุด = ผลตอบแทนสะสมตั้งแต่ต้นทุนจริง ตรงกับนิยามใน
  // agents.py::portfolio_return_history() — ใช้ตรงๆ แทนคำนวณซ้ำ
  const getCumulativeReturnPct = () => {
    const daily = portfolioHistory?.daily || [];
    if (daily.length > 0) return daily[daily.length - 1].return_pct;
    if (portfolioData?.total_cost) return (portfolioData.total_gain / portfolioData.total_cost) * 100;
    return null;
  };

  const fmtChartDateLabelDesktop = (period) => {
    const d = new Date(`${period}T00:00:00`);
    return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short' });
  };

  // ===== Date range helpers (สำหรับกราฟ Portfolio) =====
  const dateRangeLabel = {
    today: 'วันนี้ถึงตอนนี้', '7d': '7 วันล่าสุด', '30d': '30 วันล่าสุด',
    lastMonth: 'เดือนก่อน', custom: 'กำหนดเอง',
  };

  // ✅ generalize รับพารามิเตอร์ได้ (mode/cStart/cEnd) เพื่อใช้ซ้ำกับกราฟต้นทุนใน System tab
  const computeRangeBoundsFor = (mode, cStart, cEnd) => {
    const today = new Date();
    const toStr = (d) => d.toISOString().slice(0, 10);
    if (mode === 'today') return { start: toStr(today), end: toStr(today) };
    if (mode === '7d') { const s = new Date(today); s.setDate(s.getDate() - 7); return { start: toStr(s), end: toStr(today) }; }
    if (mode === '30d') { const s = new Date(today); s.setDate(s.getDate() - 30); return { start: toStr(s), end: toStr(today) }; }
    if (mode === 'lastMonth') {
      const s = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const e = new Date(today.getFullYear(), today.getMonth(), 0);
      return { start: toStr(s), end: toStr(e) };
    }
    if (mode === 'custom' && cStart && cEnd) return { start: cStart, end: cEnd };
    return { start: null, end: null };
  };
  // ✅ "สะสม" ใช้ข้อมูลเต็มเสมอ (ตาม comment ใน backend agents.py portfolio_return_history —
  // ยืนยันแล้วว่าตั้งใจให้เป็นแบบนี้). "รายเดือน" = ROI สะสม ณ สิ้นเดือน 6 เดือนล่าสุด ไม่รวมเดือนปัจจุบัน
  // (เดือนปัจจุบันยังไม่จบ เทียบเป้า 13%/เดือนยังไม่ fair). "รายปี" = ROI สะสม ณ snapshot ล่าสุดของแต่ละปี
  // ที่มีข้อมูล (รวมปีปัจจุบันด้วย เพราะ MBBook อยากเห็น progress ระหว่างปีเทียบเป้า 15%/ปี)
  const getChartPoints = () => {
    if (!portfolioHistory) return [];
    if (periodMode === 'cumulative') return portfolioHistory.daily || [];
    if (periodMode === 'yearly') return getYearlyChartPoints();
    const monthly = portfolioHistory.monthly || [];
    const thisMonth = new Date().toISOString().slice(0, 7);
    return monthly.filter(p => p.period < thisMonth).slice(-6);
  };

  // เก็บ snapshot ล่าสุดที่มีของแต่ละปีปฏิทิน (ข้อมูลเรียงจากเก่า→ใหม่อยู่แล้วจาก backend จึงวน
  // เขียนทับตัวเก่าไปเรื่อยๆ ตัวสุดท้ายที่เหลือคือตัวล่าสุดของปีนั้น) — ใช้ monthly ก่อน ถ้าไม่มีค่อย fallback
  // เป็น daily (พอร์ตใหม่มาก ยังไม่มี monthly snapshot)
  const getYearlyChartPoints = () => {
    const source = (portfolioHistory?.monthly?.length ? portfolioHistory.monthly : portfolioHistory?.daily) || [];
    if (source.length === 0) return [];
    const byYear = {};
    source.forEach(p => { byYear[p.period.slice(0, 4)] = p; });
    return Object.entries(byYear).sort(([a], [b]) => a.localeCompare(b))
      .map(([year, p]) => ({ period: year, return_pct: p.return_pct, total_value: p.total_value }));
  };

  const fmtChartDateLabel = (period) => {
    if (periodMode === 'yearly') return period; // 'YYYY' ตรงจาก backend (ปี ค.ศ. ไม่แปลง พ.ศ.)
    if (periodMode === 'monthly') {
      const [y, m] = period.split('-');
      return `${m}/${y.slice(2)}`;
    }
    const [, m, d] = period.split('-');
    return `${parseInt(d, 10)}/${parseInt(m, 10)}`;
  };

  // ✅ เพิ่ม 2026-07-05 (รอบ 5, Finding 2): กราฟต้นทุนระบบ System tab — รวม historyData.runs
  // (มีอยู่แล้วจาก fetchHistory) เป็นรายวัน/รายเดือน ไม่ต้องเพิ่ม endpoint ใหม่
  const getCostDailyPoints = () => {
    const runs = historyData?.runs || [];
    const byDay = {};
    for (const r of runs) {
      if (!r.timestamp || r.cost_usd == null) continue;
      const day = r.timestamp.slice(0, 10);
      byDay[day] = (byDay[day] || 0) + r.cost_usd;
    }
    return Object.entries(byDay).sort(([a], [b]) => a.localeCompare(b)).map(([period, cost_usd]) => ({ period, cost_usd }));
  };
  const getCostMonthlyPoints = () => {
    const runs = historyData?.runs || [];
    const byMonth = {};
    for (const r of runs) {
      if (!r.timestamp || r.cost_usd == null) continue;
      const month = r.timestamp.slice(0, 7);
      byMonth[month] = (byMonth[month] || 0) + r.cost_usd;
    }
    return Object.entries(byMonth).sort(([a], [b]) => a.localeCompare(b)).map(([period, cost_usd]) => ({ period, cost_usd }));
  };
  const getCostChartPoints = () => {
    if (costPeriodMode === 'cumulative') {
      let running = 0;
      return getCostDailyPoints().map(p => { running += p.cost_usd; return { period: p.period, cost_usd: running }; });
    }
    const source = costPeriodMode === 'monthly' ? getCostMonthlyPoints() : getCostDailyPoints();
    const { start, end } = computeRangeBoundsFor(costDateRangeMode, costCustomStart, costCustomEnd);
    if (!start || !end) return source;
    return source.filter(p => p.period >= start.slice(0, p.period.length) && p.period <= end.slice(0, p.period.length));
  };

  // ===== Chart components (เรียกเป็น function ตรงๆ ไม่ใช่ JSX tag — ไม่มี hook ข้างในจึงปลอดภัย) =====
  // ✅ หมายเหตุ implementation: ใช้ CSS keyframe (barGrow / line-draw) แทนการวัดตำแหน่ง DOM แบบ FLIP
  // ด้วยมือ (getBoundingClientRect) ที่เคยเจอบั๊กแท่งกระตุกตกค้างมาก่อน — วิธีนี้ปลอดภัยกว่า (React
  // reconcile ด้วย key เอง) แลกกับ animation ที่ไม่ใช่ FLIP แบบเป๊ะๆ ถ้าอยากได้แบบ pixel-perfect FLIP
  // ทีหลังค่อยอัปเกรดจุดนี้ทีเดียว
  // ✅ 2026-07-08: เพิ่ม `fill` — ใช้ตอนอยู่ใน DesktopChartBlock (grid item ที่ถูก stretch ให้สูงเท่า
  // คอลัมน์ KPI cards ข้างๆ) height:200 ตายตัวเดิมทำให้การ์ดกราฟเตี้ยกว่า 3 การ์ด KPI เพราะไม่ยอมโต
  // ตาม container ที่ stretch ไว้ — flex:1 (แทน height คงที่) ให้มันโตเต็มพื้นที่ที่เหลือใน flex column
  // ของ DesktopChartBlock เอง (Mobile ไม่ส่ง fill มา เลยยังคงสูง 200 คงที่เหมือนเดิม ไม่กระทบ)
  const BarChart = ({ points, fill }) => {
    if (!points || points.length === 0) {
      return <div style={{ ...styles.cardTight, textAlign: 'center', color: COLORS.faint, fontSize: 13 }}>ยังไม่มีข้อมูลกราฟในช่วงที่เลือก</div>;
    }
    const maxAbs = Math.max(...points.map(p => Math.abs(p.return_pct)), 1);
    const MIN_COL_W = isMobile ? 40 : 48;
    return (
      <div style={{ ...styles.cardTight, display: 'flex', alignItems: 'flex-end', gap: 4, ...(fill ? { flex: 1, minHeight: 200 } : { height: 200 }), overflowX: 'auto', minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: '100%', width: '100%', minWidth: points.length * MIN_COL_W }}>
          {points.map(p => {
            const heightPct = Math.max((Math.abs(p.return_pct) / maxAbs) * 100, 4);
            const isPos = p.return_pct >= 0;
            return (
              <div key={p.period} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: '1 1 0', minWidth: MIN_COL_W, height: '100%', justifyContent: 'flex-end' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: isPos ? COLORS.gold : COLORS.red, marginBottom: 4, whiteSpace: 'nowrap' }}>
                  {isPos ? '+' : ''}{p.return_pct}%
                </span>
                <div className="chart-bar" style={{
                  width: '55%', maxWidth: isMobile ? 26 : 32, height: `${heightPct}%`, minHeight: 6,
                  borderRadius: 6, background: `linear-gradient(180deg, ${COLORS.purple}, ${COLORS.purpleSoft})`,
                }} />
                <span style={{ fontSize: 10, color: COLORS.faint, marginTop: 6, whiteSpace: 'nowrap' }}>{fmtChartDateLabel(p.period)}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const CumulativeLineChart = ({ points, fill }) => {
    if (!points || points.length === 0) {
      return <div style={{ ...styles.cardTight, textAlign: 'center', color: COLORS.faint, fontSize: 13 }}>ยังไม่มีข้อมูลสะสม</div>;
    }
    const W = 600, H = 180, PAD = 24;
    const vals = points.map(p => p.return_pct);
    const min = Math.min(...vals, 0), max = Math.max(...vals, 0);
    const range = (max - min) || 1;
    const stepX = (W - PAD * 2) / Math.max(points.length - 1, 1);
    const coords = points.map((p, i) => {
      const x = PAD + i * stepX;
      const y = H - PAD - ((p.return_pct - min) / range) * (H - PAD * 2);
      return [x, y];
    });
    const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c[0].toFixed(1)} ${c[1].toFixed(1)}`).join(' ');
    const last = points[points.length - 1];
    const lastCoord = coords[coords.length - 1];
    // ✅ 2026-07-08: MBBook ทักว่าตัวเลข "+X%" ในการ์ดกราฟสะสม ใหญ่แปลกๆ ไม่สมส่วน — root cause คือ
    // เดิม label เป็น <text> ในหน่วย viewBox (600x180) ร่วมกับ preserveAspectRatio="none" (ยืด SVG
    // ไม่รักษาสัดส่วนให้เต็ม container) พอการ์ดกราฟเปลี่ยนความสูง (จาก fill:true ที่เพิ่งแก้ไป) อัตราส่วน
    // กว้าง:สูงของ container เปลี่ยนไปจาก viewBox เดิมมาก → ตัวเลขถูกยืดเพี้ยนไปด้วย ย้าย label ออกมา
    // เป็น <span> HTML ธรรมดาแทน (วางตำแหน่งด้วย % ของ container แต่ font-size เป็น px จริง ไม่ยืดตาม
    // viewBox เลยนิ่งเสมอไม่ว่าการ์ดจะสัดส่วนแบบไหน)
    const labelLeftPct = Math.min(Math.max((lastCoord[0] / W) * 100, 8), 92);
    const labelTopPct = Math.max((lastCoord[1] / H) * 100 - 10, 4);
    return (
      <div style={{ ...styles.cardTight, position: 'relative', ...(fill ? { flex: 1, minHeight: 200 } : { height: 200 }) }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%', overflow: 'visible' }} preserveAspectRatio="none">
          <path d={path} fill="none" stroke={COLORS.purple} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="line-draw" vectorEffect="non-scaling-stroke" />
          <circle cx={lastCoord[0]} cy={lastCoord[1]} r={4} fill={COLORS.gold} />
        </svg>
        <span style={{ position: 'absolute', left: `${labelLeftPct}%`, top: `${labelTopPct}%`, transform: 'translateX(-50%)', fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap', color: last.return_pct >= 0 ? COLORS.gold : COLORS.red }}>
          {last.return_pct >= 0 ? '+' : ''}{last.return_pct}%
        </span>
      </div>
    );
  };

  // ⚠️ ลบ 2026-07-08: DesktopValueBarChart (กราฟแท่ง ฿ มูลค่ารวม) เคยตั้งใจให้ Desktop ต่างจาก Mobile
  // แต่ mockup รอบใหม่ (confirm แล้ว) ให้ Desktop ใช้กราฟ % เหมือน Mobile ทั้งหมด (Monthly/Yearly/
  // Cumulative ใช้ return_pct ตัวเดียวกัน) — MBBook ตัดสินใจเปลี่ยนมาใช้ BarChart({points}) แทนแล้ว
  // (ถามยืนยันก่อนแล้วเพราะขัดกับ comment เดิมที่เคยตั้งใจแยก Desktop/Mobile ไว้)

  // ===== Sliding pill selector (period toggle ของ Portfolio Mobile/Desktop + Cost chart ใน System) =====
  const SlidingPill = ({ options, value, onChange }) => (
    <div style={{ display: 'inline-flex', backgroundColor: 'rgba(148,163,184,0.08)', borderRadius: 12, padding: 4, gap: 2 }}>
      {options.map(opt => {
        const active = opt.value === value;
        return (
          <button key={opt.value} className="pill-btn" onClick={() => onChange(opt.value)} style={{
            padding: isMobile ? '9px 14px' : '8px 16px', borderRadius: 10, border: 'none',
            fontSize: 13, fontWeight: 700, cursor: 'pointer',
            backgroundColor: active ? COLORS.purple : 'transparent',
            color: active ? '#fff' : COLORS.muted,
            transition: 'background-color 0.2s ease',
            // ✅ 2026-07-08: min-width + text-align center ตาม mockup fix — กันคำแต่ละคำ (Monthly/
            // Yearly/Cumulative) ชิดซ้ายในคอลัมน์ตัวเองตอนความยาวคำไม่เท่ากัน (มีแค่ 3 จุดใช้คอมโพเนนต์นี้
            // ทั้งหมดเป็น period pill พอดี ไม่กระทบ pagination ของ News ซึ่งใช้ NewsPagination แยกต่างหาก)
            minWidth: 84, textAlign: 'center',
          }}>
            {opt.label}
          </button>
        );
      })}
    </div>
  );

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 2): generalize เป็น prop-based เพื่อใช้ซ้ำกับกราฟต้นทุนใน
  // System tab ได้ (เดิม hardcode ผูกกับ state ของ Portfolio เท่านั้น)
  const DateRangeDropdownGeneric = ({ value, onChange, isOpen, onToggle, cStart, cEnd, onCStart, onCEnd }) => (
    <div style={{ position: 'relative' }}>
      <button className="press-btn" onClick={onToggle} style={{
        ...styles.row(SP.xs), padding: '8px 12px', borderRadius: 10,
        backgroundColor: 'rgba(148,163,184,0.08)', border: `1px solid ${COLORS.cardBorder}`,
        color: COLORS.text, fontSize: 13, fontWeight: 600, cursor: 'pointer',
      }}>
        {dateRangeLabel[value]} <ChevronDown size={14} />
      </button>
      {isOpen && (
        <div style={{
          position: 'absolute', top: '110%', right: 0, zIndex: 60, minWidth: 200,
          backgroundColor: '#111431', border: `1px solid ${COLORS.cardBorder}`, borderRadius: 12,
          padding: SP.sm, boxShadow: '0 12px 30px rgba(0,0,0,0.4)',
        }}>
          {['today', '7d', '30d', 'lastMonth'].map(key => (
            <button key={key} className="press-btn" onClick={() => onChange(key)} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%',
              padding: '9px 10px', borderRadius: 8, border: 'none', textAlign: 'left', cursor: 'pointer',
              backgroundColor: value === key ? COLORS.purpleSoft : 'transparent',
              color: value === key ? COLORS.purple : COLORS.text, fontSize: 13, fontWeight: 600,
            }}>
              {dateRangeLabel[key]} {value === key && <Check size={14} />}
            </button>
          ))}
          <div style={{ borderTop: `1px solid ${COLORS.cardBorder}`, marginTop: SP.xs, paddingTop: SP.sm }}>
            <p style={{ ...styles.label, marginBottom: 6 }}>กำหนดเอง</p>
            <div style={styles.row(SP.xs)}>
              <input type="date" value={cStart} onChange={(e) => onCStart(e.target.value)} style={{ ...styles.input, padding: '6px 8px', fontSize: 12 }} />
              <input type="date" value={cEnd} onChange={(e) => onCEnd(e.target.value)} style={{ ...styles.input, padding: '6px 8px', fontSize: 12 }} />
            </div>
            <button className="press-btn" onClick={() => { if (cStart && cEnd) onChange('custom'); }}
              style={btn('outline', { width: '100%', marginTop: SP.xs, padding: '6px', fontSize: 12, minHeight: 'auto' })}>
              ใช้ช่วงนี้
            </button>
          </div>
        </div>
      )}
    </div>
  );


  const CostDateRangeDropdown = () => DateRangeDropdownGeneric({
    value: costDateRangeMode,
    onChange: (key) => { setCostDateRangeMode(key); setCostDateDropdownOpen(false); },
    isOpen: costDateDropdownOpen, onToggle: () => setCostDateDropdownOpen(o => !o),
    cStart: costCustomStart, cEnd: costCustomEnd, onCStart: setCostCustomStart, onCEnd: setCostCustomEnd,
  });

  // ===== Inline message (สำหรับ error/success ในฟอร์ม ไม่ใช่ toast) =====
  const InlineMessage = ({ msg }) => {
    if (!msg) return null;
    const ok = msg.type === 'success';
    return (
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: SP.sm,
        padding: '10px 12px', borderRadius: 10, marginTop: SP.sm,
        backgroundColor: ok ? COLORS.greenSoft : COLORS.redSoft,
        color: ok ? COLORS.green : COLORS.red, fontSize: 13,
      }}>
        {ok ? <Check size={16} style={{ flexShrink: 0, marginTop: 1 }} /> : <Info size={16} style={{ flexShrink: 0, marginTop: 1 }} />}
        <span>{msg.text}</span>
      </div>
    );
  };

  // ===== Toast (slide up from bottom, auto-dismiss) =====
  const ToastView = () => {
    if (!toast) return null;
    return (
      <div className={toast.phase === 'in' ? 'toast-in' : 'toast-out'} style={{
        position: 'fixed', bottom: isMobile ? 76 : 24, left: '50%',
        backgroundColor: '#1A1F3D', border: `1px solid ${COLORS.cardBorder}`,
        color: COLORS.text, fontSize: 13, fontWeight: 600,
        padding: '12px 18px', borderRadius: 12, zIndex: 300,
        boxShadow: '0 10px 30px rgba(0,0,0,0.4)', maxWidth: '86vw',
        display: 'flex', alignItems: 'center', gap: SP.sm,
      }}>
        <Check size={16} style={{ color: COLORS.green, flexShrink: 0 }} />
        {toast.text}
      </div>
    );
  };

  // ===== POPUP CONTENTS =====

  const TradeFormContent = () => (
    <div style={styles.stack(SP.lg)}>
      <div>
        <p style={{ ...styles.row(SP.xs), color: COLORS.muted, fontSize: 13, marginBottom: SP.md, marginTop: 0 }}>
          <Camera size={16} /> ส่งรูปสลิปซื้อขาย (เช่น screenshot จาก Dime) ให้อ่านค่าอัตโนมัติ
        </p>
        <label style={{
          ...styles.row(SP.sm), justifyContent: 'center',
          padding: '14px', border: `1.5px dashed ${COLORS.cardBorder}`, borderRadius: 10,
          cursor: 'pointer', color: COLORS.muted, fontSize: 13, marginBottom: SP.md,
        }}>
          <Upload size={16} />
          {tradeImageFile ? tradeImageFile.name : 'เลือกรูปสลิป'}
          <input type="file" accept="image/*" capture="environment" onChange={handleSelectTradeImage} style={{ display: 'none' }} />
        </label>
        {tradeImagePreview && (
          <img src={tradeImagePreview} alt="trade slip preview"
            style={{ maxWidth: '100%', maxHeight: 200, borderRadius: 10, marginBottom: SP.md, display: 'block', border: `1px solid ${COLORS.cardBorder}` }} />
        )}
        <button className="press-btn" onClick={handleParseTradeImage} disabled={tradeParsing || !tradeImageFile}
          style={btn('outline', { width: '100%', opacity: (tradeParsing || !tradeImageFile) ? 0.5 : 1, cursor: (tradeParsing || !tradeImageFile) ? 'default' : 'pointer' })}>
          {tradeParsing ? 'กำลังอ่านรูป...' : 'อ่านข้อมูลจากรูป'}
        </button>
        {InlineMessage({ msg: tradeParseMessage })}
      </div>

      <div style={{ borderTop: `1px solid ${COLORS.cardBorder}`, paddingTop: SP.lg }}>
        <p style={{ color: COLORS.faint, fontSize: 12, marginTop: 0, marginBottom: SP.lg }}>
          ตรวจทาน/แก้ไขข้อมูลก่อนกดบันทึก — แก้มือได้เสมอ ไม่จำเป็นต้องส่งรูป
        </p>
        <div style={styles.stack(SP.md)}>
          <div>
            <label style={styles.label}>หุ้น (Ticker)</label>
            <input type="text" value={tradeTicker} onChange={(e) => setTradeTicker(e.target.value)} placeholder="เช่น WDC, NBIS..." style={styles.input} />
          </div>
          <div>
            <label style={styles.label}>ประเภท</label>
            <div style={styles.row(SP.sm)}>
              {['BUY', 'SELL'].map(a => {
                const active = tradeAction === a;
                const c = a === 'BUY' ? COLORS.green : COLORS.red;
                return (
                  <button key={a} className="press-btn" onClick={() => setTradeAction(a)} style={{
                    flex: 1, padding: isMobile ? 14 : 10, minHeight: isMobile ? 46 : 'auto',
                    borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: 'pointer',
                    border: `1px solid ${c}`, backgroundColor: active ? c : 'transparent', color: active ? '#0B1130' : c,
                  }}>
                    {a === 'BUY' ? 'ซื้อ' : 'ขาย'}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <label style={styles.label}>จำนวนหุ้น (ใส่ทศนิยมได้)</label>
            <input type="number" step="any" value={tradeShares} onChange={(e) => setTradeShares(e.target.value)} placeholder="เช่น 0.1874433" style={styles.input} />
          </div>
          <div>
            <label style={styles.label}>ราคาต่อหุ้น (USD)</label>
            <input type="number" step="any" value={tradePrice} onChange={(e) => setTradePrice(e.target.value)} placeholder="เช่น 537.97" style={styles.input} />
          </div>
          <button className="clay-btn" onClick={handleSubmitTrade} disabled={tradeSubmitting}
            style={clayGoldStyle({ width: '100%', padding: isMobile ? '14px' : '12px', fontSize: 15, minHeight: isMobile ? 48 : 'auto', opacity: tradeSubmitting ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: SP.xs })}>
            <Check size={16} /> {tradeSubmitting ? 'กำลังบันทึก...' : 'บันทึกรายการ'}
          </button>
          {InlineMessage({ msg: tradeMessage })}
        </div>
      </div>
    </div>
  );

  const AddTickerContent = () => (
    <div style={styles.stack(SP.md)}>
      <p style={{ color: COLORS.muted, fontSize: 13, margin: 0 }}>เพิ่ม ticker ใหม่เข้าระบบติดตาม ({stocks.length}/{MAX_TICKERS})</p>
      <input type="text" value={newTicker} onChange={(e) => setNewTicker(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleAddStock()}
        placeholder="เช่น NVDA, META..." style={styles.input} autoFocus />
      <button className="clay-btn" onClick={handleAddStock} disabled={addingTicker}
        style={clayGoldStyle({ width: '100%', padding: isMobile ? '14px' : '12px', fontSize: 15, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: SP.xs, opacity: addingTicker ? 0.7 : 1 })}>
        <Plus size={16} /> {addingTicker ? 'กำลังเพิ่ม...' : 'เพิ่มหุ้น'}
      </button>
    </div>
  );

  const ConfirmDeleteContent = ({ ticker }) => (
    <div style={styles.stack(SP.lg)}>
      <p style={{ color: COLORS.text, fontSize: 14, margin: 0 }}>ต้องการลบ <b>{ticker}</b> ออกจากรายการติดตามใช่ไหมครับ?</p>
      <div style={styles.row(SP.sm)}>
        <button className="press-btn" onClick={closePopup} style={btn('ghost', { flex: 1 })}>ยกเลิก</button>
        <button className="press-btn" onClick={() => handleRemoveStock(ticker)} style={btn('danger', { flex: 1 })}>
          <Trash2 size={15} /> ลบเลย
        </button>
      </div>
    </div>
  );

  // ✅ popup กลาง ใช้ร่วมกัน Tickers tab และ Portfolio holding (UI_Spec.md ข้อ 7)
  // data = { ticker } อย่างน้อย — จะไป lookup stock info + holding info เองจาก state ปัจจุบัน
  const StockDetailContent = ({ ticker }) => {
    const stock = stocks.find(s => s.ticker === ticker);
    const holding = (portfolioData?.holdings || []).find(h => h.ticker === ticker);
    if (!stock && !holding) return null;
    const sig = stock?.signal;
    const totalValue = portfolioData?.total_value;
    const weightPct = holding && totalValue ? (holding.current_value / totalValue) * 100 : null;

    return (
      <div style={styles.stack(SP.lg)}>
        <div>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: COLORS.text }}>
            {ticker}{(stock?.company_name || COMPANY_NAMES[ticker]) ? ` - ${stock?.company_name || COMPANY_NAMES[ticker]}` : ''}
          </h3>
          {sig && (
            <span key={sig} className="signal-pulse" style={{
              marginTop: 6, fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 8,
              backgroundColor: signalBgColor(sig), color: signalColor(sig),
            }}>
              {signalLabel(sig)}
            </span>
          )}
        </div>

        {holding && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SP.md }}>
              <div>
                <p style={styles.label}>ถืออยู่</p>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: COLORS.text }}>{holding.shares.toFixed(4)} หุ้น</p>
              </div>
              <div>
                <p style={styles.label}>สัดส่วน</p>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: COLORS.text }}>{weightPct != null ? `${weightPct.toFixed(1)}%` : '—'}</p>
              </div>
              <div>
                <p style={styles.label}>ต้นทุนเฉลี่ย/หุ้น</p>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: COLORS.text }}>{hideAmounts ? `$${MASK}` : fmtUSD(holding.avg_cost)}</p>
              </div>
              <div>
                <p style={styles.label}>ต้นทุนทั้งหมด</p>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: COLORS.text }}>{hideAmounts ? `$${MASK}` : fmtUSD(holding.shares * holding.avg_cost)}</p>
              </div>
            </div>
          </>
        )}

        {stock?.confidence != null && (
          <div>
            <p style={styles.label}>Confidence signal</p>
            <div style={{ width: '100%', height: 8, backgroundColor: 'rgba(148,163,184,0.15)', borderRadius: 6, overflow: 'hidden' }}>
              <div style={{ width: `${Math.round(stock.confidence * 100)}%`, height: '100%', backgroundColor: COLORS.purple, borderRadius: 6, transition: 'width 0.4s ease' }} />
            </div>
          </div>
        )}

        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: stock?.reasoning ? COLORS.text : COLORS.faint }}>
          เหตุผล: {stock?.reasoning || 'ยังไม่มีเหตุผลบันทึกไว้สำหรับหุ้นนี้ (รอรอบวิเคราะห์ถัดไป)'}
        </p>

        {stock && (
          <div style={{ borderTop: `1px solid ${COLORS.cardBorder}`, paddingTop: SP.md }}>
            <p style={{ ...styles.label, marginBottom: SP.sm }}>ข้อมูลเชิงลึก</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SP.md, marginBottom: SP.md }}>
              <div><p style={styles.label}>Market cap</p><p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: COLORS.text }}>{fmtMarketCap(stock.market_cap)}</p></div>
              <div><p style={styles.label}>P/E</p><p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: COLORS.text }}>{stock.pe_ratio != null ? (stock.pe_ratio < 0 ? '— (ยังไม่กำไร)' : stock.pe_ratio.toFixed(1)) : '—'}</p></div>
              <div><p style={styles.label}>EPS</p><p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: COLORS.text }}>{stock.eps != null ? `$${stock.eps.toFixed(2)}` : '—'}</p></div>
              <div><p style={styles.label}>PEG</p><p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: COLORS.text }}>{stock.peg_ratio != null ? stock.peg_ratio.toFixed(2) : '—'}</p></div>
              <div><p style={styles.label}>Beta</p><p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: COLORS.text }}>{stock.beta != null ? stock.beta.toFixed(2) : '—'}</p></div>
              <div><p style={styles.label}>52 สัปดาห์</p><p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: COLORS.text }}>{stock.week52_low != null && stock.week52_high != null ? `$${stock.week52_low.toFixed(2)} – $${stock.week52_high.toFixed(2)}` : '—'}</p></div>
            </div>

            {/* ✅ แนวรับไม้ 1-3 (S1/S2/S3) — เพิ่มตาม UI_Spec.md ยืนยันแล้วว่า backend มีข้อมูลจริง
                (หนุ่มคำนวณให้ทุกคืน, main.py /stocks expose เพิ่มแล้ว 2026-07-05) */}
            <div>
              <p style={{ ...styles.label, marginBottom: 6 }}>แนวรับ (ไม้ 1-3)</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: SP.sm }}>
                {[['ไม้ 1', stock.s1], ['ไม้ 2', stock.s2], ['ไม้ 3', stock.s3]].map(([label, val]) => (
                  <div key={label} style={{ padding: SP.sm, backgroundColor: 'rgba(148,163,184,0.08)', borderRadius: 10, textAlign: 'center' }}>
                    <p style={{ ...styles.label, marginBottom: 2, fontSize: 10 }}>{label}</p>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: COLORS.text }}>{val ? `$${Number(val).toFixed(2)}` : '—'}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div style={{ padding: SP.md, backgroundColor: 'rgba(148,163,184,0.08)', borderRadius: 10 }}>
          <p style={{ ...styles.label, marginBottom: 4 }}>วันประกาศงบ (เวลาไทย)</p>
          <p style={{ margin: 0, fontSize: 14, fontWeight: 700, color: COLORS.text }}>
            {stock?.earnings_date_thai && stock.earnings_date_thai !== '-' ? stock.earnings_date_thai : '- ยังไม่ประกาศกำหนดการ'}
          </p>
        </div>

        <div style={{ borderTop: `1px solid ${COLORS.cardBorder}`, paddingTop: SP.md }}>
          <p style={{ ...styles.label, marginBottom: 4 }}>เกี่ยวกับบริษัทนี้</p>
          {/* ✅ แก้ 2026-07-05 (รอบ 5): ต่อ field จริงจาก backend แล้ว (Finnhub /stock/profile2 +
              yfinance longBusinessSummary — ดู agents.py::_fetch_company_profile) รอ deploy + prefetch
              รอบแรกก่อนข้อมูลจะขึ้น ระหว่างนี้ fallback เป็นข้อความสถานะจริง ไม่แต่งเนื้อหาเอง */}
          <p style={{ margin: 0, fontSize: 12, lineHeight: 1.7, color: stock?.company_description ? COLORS.text : COLORS.faint }}>
            {stock?.company_description || 'ยังไม่มีข้อมูลคำอธิบายบริษัท (รอ deploy backend รอบล่าสุด + prefetch รอบถัดไป)'}
          </p>
        </div>

        {/* ✅ แก้ 2026-07-07: เดิมโชว์ปุ่มลบเสมอไม่ว่าจะถือหุ้นอยู่จริงหรือไม่ — MBBook ทักว่าหุ้นที่ถือ
            อยู่จริงไม่ควรมีปุ่ม "ลบออกจากรายการ" เพราะต้องขายก่อน ไม่ใช่ลบทิ้ง จึงโชว์ปุ่มนี้เฉพาะหุ้นที่
            ยังไม่ได้ถือ (แค่ติดตาม/สนใจ) เท่านั้น */}
        {!holding && (
          <div style={{ borderTop: `1px solid ${COLORS.cardBorder}`, paddingTop: SP.md }}>
            <button className="press-btn" onClick={() => openConfirmDeleteFromDetail(ticker)}
              style={btn('danger', { width: '100%', backgroundColor: 'transparent', border: `1px solid ${COLORS.red}`, color: COLORS.red })}>
              <Trash2 size={15} /> ลบหุ้นนี้ออกจากรายการติดตาม
            </button>
          </div>
        )}
      </div>
    );
  };

  const NEWS_SENTIMENT_COLOR = { Positive: COLORS.green, Negative: COLORS.red, Neutral: COLORS.muted };

  // ✅ แก้ 2026-07-05 (รอบ 7): เพิ่มขนาด font popup รายละเอียดข่าว — Desktop เพิ่มเยอะ, Mobile
  // เพิ่มแค่ ~2 ขนาด (เดิม popup นี้ใช้ค่าคงที่เดียวกันทั้ง 2 ฝั่ง ไม่เคยแยก isMobile มาก่อน)
  // ✅ แก้ 2026-07-05 (รอบ 9): MBBook ขอลดลง 2px (ยังใหญ่กว่ารอบ 6 เดิมอยู่ดี)
  const NewsDetailContent = ({ article }) => {
    if (!article) return null;
    const badgeFs = isMobile ? 12.5 : 17;
    return (
      <div style={styles.stack(SP.md)}>
        <div style={{ ...styles.row(SP.xs), flexWrap: 'wrap' }}>
          {article.tickers.map(t => (
            <span key={t} style={{ fontSize: badgeFs, fontWeight: 700, padding: '3px 10px', borderRadius: 7, backgroundColor: COLORS.purpleSoft, color: COLORS.purple }}>{t}</span>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: badgeFs, fontWeight: 700, padding: '3px 10px', borderRadius: 7, backgroundColor: `${NEWS_SENTIMENT_COLOR[article.sentiment]}22`, color: NEWS_SENTIMENT_COLOR[article.sentiment] }}>
            {article.sentiment}
          </span>
        </div>
        <h3 style={{ margin: 0, fontSize: isMobile ? 18 : 24, fontWeight: 700, color: COLORS.text, lineHeight: 1.5 }}>{article.headline}</h3>
        <div style={styles.row(SP.xs)}>
          <span style={{ fontSize: badgeFs, fontWeight: 700, padding: '3px 10px', borderRadius: 7, backgroundColor: `${NEWS_SENTIMENT_COLOR[article.sentiment]}22`, color: NEWS_SENTIMENT_COLOR[article.sentiment] }}>{article.sentiment}</span>
          <span style={{ fontSize: badgeFs, fontWeight: 700, padding: '3px 10px', borderRadius: 7, backgroundColor: 'rgba(245,196,107,0.16)', color: COLORS.gold }}>Impact: {article.impact}</span>
        </div>
        <p style={{ margin: 0, fontSize: isMobile ? 14.5 : 17, lineHeight: 1.8, color: COLORS.text }}>{article.body}</p>
        <p style={{ margin: 0, fontSize: isMobile ? 13 : 15, color: COLORS.faint }}>{article.date} · {article.source}</p>
      </div>
    );
  };

  // ===== POPUP MODAL WRAPPER (generic, FLIP-style expand from origin element) =====
  const popupTitle = () => {
    if (!popup) return '';
    if (popup.type === 'trade') return 'บันทึกการซื้อ-ขาย';
    if (popup.type === 'addTicker') return 'เพิ่มหุ้นใหม่';
    if (popup.type === 'confirmDelete') return 'ยืนยันการลบ';
    if (popup.type === 'stockDetail') return '';
    if (popup.type === 'newsDetail') return 'รายละเอียดข่าว';
    return '';
  };

  const PopupModal = () => {
    if (!popup) return null;
    const { phase, originRect, type, data } = popup;

    // ✅ แก้ 2026-07-05 (รอบ 7): popup ข่าวบน desktop กว้างขึ้น (480→620) เพราะเพิ่ม font ใหญ่ขึ้น
    // มากในรอบนี้ ความกว้างเดิมจะทำให้ headline ตัดบรรทัดถี่เกินไป
    const finalGeom = isMobile
      ? { top: '6vh', left: '4vw', width: '92vw', height: '88vh' }
      : { top: '50%', left: '50%', width: type === 'newsDetail' ? 620 : 480, maxHeight: '85vh' };

    const panelStyle = phase === 'opening'
      ? { position: 'fixed', top: originRect.top, left: originRect.left, width: originRect.width, height: originRect.height, borderRadius: 14, opacity: 0.5, overflow: 'hidden', transform: 'scale(0.95)', transition: 'none' }
      : {
          position: 'fixed', ...finalGeom,
          transform: isMobile ? (phase === 'closing' ? 'scale(0.92)' : 'scale(1)') : `translate(-50%,-50%) ${phase === 'closing' ? 'scale(0.92)' : 'scale(1)'}`,
          opacity: phase === 'closing' ? 0 : 1, borderRadius: 20, overflow: 'auto',
          transition: 'top 0.32s cubic-bezier(.34,1.56,.64,1), left 0.32s cubic-bezier(.34,1.56,.64,1), width 0.32s cubic-bezier(.34,1.56,.64,1), height 0.32s cubic-bezier(.34,1.56,.64,1), transform 0.32s cubic-bezier(.34,1.56,.64,1), opacity 0.26s ease',
        };

    const title = popupTitle();

    return (
      <div>
        <div className="modal-backdrop" onClick={closePopup} style={{ position: 'fixed', inset: 0, zIndex: 200, backgroundColor: 'rgba(5,7,20,0.6)', opacity: phase === 'closing' ? 0 : 1 }} />
        <div style={{ ...panelStyle, zIndex: 201, backgroundColor: '#111431', border: `1px solid ${COLORS.cardBorder}`, boxShadow: '0 20px 60px rgba(0,0,0,0.5)', padding: SP.xl }}>
          {title && (
            <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: SP.lg }}>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: COLORS.text }}>{title}</h3>
              <button className="icon-btn" onClick={closePopup} style={{ background: 'transparent', border: 'none', color: COLORS.muted, cursor: 'pointer', padding: 6, borderRadius: 10, display: 'flex' }}>
                <X size={20} />
              </button>
            </div>
          )}
          {type === 'stockDetail' && (
            <button className="icon-btn" onClick={closePopup} style={{ position: 'absolute', top: 18, right: 18, background: 'transparent', border: 'none', color: COLORS.muted, cursor: 'pointer', padding: 6, borderRadius: 10, display: 'flex' }}>
              <X size={20} />
            </button>
          )}

          {type === 'trade' && TradeFormContent()}
          {type === 'addTicker' && AddTickerContent()}
          {type === 'confirmDelete' && ConfirmDeleteContent({ ticker: data?.ticker })}
          {type === 'stockDetail' && StockDetailContent({ ticker: data?.ticker })}
          {type === 'newsDetail' && NewsDetailContent({ article: data?.article })}
        </div>
      </div>
    );
  };

  // ===== Shared small pieces (การ์ดหุ้น ใช้ทั้ง Tickers และ Portfolio holding) =====

  const HoldingCard = ({ h }) => {
    const isGain = h.gain >= 0;
    const stockInfo = stocks.find(s => s.ticker === h.ticker);
    const rate = portfolioData?.usd_thb_rate;
    // ✅ แก้บั๊ก 2026-07-05 (รอบ 4): เดิมโชว์ current_value (มูลค่ารวมทั้ง position) เป็นตัวเลขหลัก —
    // ผิด ต้องเป็นราคาต่อหุ้น (current_price) ตามรูปตัวอย่างที่ส่งมา (฿1,620 ≈$46.30 ต่อหุ้น ไม่ใช่รวม)
    const priceThb = rate != null ? h.current_price * rate : null;
    const gainThb = rate != null ? h.gain * rate : null;
    return (
      <div className="glass-row" onClick={(e) => openPopup('stockDetail', { ticker: h.ticker }, e.currentTarget)}
        style={{ ...styles.cardTight, ...styles.row(SP.md), justifyContent: 'space-between' }}>
        <div style={{ ...styles.row(SP.sm), minWidth: 0 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 12, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            backgroundColor: COLORS.purpleSoft, color: COLORS.purple, fontWeight: 800, fontSize: 13,
          }}>
            {h.ticker.slice(0, 2)}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={styles.row(SP.xs)}>
              <p style={{ fontSize: 17, fontWeight: 700, margin: 0, color: COLORS.text }}>{h.ticker}</p>
              {stockInfo?.signal && (
                <span key={stockInfo.signal} className="signal-pulse" style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 6, backgroundColor: signalBgColor(stockInfo.signal), color: signalColor(stockInfo.signal) }}>
                  {signalLabel(stockInfo.signal)}
                </span>
              )}
              {portfolioData?.total_value ? (
                <span style={{ fontSize: 12.5, color: COLORS.muted }}>{((h.current_value / portfolioData.total_value) * 100).toFixed(1)}%</span>
              ) : null}
            </div>
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          {MoneyDual({ thb: priceThb, usd: h.current_price, mainSize: 17 })}
          <p style={{ fontSize: 13, margin: '2px 0 0 0', color: isGain ? COLORS.green : COLORS.red, fontWeight: 600 }}>
            {isGain ? '↗ +' : '↘ '}{h.gain_pct.toFixed(1)}% {gainThb != null ? (hideAmounts ? `(฿${MASK})` : `(${isGain ? '+' : ''}${fmtTHB(gainThb)})`) : ''}
          </p>
        </div>
      </div>
    );
  };

  // ✅ แก้ 2026-07-09: MBBook ทักว่าปุ่มลบ (ถังขยะ) บนการ์ด ticker ไม่จำเป็น เพราะมีปุ่มลบใน popup
  // stockDetail อยู่แล้ว (gated ด้วย !holding ตาม comment ด้านบน) — ลบปุ่มซ้ำซ้อนนี้ทิ้ง ให้ลบได้
  // ทางเดียวคือผ่าน popup เท่านั้น
  const TickerCard = ({ stock }) => (
    <div className="glass-row" onClick={(e) => openPopup('stockDetail', { ticker: stock.ticker }, e.currentTarget)}
      style={{ ...styles.cardTight, ...styles.row(SP.md), justifyContent: 'space-between' }}>
      <div style={{ ...styles.row(SP.sm), minWidth: 0 }}>
        <div style={{ width: 40, height: 40, borderRadius: 12, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.purpleSoft, color: COLORS.purple, fontWeight: 800, fontSize: 13 }}>
          {stock.ticker.slice(0, 2)}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={styles.row(SP.xs)}>
            <p style={{ fontSize: 17, fontWeight: 700, margin: 0, color: COLORS.text }}>{stock.ticker}</p>
            <span key={stock.signal} className="signal-pulse" style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 6, backgroundColor: signalBgColor(stock.signal), color: signalColor(stock.signal) }}>
              {signalLabel(stock.signal)}
            </span>
          </div>
          {(stock.company_name || COMPANY_NAMES[stock.ticker]) && (
            <p style={{ fontSize: 12.5, margin: '2px 0 0 0', color: COLORS.faint }}>{stock.company_name || COMPANY_NAMES[stock.ticker]}</p>
          )}
          <p style={{ fontSize: 12.5, margin: '3px 0 0 0', color: COLORS.muted }}>
            conf. {stock.confidence != null ? `${(stock.confidence * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <p style={{ fontSize: 17, fontWeight: 700, margin: 0, color: COLORS.text }}>{fmtUSD(stock.price)}</p>
        {/* ✅ เพิ่ม 2026-07-09: column "เปลี่ยนแปลง" เดิมว่างเปล่า (ไม่มี field ให้ใช้) — ตอนนี้ backend
            ส่ง change_pct มาจาก signal_history แล้ว (ดู main.py::get_stocks) null ได้ถ้าข้อมูลยังไม่ถึง
            2 คืน (หุ้นเพิ่งเพิ่มเข้ามา) จึงต้องเช็ค != null ก่อนแสดง ไม่ใช่แค่ truthy (0% ก็ต้องแสดง) */}
        {stock.change_pct != null ? (
          <p style={{ fontSize: 13, fontWeight: 700, margin: '2px 0 0 0', color: stock.change_pct >= 0 ? COLORS.green : COLORS.red }}>
            {stock.change_pct >= 0 ? '▲' : '▼'} {Math.abs(stock.change_pct).toFixed(1)}%
          </p>
        ) : (
          <p style={{ fontSize: 12, margin: '2px 0 0 0', color: COLORS.faint }}>—</p>
        )}
      </div>
    </div>
  );

  // ===== PORTFOLIO TAB — Mobile กับ Desktop เป็นคนละ layout จริง (ไม่ใช่ breakpoint เดียวกัน) =====

  // ✅ 2026-07-08: Monthly/Yearly/Cumulative (อังกฤษ) ตาม mockup — ตัด Daily + date-range dropdown
  // ออก (ไม่มีช่วงให้เลือกแล้ว Monthly/Yearly มีช่วงตายตัว) Mobile กับ Desktop ใช้กราฟ % ชุดเดียวกันแล้ว
  const PORTFOLIO_PERIOD_OPTIONS = [
    { value: 'monthly', label: 'Monthly' }, { value: 'yearly', label: 'Yearly' }, { value: 'cumulative', label: 'Cumulative' },
  ];

  const MobileChartBlock = () => {
    const points = getChartPoints();
    return (
      <div style={styles.stack(SP.md)}>
        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', flexWrap: 'wrap' }}>
          {SlidingPill({ options: PORTFOLIO_PERIOD_OPTIONS, value: periodMode, onChange: setPeriodMode })}
        </div>
        {periodMode === 'cumulative' ? CumulativeLineChart({ points }) : BarChart({ points })}
      </div>
    );
  };

  // ⚠️ แก้ 2026-07-08: Desktop เคยตั้งใจให้โชว์มูลค่ารวม (฿) ต่างจาก Mobile แต่ mockup ล่าสุด (confirm
  // แล้ว) ให้ Desktop ใช้กราฟ % เหมือน Mobile ทุกประการ — MBBook ยืนยันให้เปลี่ยนตามนี้แล้ว
  const DesktopChartBlock = () => {
    const points = getChartPoints();
    return (
      <div style={{ ...styles.stack(SP.md), height: '100%' }}>
        <div style={{ ...styles.row(SP.md), justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <p style={styles.sectionTitle}>ผลตอบแทนพอร์ตตามช่วงเวลา</p>
          <div style={{ ...styles.row(SP.sm), flexWrap: 'wrap' }}>
            {SlidingPill({ options: PORTFOLIO_PERIOD_OPTIONS, value: periodMode, onChange: setPeriodMode })}
          </div>
        </div>
        {periodMode === 'cumulative' ? CumulativeLineChart({ points, fill: true }) : BarChart({ points, fill: true })}
      </div>
    );
  };

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 8): เพิ่ม badge/ข้อความ "สะสม"/"วันนี้"/"ROI" ตาม mockup
  // desktop = pill badge, mobile = ข้อความเล็กใต้ตัวเลข (ตามที่แต่ละ mockup แสดงจริง)
  // ✅ 2026-07-08: เพิ่ม `sidebar` — ใช้ตอนวางเป็นคอลัมน์ข้างกราฟ Desktop (portfolio-hero 70:30 ตาม
  // mockup) การ์ดนี้ต้อง "เป็น grid item ตัวเองโดยตรง" ไม่มี wrapper div ซ้อน แล้วให้ลูกใช้ flex:1
  // กระจายความสูง — ไม่ใช้ height:100% (percentage) เพราะเคยเจอบั๊กใน mockup ที่ height:100% ผ่าน div
  // ซ้อนชั้นแล้ว resolve ไม่ได้ผลจริง ทำให้เหลือช่องว่างว่างเปล่าด้านล่าง
  const PortfolioSummaryCards = ({ cols, desktop, sidebar }) => {
    const totalGain = portfolioData?.total_gain ?? 0;
    const rate = portfolioData?.usd_thb_rate;
    const dayChange = getPortfolioDayChange();
    const cumPct = getCumulativeReturnPct();
    const roi = portfolioData?.total_cost ? ((portfolioData.total_gain / portfolioData.total_cost) * 100) : null;
    const dayChangeThb = (dayChange && rate != null) ? dayChange.diffUsd * rate : null;

    // ✅ 2026-07-08: MBBook ทักว่า row แรก (กราฟ + 3 การ์ด) ในโหมด sidebar กินพื้นที่เยอะเกินไป —
    // เทียบกับ mockup ต้นฉบับ (.kpi-label 11.5px, .kpi-change padding 3px 9px font 11.5px, gap 10px)
    // การ์ดฝั่ง React ใหญ่กว่ามาก (label 13.5px, badge padding 4px 12px font 13px, gap 12px) ทำให้
    // คอลัมน์ KPI สูงกว่าที่ควร (การ์ดกราฟ fill:true เลยถูกลากให้สูงตามไปด้วย) ย่อเฉพาะโหมด sidebar
    // ให้ใกล้เคียง mockup ไม่กระทบ Mobile (sidebar=false ยังใช้ label/Badge ขนาดเดิม)
    const Badge = ({ text, color }) => (
      <span style={{ fontSize: sidebar ? 11.5 : 13, fontWeight: 700, padding: sidebar ? '3px 9px' : '4px 12px', borderRadius: 20, backgroundColor: `${color}22`, color }}>{text}</span>
    );

    const containerStyle = sidebar
      ? { display: 'flex', flexDirection: 'column', gap: 10 }
      : { display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: SP.md };
    const cardStyle = sidebar
      ? { ...styles.cardTight, padding: '14px 16px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }
      : styles.cardTight;
    const labelStyle = sidebar ? { ...styles.label, fontSize: 11.5, marginBottom: 6 } : styles.label;

    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <p style={labelStyle}>มูลค่ารวม</p>
          {MoneyDual({ thb: portfolioData?.total_value_thb, usd: portfolioData?.total_value, mainSize: sidebar ? 22 : (desktop ? 26 : 22), mainColor: COLORS.gold })}
          {desktop ? (
            <div style={{ ...styles.row(SP.xs), marginTop: sidebar ? 6 : SP.sm, flexWrap: 'wrap' }}>
              {cumPct != null && Badge({ text: `${cumPct >= 0 ? '+' : ''}${cumPct.toFixed(1)}% สะสม`, color: COLORS.green })}
              {dayChange && Badge({ text: `${dayChange.pct >= 0 ? '+' : ''}${dayChange.pct.toFixed(1)}% วันนี้`, color: dayChange.pct >= 0 ? COLORS.green : COLORS.red })}
            </div>
          ) : (
            (cumPct != null || dayChange) && (
              <p style={{ margin: '4px 0 0 0', fontSize: 12.5, color: COLORS.muted }}>
                {cumPct != null ? `${cumPct >= 0 ? '+' : ''}${cumPct.toFixed(1)}% สะสม` : ''}
                {dayChange ? ` · ${dayChange.pct >= 0 ? '+' : ''}${dayChange.pct.toFixed(1)}% วันนี้` : ''}
              </p>
            )
          )}
        </div>
        <div style={cardStyle}>
          <p style={labelStyle}>ต้นทุน</p>
          {MoneyDual({ thb: portfolioData?.total_cost_thb, usd: portfolioData?.total_cost, mainSize: desktop ? 21 : 18 })}
        </div>
        <div style={cardStyle}>
          <p style={labelStyle}>{desktop ? 'กำไรสุทธิ' : 'กำไร'}</p>
          {MoneyDual({ thb: portfolioData?.total_gain_thb, usd: totalGain, mainSize: desktop ? 21 : 18, mainColor: totalGain >= 0 ? COLORS.green : COLORS.red })}
          {desktop && (
            <div style={{ ...styles.row(SP.xs), marginTop: sidebar ? 6 : SP.sm, flexWrap: 'wrap' }}>
              {roi != null && Badge({ text: `ROI ${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`, color: COLORS.purple })}
              {dayChangeThb != null && Badge({ text: hideAmounts ? `฿${MASK} วันนี้` : `${dayChangeThb >= 0 ? '+' : ''}${fmtTHB(dayChangeThb)} วันนี้`, color: dayChangeThb >= 0 ? COLORS.green : COLORS.red })}
            </div>
          )}
        </div>
      </div>
    );
  };

  const PortfolioFooterBar = ({ holdings }) => {
    const winCount = holdings.filter(h => h.gain >= 0).length;
    const lossCount = holdings.length - winCount;
    const roi = portfolioData?.total_cost ? ((portfolioData.total_gain / portfolioData.total_cost) * 100) : 0;
    return (
      <div style={{ ...styles.cardTight, display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: SP.md }}>
        <div><p style={styles.label}>ทั้งหมด</p><p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: COLORS.text }}>{holdings.length}</p></div>
        <div><p style={styles.label}>กำไร/ขาดทุน</p><p style={{ margin: 0, fontSize: 16, fontWeight: 700 }}><span style={{ color: COLORS.green }}>{winCount}</span><span style={{ color: COLORS.muted }}>/</span><span style={{ color: COLORS.red }}>{lossCount}</span></p></div>
        <div><p style={styles.label}>ROI รวม</p><p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: COLORS.purple }}>{roi >= 0 ? '+' : ''}{roi.toFixed(1)}%</p></div>
      </div>
    );
  };

  const PortfolioActionRow = () => (
    <div style={styles.row(SP.sm)}>
      <button className="press-btn" style={btn('ghost', { flex: 1 })}><Filter size={15} /> กรอง</button>
      <button className="press-btn" style={btn('ghost', { flex: 1 })}><ArrowUpDown size={15} /> เรียง</button>
      <button className="clay-btn" onClick={(e) => openPopup('trade', null, e.currentTarget)}
        style={clayGoldStyle({ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: SP.xs, padding: isMobile ? '13px' : '10px', fontSize: 14 })}>
        <Plus size={16} /> Trade
      </button>
    </div>
  );

  const MobilePortfolio = () => {
    const holdings = portfolioData?.holdings ?? [];
    return (
      <div style={styles.stack(SP.lg)}>
        <div>
          <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800, color: COLORS.text }}>Portfolio Analytics</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: 12, color: COLORS.muted }}>{stocks.length} หุ้น · THB/USD · อัปเดตล่าสุดชั่วโมงที่แล้ว</p>
        </div>
        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, fontWeight: 700, padding: '4px 12px', borderRadius: 20, backgroundColor: (portfolioData?.total_gain ?? 0) >= 0 ? COLORS.greenSoft : COLORS.redSoft, color: (portfolioData?.total_gain ?? 0) >= 0 ? COLORS.green : COLORS.red }}>
            {(portfolioData?.total_gain ?? 0) >= 0 ? 'พอร์ตบวกวันนี้' : 'พอร์ตติดลบวันนี้'}
          </span>
          <span style={{ fontSize: 12, color: COLORS.muted }}>ณ {new Date().toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
        </div>

        {MobileChartBlock()}
        {PortfolioSummaryCards({ cols: 1 })}

        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between' }}>
          <h3 style={{ ...styles.sectionTitle }}>หุ้นที่ถืออยู่</h3>
          <span style={{ fontSize: 12, color: COLORS.muted }}>{holdings.length} ตำแหน่ง</span>
        </div>
        {PortfolioActionRow()}

        <div style={styles.stack(SP.sm)}>
          {holdings.map(h => <div key={h.ticker}>{HoldingCard({ h })}</div>)}
        </div>
        {portfolioData && holdings.length === 0 && (
          <div style={{ ...styles.card, textAlign: 'center', color: COLORS.muted, fontSize: 13 }}>ยังไม่มีการถือครองหุ้น — กด "+ Trade" เพื่อบันทึกรายการแรก</div>
        )}
        {holdings.length > 0 && PortfolioFooterBar({ holdings })}
      </div>
    );
  };

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 1): กลับไปใช้ตารางตาม mockup 100% ตามที่ MBBook ยืนยัน
  // (ก่อนหน้านี้เคยเปลี่ยนเป็นการ์ดไปแล้วรอบก่อน แต่ mockup ล่าสุดยืนยันให้ใช้ตารางจริง)
  const HOLDINGS_TABLE_COLS = '2.2fr 1fr 1fr 1.2fr 1.2fr 1.2fr';
  const HoldingsTable = ({ holdings }) => {
    const rate = portfolioData?.usd_thb_rate;
    return (
      <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'grid', gridTemplateColumns: HOLDINGS_TABLE_COLS, gap: SP.sm, padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${COLORS.cardBorder}` }}>
          {['สินทรัพย์', 'จำนวนหุ้น', 'ต้นทุน/หุ้น', 'ต้นทุนทั้งหมด', 'ราคาปัจจุบัน', 'เปลี่ยนแปลง'].map((h, i) => (
            <span key={h} style={{ fontSize: 13, fontWeight: 600, color: COLORS.faint, textAlign: i === 0 ? 'left' : 'right' }}>{h}</span>
          ))}
        </div>
        {holdings.map(h => {
          const isGain = h.gain >= 0;
          const stockInfo = stocks.find(s => s.ticker === h.ticker);
          const priceThb = rate != null ? h.current_price * rate : null;
          const gainThb = rate != null ? h.gain * rate : null;
          return (
            <div key={h.ticker} className="glass-row" onClick={(e) => openPopup('stockDetail', { ticker: h.ticker }, e.currentTarget)}
              style={{ display: 'grid', gridTemplateColumns: HOLDINGS_TABLE_COLS, gap: SP.sm, alignItems: 'center', padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${COLORS.cardBorder}` }}>
              <div style={styles.row(SP.sm)}>
                <div style={{ width: 38, height: 38, borderRadius: 10, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.purpleSoft, color: COLORS.purple, fontWeight: 800, fontSize: 13 }}>
                  {h.ticker.slice(0, 2)}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={styles.row(SP.xs)}>
                    <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.text }}>{h.ticker}</span>
                    {stockInfo?.signal && (
                      <span key={stockInfo.signal} className="signal-pulse" style={{ fontSize: 11, fontWeight: 700, padding: '2px 7px', borderRadius: 6, backgroundColor: signalBgColor(stockInfo.signal), color: signalColor(stockInfo.signal) }}>
                        {signalLabel(stockInfo.signal)}
                      </span>
                    )}
                  </div>
                  {portfolioData?.total_value ? (
                    <span style={{ fontSize: 13, color: COLORS.muted }}>{((h.current_value / portfolioData.total_value) * 100).toFixed(1)}%</span>
                  ) : null}
                </div>
              </div>
              <span style={{ fontSize: 15, color: COLORS.text, textAlign: 'right' }}>{h.shares.toFixed(2)}</span>
              <span style={{ fontSize: 15, color: COLORS.text, textAlign: 'right' }}>{hideAmounts ? `$${MASK}` : fmtUSD(h.avg_cost)}</span>
              <span style={{ fontSize: 15, color: COLORS.text, textAlign: 'right' }}>{hideAmounts ? `$${MASK}` : fmtUSD(h.shares * h.avg_cost)}</span>
              <div style={{ textAlign: 'right' }}>
                <p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: COLORS.text }}>{hideAmounts ? `฿${MASK}` : (priceThb != null ? fmtTHB(priceThb) : fmtUSD(h.current_price))}</p>
                <p style={{ margin: 0, fontSize: 13, color: COLORS.muted }}>{hideAmounts ? `$${MASK}` : fmtUSD(h.current_price)}</p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: isGain ? COLORS.green : COLORS.red }}>{isGain ? '↗ +' : '↘ '}{h.gain_pct.toFixed(1)}%</p>
                {gainThb != null && <p style={{ margin: 0, fontSize: 13, color: isGain ? COLORS.green : COLORS.red }}>{hideAmounts ? `(฿${MASK})` : `(${isGain ? '+' : ''}${fmtTHB(gainThb)})`}</p>}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const DesktopPortfolio = () => {
    const holdings = portfolioData?.holdings ?? [];
    return (
      <div style={styles.stack(SP.xl)}>
        <div style={{ ...styles.row(SP.md), justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: COLORS.text }}>Portfolio</h2>
            <p style={{ margin: '4px 0 0 0', fontSize: 14, color: COLORS.muted }}>{stocks.length} หุ้น · THB/USD · อัปเดตล่าสุดชั่วโมงที่แล้ว</p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: 13, fontWeight: 700, padding: '5px 13px', borderRadius: 20, backgroundColor: (portfolioData?.total_gain ?? 0) >= 0 ? COLORS.greenSoft : COLORS.redSoft, color: (portfolioData?.total_gain ?? 0) >= 0 ? COLORS.green : COLORS.red }}>
              {(portfolioData?.total_gain ?? 0) >= 0 ? 'พอร์ตบวกวันนี้' : 'พอร์ตติดลบวันนี้'}
            </span>
            <p style={{ margin: '6px 0 0 0', fontSize: 13, color: COLORS.muted }}>ณ {new Date().toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
          </div>
        </div>

        {/* ✅ 2026-07-08: portfolio-hero ตาม mockup — กราฟ+KPI cards เคียงกัน 70:30 (เดิมเรียงต่อกัน
            เต็มความกว้างทั้งคู่) alignItems:'stretch' (ค่า default ของ grid อยู่แล้ว แต่ระบุไว้ชัดๆ)
            ทำให้ 2 คอลัมน์สูงเท่ากันเสมอ โดย PortfolioSummaryCards(sidebar:true) เป็น grid item ตรงๆ
            ไม่มี wrapper ซ้อน (ดู comment ที่ตัว component) */}
        <div style={{ display: 'grid', gridTemplateColumns: '2.3fr 1fr', gap: SP.lg, alignItems: 'stretch' }}>
          {DesktopChartBlock()}
          {PortfolioSummaryCards({ cols: 1, desktop: true, sidebar: true })}
        </div>

        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between' }}>
          <h3 style={{ ...styles.sectionTitle, fontSize: 19 }}>หุ้นที่ถืออยู่</h3>
          <div style={{ ...styles.row(SP.md) }}>
            <span style={{ fontSize: 14, color: COLORS.muted }}>{holdings.length} ตำแหน่ง</span>
            {PortfolioActionRow()}
          </div>
        </div>

        {holdings.length > 0 ? HoldingsTable({ holdings }) : (portfolioData && (
          <div style={{ ...styles.card, textAlign: 'center', color: COLORS.muted, fontSize: 14 }}>ยังไม่มีการถือครองหุ้น — กด "+ Trade" เพื่อบันทึกรายการแรก</div>
        ))}
        {holdings.length > 0 && PortfolioFooterBar({ holdings })}
      </div>
    );
  };

  // ===== TICKERS TAB — ทั้ง mobile/desktop ใช้การ์ด ต่างกันแค่จำนวนคอลัมน์ =====

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 1): กลับ header เต็ม "หุ้นที่จับตามอง" ตาม mockup 100%
  // (ก่อนหน้านี้เคยย่อเป็น "Tickers" ไปแล้วรอบก่อน) ปุ่มเพิ่ม: desktop = ตัวหนังสือ, mobile = ไอคอนอย่างเดียว
  const TickersHeader = ({ desktop }) => (
    <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between' }}>
      <div>
        <h2 style={{ margin: 0, fontSize: isMobile ? 19 : 24, fontWeight: 800, color: COLORS.text }}>หุ้นที่จับตามอง</h2>
        <p style={{ margin: '4px 0 0 0', fontSize: isMobile ? 12 : 13.5, color: COLORS.muted }}>{stocks.length} / {MAX_TICKERS} ตัว · ราคาอัปเดตทุกชั่วโมง</p>
      </div>
      {desktop ? (
        <button className="clay-btn" onClick={(e) => openPopup('addTicker', null, e.currentTarget)}
          style={clayGoldStyle({ padding: '10px 18px', display: 'flex', alignItems: 'center', gap: SP.xs, fontSize: 14, flexShrink: 0 })}>
          <Plus size={16} strokeWidth={2.5} /> เพิ่มหุ้น
        </button>
      ) : (
        <button className="clay-btn" onClick={(e) => openPopup('addTicker', null, e.currentTarget)}
          style={clayGoldStyle({ width: 42, height: 42, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 })} aria-label="เพิ่มหุ้น">
          <Plus size={20} strokeWidth={2.5} />
        </button>
      )}
    </div>
  );

  const MobileTickers = () => (
    <div style={styles.stack(SP.lg)}>
      {TickersHeader({ desktop: false })}
      <div style={{ position: 'relative' }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: COLORS.faint }} />
        <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="ค้นหาหุ้น..." style={{ ...styles.input, paddingLeft: 38 }} />
      </div>
      <div style={styles.stack(SP.sm)}>
        {filteredStocks.map(stock => <div key={stock.ticker}>{TickerCard({ stock })}</div>)}
        {filteredStocks.length === 0 && <p style={{ color: COLORS.faint, fontSize: 13, textAlign: 'center', padding: SP.lg }}>ไม่พบหุ้นที่ค้นหา</p>}
      </div>
    </div>
  );

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 1): Desktop กลับไปใช้ตารางตาม mockup 100%
  const TICKERS_TABLE_COLS = '2.4fr 1fr 1.2fr 1fr';
  // ✅ แก้ 2026-07-09: ลบปุ่มถังขยะซ้ำซ้อนออกเช่นเดียวกับ TickerCard ด้านบน — ลบได้ทางเดียวคือผ่าน
  // popup stockDetail เท่านั้น
  const TickersTable = () => (
    <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
      <div style={{ display: 'grid', gridTemplateColumns: TICKERS_TABLE_COLS, gap: SP.sm, padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${COLORS.cardBorder}` }}>
        {['หุ้น', 'Confidence', 'ราคาปัจจุบัน', 'เปลี่ยนแปลง'].map((h, i) => (
          <span key={h} style={{ fontSize: 13, fontWeight: 600, color: COLORS.faint, textAlign: i === 0 ? 'left' : 'right' }}>{h}</span>
        ))}
      </div>
      {filteredStocks.map(stock => (
        <div key={stock.ticker} className="glass-row" onClick={(e) => openPopup('stockDetail', { ticker: stock.ticker }, e.currentTarget)}
          style={{ display: 'grid', gridTemplateColumns: TICKERS_TABLE_COLS, gap: SP.sm, alignItems: 'center', padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${COLORS.cardBorder}` }}>
          <div style={styles.row(SP.sm)}>
            <div style={{ width: 38, height: 38, borderRadius: 10, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.purpleSoft, color: COLORS.purple, fontWeight: 800, fontSize: 13 }}>
              {stock.ticker.slice(0, 2)}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={styles.row(SP.xs)}>
                <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.text }}>{stock.ticker}</span>
                <span key={stock.signal} className="signal-pulse" style={{ fontSize: 11, fontWeight: 700, padding: '2px 7px', borderRadius: 6, backgroundColor: signalBgColor(stock.signal), color: signalColor(stock.signal) }}>
                  {signalLabel(stock.signal)}
                </span>
              </div>
              {(stock.company_name || COMPANY_NAMES[stock.ticker]) && <span style={{ fontSize: 13, color: COLORS.faint }}>{stock.company_name || COMPANY_NAMES[stock.ticker]}</span>}
            </div>
          </div>
          <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.purple, textAlign: 'right' }}>
            {stock.confidence != null ? `${(stock.confidence * 100).toFixed(0)}%` : '—'}
          </span>
          <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.text, textAlign: 'right' }}>{fmtUSD(stock.price)}</span>
          {/* ✅ เพิ่ม 2026-07-09: เติม column "เปลี่ยนแปลง" (เดิมว่างเปล่า) — ดู comment เดียวกันใน TickerCard */}
          <span style={{ fontSize: 16, fontWeight: 700, textAlign: 'right', color: stock.change_pct == null ? COLORS.faint : stock.change_pct >= 0 ? COLORS.green : COLORS.red }}>
            {stock.change_pct != null ? `${stock.change_pct >= 0 ? '▲' : '▼'} ${Math.abs(stock.change_pct).toFixed(1)}%` : '—'}
          </span>
        </div>
      ))}
      {filteredStocks.length === 0 && <p style={{ color: COLORS.faint, fontSize: 13, textAlign: 'center', padding: SP.lg }}>ไม่พบหุ้นที่ค้นหา</p>}
    </div>
  );

  const DesktopTickers = () => (
    <div style={styles.stack(SP.xl)}>
      {TickersHeader({ desktop: true })}
      <div style={{ position: 'relative', maxWidth: 360 }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: COLORS.faint }} />
        <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="ค้นหาหุ้น..." style={{ ...styles.input, paddingLeft: 38 }} />
      </div>
      {TickersTable()}
    </div>
  );

  // ===== NEWS TAB =====

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 1): กลับ header เต็ม "ข่าวหุ้น" + subtitle ตาม mockup 100%
  // (ก่อนหน้านี้เคยย่อเป็น "News" ไปแล้วรอบก่อน) desktop subtitle เพิ่มจำนวนข่าวต่อท้ายด้วย
  // ✅ แก้ 2026-07-05 (รอบ 7): MBBook ขอเพิ่มขนาดตัวหนังสือหน้า News อีก — Desktop เพิ่มเยอะ,
  // Mobile เพิ่มแค่ ~2 ขนาด (ทั้งหน้า list และ popup รายละเอียดข่าว)
  // ✅ แก้ 2026-07-05 (รอบ 9): MBBook ขอลดลง 2px ทั้งหน้า (ยังใหญ่กว่ารอบ 6 เดิมอยู่ดี) + เพิ่มปุ่ม
  // "อ่านทั้งหมด" มุมขวาบนของ header (เผื่อระบบข่าวจริงต่อเสร็จแล้วมีเป็นร้อยข่าว ไม่ต้องกด popup ทีละอัน)
  const NewsHeader = ({ desktop }) => {
    const allNews = getAllNews();
    const unreadCount = allNews.filter(a => !readNewsIds.has(a.id)).length;
    return (
      <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: isMobile ? 19 : 27, fontWeight: 800, color: COLORS.text }}>ข่าวหุ้น</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: isMobile ? 12 : 15, color: COLORS.muted }}>
            สรุปข่าวย้อนหลัง 7 วัน · วิเคราะห์โดยนัตตี้{desktop ? ` · ${allNews.length} ข่าว` : ''}
          </p>
        </div>
        <div style={{ ...styles.row(SP.xs), flexWrap: 'wrap' }}>
          {/* ✅ เพิ่ม 2026-07-05 (รอบ 10): ปุ่มทดสอบชั่วคราว — จำลองข่าวใหม่เข้ามาเพื่อเช็คป้าย New +
              ปุ่มอ่านทั้งหมด ลบทิ้งได้พร้อม MOCK_NEWS ตอนต่อ backend ข่าวจริง (#51) */}
          <button className="press-btn" onClick={addTestNews}
            style={btn('outline', { fontSize: isMobile ? 12 : 13, padding: isMobile ? '8px 12px' : '9px 14px', minHeight: 'auto' })}>
            <Plus size={isMobile ? 14 : 15} /> ข่าวทดสอบ
          </button>
          {unreadCount > 0 && (
            <button className="press-btn" onClick={markAllNewsRead}
              style={btn('ghost', { fontSize: isMobile ? 12 : 13, padding: isMobile ? '8px 12px' : '9px 14px', minHeight: 'auto' })}>
              <Check size={isMobile ? 14 : 15} /> อ่านทั้งหมด
            </button>
          )}
        </div>
      </div>
    );
  };

  const NewsPagination = () => {
    const totalNews = getAllNews().length;
    const totalPages = Math.max(Math.ceil(totalNews / NEWS_PAGE_SIZE), 1);
    const startIdx = (newsPage - 1) * NEWS_PAGE_SIZE + 1;
    const endIdx = Math.min(newsPage * NEWS_PAGE_SIZE, totalNews);
    const btnSize = isMobile ? 32 : 38;
    return (
      <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <span style={{ fontSize: isMobile ? 12 : 15, color: COLORS.muted }}>แสดงข่าวที่ {startIdx}–{endIdx} จาก {totalNews} ข่าว</span>
        <div style={styles.row(SP.xs)}>
          <button className="icon-btn" disabled={newsPage === 1} onClick={() => setNewsPage(p => Math.max(1, p - 1))}
            style={{ width: btnSize, height: btnSize, borderRadius: '50%', border: `1px solid ${COLORS.cardBorder}`, backgroundColor: 'transparent', color: COLORS.text, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: newsPage === 1 ? 'default' : 'pointer', opacity: newsPage === 1 ? 0.4 : 1 }}>
            <ChevronLeft size={isMobile ? 14 : 17} />
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
            <button key={n} className="pill-btn" onClick={() => setNewsPage(n)} style={{
              width: btnSize, height: btnSize, borderRadius: '50%', border: n === newsPage ? 'none' : `1px solid ${COLORS.cardBorder}`,
              backgroundColor: n === newsPage ? COLORS.purple : 'transparent', color: n === newsPage ? '#fff' : COLORS.muted,
              fontSize: isMobile ? 13 : 16, fontWeight: 700, cursor: 'pointer',
            }}>
              {n}
            </button>
          ))}
          <button className="icon-btn" disabled={newsPage === totalPages} onClick={() => setNewsPage(p => Math.min(totalPages, p + 1))}
            style={{ width: btnSize, height: btnSize, borderRadius: '50%', border: `1px solid ${COLORS.cardBorder}`, backgroundColor: 'transparent', color: COLORS.text, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: newsPage === totalPages ? 'default' : 'pointer', opacity: newsPage === totalPages ? 0.4 : 1 }}>
            <ChevronRight size={isMobile ? 14 : 17} />
          </button>
        </div>
      </div>
    );
  };

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 1): footer แถวเดียว (วันที่·source ซ้าย + Impact ขวา) ตาม
  // mockup 100% (ก่อนหน้านี้ Impact แยกเป็นแถวของตัวเอง) + เพิ่ม snippet เนื้อหาสั้นๆ ใต้ headline
  // ✅ แก้ 2026-07-05 (รอบ 8): เพิ่มป้าย "New" สีทองสำหรับข่าวที่ยังไม่เคยถูกคลิกเปิด popup — คลิกครั้ง
  // แรกจะ mark ว่าอ่านแล้วทันที (markNewsRead) ป้ายจะหายไปตั้งแต่ re-render ถัดไป
  const NewsCard = ({ article }) => {
    const snippet = article.body.length > 90 ? article.body.slice(0, 90).trim() + '...' : article.body;
    const isNew = !readNewsIds.has(article.id);
    return (
      <div className="glass-row" onClick={(e) => { markNewsRead(article.id); openPopup('newsDetail', { article }, e.currentTarget); }} style={styles.cardTight}>
        <div style={{ ...styles.row(SP.xs), marginBottom: SP.sm, flexWrap: 'wrap' }}>
          {isNew && (
            <span style={{ fontSize: isMobile ? 10 : 15, fontWeight: 800, padding: '3px 10px', borderRadius: 6, backgroundColor: 'rgba(245,196,107,0.16)', color: COLORS.gold }}>New</span>
          )}
          {article.tickers.map(t => (
            <span key={t} style={{ fontSize: isMobile ? 10 : 15, fontWeight: 700, padding: '3px 10px', borderRadius: 6, backgroundColor: COLORS.purpleSoft, color: COLORS.purple }}>{t}</span>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: isMobile ? 10 : 15, fontWeight: 700, padding: '3px 10px', borderRadius: 6, backgroundColor: `${NEWS_SENTIMENT_COLOR[article.sentiment]}22`, color: NEWS_SENTIMENT_COLOR[article.sentiment] }}>{article.sentiment}</span>
        </div>
        <p style={{ margin: '0 0 4px 0', fontSize: isMobile ? 14 : 19, fontWeight: 700, color: COLORS.text, lineHeight: 1.5 }}>{article.headline}</p>
        <p style={{ margin: '0 0 8px 0', fontSize: isMobile ? 12 : 16, color: COLORS.muted, lineHeight: 1.6 }}>{snippet}</p>
        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between' }}>
          <span style={{ fontSize: isMobile ? 11 : 15, color: COLORS.faint }}>{article.date} · {article.source}</span>
          <span style={{ fontSize: isMobile ? 11 : 15, fontWeight: 700, color: COLORS.gold }}>Impact: {article.impact}</span>
        </div>
      </div>
    );
  };

  // ✅ แก้ 2026-07-05 (รอบ 4): เรียงการ์ดข่าวเป็น 1 คอลัมน์เสมอ (ทั้ง mobile/desktop) ตามที่ MBBook
  // ยืนยันว่าเรียงซ้าย-ขวาแบบ grid หลายคอลัมน์ทำให้ลายตา ต้องการแบบเรียง 1-1 row เท่านั้น
  // ✅ แก้ 2026-07-05 (รอบ 8): sort ตาม timestamp ใหม่→เก่าเสมอ (ไม่พึ่งลำดับ array เดิม) ตามที่
  // MBBook ขอ — ข่าวล่าสุดต้องอยู่บนสุดเสมอ แม้จะมีข่าวใหม่แทรกเข้ามาระหว่างที่อ่านค้างอยู่หน้าอื่นก็ตาม
  const NewsList = () => {
    const sorted = getAllNews().sort((a, b) => b.timestamp - a.timestamp);
    const start = (newsPage - 1) * NEWS_PAGE_SIZE;
    const pageItems = sorted.slice(start, start + NEWS_PAGE_SIZE);
    return (
      <div style={styles.stack(SP.sm)}>
        {pageItems.map(a => <div key={a.id}>{NewsCard({ article: a })}</div>)}
      </div>
    );
  };

  const MobileNews = () => (
    <div style={styles.stack(SP.lg)}>
      {NewsHeader({ desktop: false })}
      {NewsList()}
      {NewsPagination()}
    </div>
  );

  const DesktopNews = () => (
    <div style={styles.stack(SP.xl)}>
      {NewsHeader({ desktop: true })}
      {NewsList()}
      {NewsPagination()}
    </div>
  );

  // ===== SYSTEM TAB (ไม่มีแก้ไข ใช้ตามที่ confirm แล้ว) =====

  // ✅ แก้ 2026-07-05 (รอบ 5, Finding 2/3/4/5): restructure ทั้งแท็บตาม mockup 100% —
  // ตัด "รายงานตลาดย้อนหลัง" + budget bar เดิม (ไม่มีใน mockup ใหม่เลย ตาม Finding 5 ที่ MBBook
  // ยืนยันให้ตัดออก), เพิ่ม subtitle, กราฟต้นทุนมี period/date-range เหมือน Portfolio, win-rate
  // มีแถบ + ขีดเป้าหมาย, นิกเป็นตารางบน desktop
  const WinRateBar = ({ pct, target, meets }) => {
    const barColor = meets ? COLORS.green : COLORS.red;
    const targetPos = Math.min(Math.max(target, 0), 100);
    return (
      <div style={{ position: 'relative', width: '100%', height: 8, backgroundColor: 'rgba(148,163,184,0.15)', borderRadius: 6, marginTop: SP.sm }}>
        <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', backgroundColor: barColor, borderRadius: 6, transition: 'width 0.4s ease' }} />
        <div style={{ position: 'absolute', top: -2, left: `${targetPos}%`, width: 2, height: 12, backgroundColor: COLORS.gold, borderRadius: 1 }} />
      </div>
    );
  };

  // ✅ 2026-07-08: เพิ่ม `fill` — ใช้ตอน Desktop sys-grid (การ์ดกราฟต้นทุน+การ์ด Win Rate เคียงกัน)
  // ให้การ์ดนี้ flex:1 กระจายเต็มความสูงคอลัมน์ ตาม mockup fix (ปกติไม่ fill เพราะ Mobile วางแบบ grid
  // 2 คอลัมน์ ไม่ต้องยืดสูง)
  const WinRateCard = ({ label, r, showLabel = true, fill }) => {
    const wr = r?.win_rate_pct;
    const target = r?.win_rate_target_pct ?? 75;
    const meets = r?.meets_win_target;
    const delta = wr != null ? Math.round(wr - target) : null;
    const cardStyle = fill ? { ...styles.cardTight, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' } : styles.cardTight;
    return (
      <div style={cardStyle}>
        {showLabel && <p style={styles.label}>{label} (เป้า {target}%)</p>}
        {wr != null ? (
          <>
            <p style={{ fontSize: isMobile ? 26 : 30, fontWeight: 800, margin: 0, color: meets ? COLORS.green : COLORS.red }}>{wr}%</p>
            {WinRateBar({ pct: wr, target, meets })}
            <p style={{ fontSize: isMobile ? 12 : 13.5, margin: '6px 0 0 0', color: meets ? COLORS.green : COLORS.red }}>
              {delta >= 0 ? `ผ่านเป้า +${delta}%` : `ต่ำกว่าเป้า ${Math.abs(delta)}%`}
            </p>
          </>
        ) : (
          <p style={{ fontSize: 14, margin: '8px 0 0 0', color: COLORS.faint }}>ยังไม่มีสัญญาณครบอายุพอให้คำนวณ</p>
        )}
      </div>
    );
  };

  // ✅ เพิ่ม 2026-07-05 (รอบ 6): MBBook ขอให้กราฟ "สะสม" ทุกจุดในแอปเป็นกราฟเส้น (ไล่ซ้าย→ขวา,
  // เส้นขึ้น, มีค่าบอกปลายเส้น) เหมือน CumulativeLineChart ของ Portfolio — ทำแบบเดียวกันสำหรับ
  // ต้นทุนระบบ ต่างกันแค่ label ปลายเส้นเป็น "$" ไม่ใช่ "%" เพราะต้นทุนสะสมเป็นตัวเงินจริง ไม่มี
  // ฐาน % ให้เทียบ (ถ้า MBBook อยากได้ % เทียบงบ ให้บอกเพิ่มได้ เดี๋ยวปรับ)
  const CostCumulativeLineChart = ({ points }) => {
    if (!points || points.length === 0) {
      return <div style={{ ...styles.cardTight, textAlign: 'center', color: COLORS.faint, fontSize: 13 }}>ยังไม่มีข้อมูลสะสม</div>;
    }
    const W = 600, H = 180, PAD = 24;
    const vals = points.map(p => p.cost_usd);
    const min = Math.min(...vals, 0), max = Math.max(...vals, 0);
    const range = (max - min) || 1;
    const stepX = (W - PAD * 2) / Math.max(points.length - 1, 1);
    const coords = points.map((p, i) => {
      const x = PAD + i * stepX;
      const y = H - PAD - ((p.cost_usd - min) / range) * (H - PAD * 2);
      return [x, y];
    });
    const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c[0].toFixed(1)} ${c[1].toFixed(1)}`).join(' ');
    const last = points[points.length - 1];
    const lastCoord = coords[coords.length - 1];
    return (
      <div style={{ height: 200 }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%', overflow: 'visible' }} preserveAspectRatio="none">
          <path d={path} fill="none" stroke={COLORS.purple} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="line-draw" vectorEffect="non-scaling-stroke" />
          <circle cx={lastCoord[0]} cy={lastCoord[1]} r={4} fill={COLORS.gold} />
          <text x={Math.max(lastCoord[0] - 50, 0)} y={Math.max(lastCoord[1] - 10, 14)} fontSize="15" fontWeight="700" fill={COLORS.gold}>
            ${last.cost_usd.toFixed(2)}
          </text>
        </svg>
      </div>
    );
  };

  const CostChartCard = ({ desktop }) => {
    const points = getCostChartPoints();
    const total7d = points.reduce((sum, p) => sum + p.cost_usd, 0);
    const avgPerDay = points.length ? total7d / points.length : 0;
    const maxCost = Math.max(...points.map(p => p.cost_usd), 0.01);
    return (
      <div style={styles.card}>
        <div style={{ ...styles.row(SP.md), justifyContent: 'space-between', flexWrap: 'wrap', marginBottom: SP.md }}>
          <p style={styles.sectionTitle}>ต้นทุนระบบ (Token cost)</p>
          <div style={{ ...styles.row(SP.sm), flexWrap: 'wrap' }}>
            {SlidingPill({
              options: [{ value: 'daily', label: 'Daily' }, { value: 'monthly', label: 'Monthly' }, { value: 'cumulative', label: 'Cumulative' }],
              value: costPeriodMode, onChange: setCostPeriodMode,
            })}
            {costPeriodMode !== 'cumulative' && CostDateRangeDropdown()}
          </div>
        </div>
        {points.length === 0 ? (
          <p style={{ color: COLORS.faint, fontSize: 14, textAlign: 'center', padding: SP.lg, margin: 0 }}>ยังไม่มีข้อมูลต้นทุนในช่วงที่เลือก</p>
        ) : costPeriodMode === 'cumulative' ? (
          CostCumulativeLineChart({ points })
        ) : (
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: isMobile ? 6 : 10, height: 160, overflowX: 'auto' }}>
            {points.map(p => (
              <div key={p.period} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: '1 0 auto', minWidth: isMobile ? 32 : 46, height: '100%', justifyContent: 'flex-end' }}>
                <span style={{ fontSize: isMobile ? 10 : 12, fontWeight: 700, color: COLORS.gold, marginBottom: 4, whiteSpace: 'nowrap' }}>${p.cost_usd.toFixed(2)}</span>
                <div className="chart-bar" style={{ width: isMobile ? 20 : 30, height: `${Math.max((p.cost_usd / maxCost) * 100, 4)}%`, minHeight: 6, borderRadius: 6, background: `linear-gradient(180deg, ${COLORS.purple}, ${COLORS.purpleSoft})` }} />
                <span style={{ fontSize: isMobile ? 10 : 12, color: COLORS.faint, marginTop: 6, whiteSpace: 'nowrap' }}>{costPeriodMode === 'monthly' ? p.period.slice(5) : fmtChartDateLabelDesktop(p.period)}</span>
              </div>
            ))}
          </div>
        )}
        {points.length > 0 && costPeriodMode !== 'cumulative' && (
          <p style={{ color: COLORS.gold, fontSize: isMobile ? 12 : 13.5, fontWeight: 600, marginTop: SP.md, marginBottom: 0 }}>
            รวม {points.length} {costPeriodMode === 'monthly' ? 'เดือน' : 'วัน'}: ${total7d.toFixed(2)}{desktop ? ` · เฉลี่ย $${avgPerDay.toFixed(2)}/${costPeriodMode === 'monthly' ? 'เดือน' : 'วัน'}` : ''}
          </p>
        )}
        {points.length > 0 && costPeriodMode === 'cumulative' && (
          <p style={{ color: COLORS.gold, fontSize: isMobile ? 12 : 13.5, fontWeight: 600, marginTop: SP.md, marginBottom: 0 }}>
            สะสมทั้งหมด {points.length} วัน: ${points[points.length - 1].cost_usd.toFixed(2)}
          </p>
        )}
      </div>
    );
  };

  const NIK_TABLE_COLS = '2.4fr 1fr 0.8fr';
  const NikSuggestionsCard = ({ desktop }) => (
    <div style={styles.card}>
      <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: SP.md }}>
        <p style={styles.sectionTitle}>รายงานจากนิก</p>
        {nikSuggestions?.pending_count > 0 && <span style={{ backgroundColor: 'rgba(245,196,107,0.16)', color: COLORS.gold, fontSize: 13, padding: '3px 11px', borderRadius: 12 }}>{nikSuggestions.pending_count} pending</span>}
      </div>
      {!nikSuggestions && <p style={{ color: COLORS.faint, fontSize: 14 }}>กำลังโหลด...</p>}
      {nikSuggestions?.suggestions?.length === 0 && <p style={{ color: COLORS.faint, fontSize: 14 }}>ยังไม่มี suggestion จากนิก</p>}

      {desktop && nikSuggestions?.suggestions?.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: NIK_TABLE_COLS, gap: SP.sm, padding: `${SP.sm}px 0`, borderBottom: `1px solid ${COLORS.cardBorder}`, marginBottom: SP.sm }}>
          {['ข้อเสนอ', 'วันที่แจ้ง', 'สถานะ'].map((h, i) => (
            <span key={h} style={{ fontSize: 13, fontWeight: 600, color: COLORS.faint, textAlign: i === 0 ? 'left' : 'right' }}>{h}</span>
          ))}
        </div>
      )}

      {nikSuggestions?.suggestions?.map(s => {
        const sColor = s.status === 'complete' ? COLORS.green : s.status === 'failed' ? COLORS.red : COLORS.gold;
        const sLabel = s.status === 'complete' ? 'Complete' : s.status === 'failed' ? 'Failed' : 'Pending';
        const dateStr = new Date(s.created_at).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'short', timeStyle: 'short' });

        if (desktop) {
          return (
            <div key={s.id} style={{ display: 'grid', gridTemplateColumns: NIK_TABLE_COLS, gap: SP.sm, alignItems: 'center', padding: `${SP.sm}px 0`, borderBottom: `1px solid ${COLORS.cardBorder}` }}>
              <span style={{ fontSize: 15, color: COLORS.text }}>{s.summary}</span>
              <span style={{ fontSize: 13.5, color: COLORS.muted, textAlign: 'right' }}>{dateStr}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: sColor, textAlign: 'right' }}>{sLabel}</span>
            </div>
          );
        }
        return (
          <div key={s.id} style={{ padding: SP.md, backgroundColor: 'rgba(148,163,184,0.08)', borderRadius: 10, marginBottom: SP.sm }}>
            <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <p style={{ fontSize: 13, fontWeight: 600, margin: 0, flex: 1, color: COLORS.text }}>{s.summary}</p>
              <span style={{ color: sColor, fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>{sLabel}</span>
            </div>
            <p style={{ color: COLORS.faint, fontSize: 11, margin: '6px 0 0 0' }}>{dateStr}</p>
            {s.status === 'failed' && s.error_message && <p style={{ color: COLORS.red, fontSize: 11, margin: '6px 0 0 0' }}>{s.error_message}</p>}
          </div>
        );
      })}
    </div>
  );

  const SystemTab = () => {
    const r14 = roiSummary?.['14d'];
    const r30 = roiSummary?.['30d'];

    return (
      <div style={styles.stack(SP.lg)}>
        <div>
          <h2 style={{ margin: 0, fontSize: isMobile ? 19 : 24, fontWeight: 800, color: COLORS.text }}>System</h2>
          <p style={{ margin: '4px 0 0 0', fontSize: isMobile ? 12 : 13.5, color: COLORS.muted }}>สถานะการทำงานของ AI Stock Analyzer</p>
        </div>

        {isMobile ? (
          <>
            {CostChartCard({ desktop: false })}
            <h3 style={styles.sectionTitle}>Win Rate ของ AI (เป้า 75%)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: SP.sm }}>
              {WinRateCard({ label: '@14 วัน', r: r14, showLabel: false })}
              {WinRateCard({ label: '@30 วัน', r: r30, showLabel: false })}
            </div>
          </>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1fr', gap: SP.lg, alignItems: 'stretch' }}>
            {CostChartCard({ desktop: true })}
            <div style={styles.stack(SP.md)}>
              {WinRateCard({ label: 'Win Rate @14 วัน', r: r14, fill: true })}
              {WinRateCard({ label: 'Win Rate @30 วัน', r: r30, fill: true })}
            </div>
          </div>
        )}

        {roiSummary?.portfolio_return && (
          <div style={{ ...styles.cardTight, ...styles.row(SP.sm), justifyContent: 'space-between' }}>
            <span style={{ fontSize: isMobile ? 13 : 14.5, color: COLORS.muted }}>ผลตอบแทนพอร์ตสะสมจริง (เป้า 13%, ไม่มีเส้นตาย)</span>
            <span style={{ fontSize: isMobile ? 15 : 17, fontWeight: 700, color: roiSummary.portfolio_return.return_pct >= 0 ? COLORS.green : COLORS.red }}>
              {roiSummary.portfolio_return.return_pct >= 0 ? '+' : ''}{roiSummary.portfolio_return.return_pct}%
            </span>
          </div>
        )}

        {NikSuggestionsCard({ desktop: !isMobile })}
      </div>
    );
  };

  // ===== RENDER =====
  // ✅ Desktop/Mobile แยกจริงต่อแท็บ (Portfolio/Tickers/News) ตาม UI_Spec.md — System ใช้ร่วมกัน
  // เพราะ MBBook confirm ว่าโครงสร้างเหมือนกันอยู่แล้ว ต่างแค่จำนวนคอลัมน์ (จัดการด้วย isMobile ภายใน)
  const renderTab = () => {
    if (activeTab === 'portfolio') return isMobile ? MobilePortfolio() : DesktopPortfolio();
    if (activeTab === 'tickers') return isMobile ? MobileTickers() : DesktopTickers();
    if (activeTab === 'news') return isMobile ? MobileNews() : DesktopNews();
    if (activeTab === 'system') return SystemTab();
    return MobilePortfolio();
  };

  const BottomNav = () => (
    <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 100, display: 'flex', backgroundColor: 'rgba(11,17,48,0.92)', borderTop: `1px solid ${COLORS.cardBorder}`, paddingBottom: 'env(safe-area-inset-bottom, 0px)', backdropFilter: 'blur(10px)' }}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.id;
        return (
          <button key={tab.id} className="press-btn" onClick={() => setActiveTab(tab.id)} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3, minHeight: 58, padding: '6px 2px', backgroundColor: 'transparent', border: 'none', color: active ? COLORS.purple : COLORS.muted, cursor: 'pointer' }}>
            <Icon size={20} strokeWidth={active ? 2.4 : 2} />
            <span style={{ fontSize: 10, fontWeight: active ? 700 : 500 }}>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );

  const TopNav = () => (
    <div style={{ ...styles.row(SP.xs), marginBottom: SP.xl, flexWrap: 'wrap' }}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.id;
        return (
          <button key={tab.id} className={`nav-btn${active ? ' nav-btn-active' : ''}`} onClick={() => setActiveTab(tab.id)} style={{
            ...styles.row(SP.xs), padding: '10px 18px', borderRadius: 12, fontWeight: 600, fontSize: 15,
            backgroundColor: active ? COLORS.purple : 'transparent', color: active ? '#fff' : COLORS.muted,
            border: `1px solid ${active ? COLORS.purple : COLORS.cardBorder}`, cursor: 'pointer', whiteSpace: 'nowrap',
          }}>
            <Icon size={17} /> {tab.label}
          </button>
        );
      })}
    </div>
  );

  // ===== ✅ เพิ่ม 2026-07-09: หน้า Login (ระบบ password) =====
  // helper ธรรมดา เรียกเป็น LoginView() ตามกติกา (ห้าม <LoginView/>) — ไม่มี hook ข้างใน
  // จอเดียวใช้ร่วม Desktop/Mobile ได้ (การ์ดเล็กกลางจอ — ข้อยกเว้นแบบเดียวกับ System tab)
  const submitLogin = async (pinOverride) => {
    // pinOverride: ส่งค่า PIN ตรงๆ ตอน auto-submit (state ยังไม่ทัน update ใน tick เดียวกัน)
    const pin = typeof pinOverride === 'string' ? pinOverride : loginPassword;
    if (!pin || loginState.busy) return;
    setLoginState({ busy: true, error: null });
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pin }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && (data.token || data.auth_disabled)) {
        const token = data.token || 'auth-disabled';
        localStorage.setItem(AUTH_TOKEN_KEY, token);
        setAuthToken(token);
        window.location.reload(); // โหลดข้อมูลใหม่ทั้งหมดด้วย token (effects รอบแรกยิงไปก่อน login แล้ว)
      } else {
        setLoginState({ busy: false, error: data.detail || 'รหัสผ่านไม่ถูกต้อง' });
      }
    } catch (e) {
      setLoginState({ busy: false, error: 'เชื่อมต่อ server ไม่ได้ ลองใหม่อีกครั้ง' });
    }
  };

  const LoginView = () => (
    <div style={{ ...styles.pageBg, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <style>{GLOBAL_CSS}</style>
      <div style={{ ...styles.card, width: 340, maxWidth: '88vw', padding: SP.xl, textAlign: 'center' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: COLORS.text, margin: 0, marginBottom: SP.xs }}>AI Stock Analyzer</h1>
        <div style={{ color: COLORS.muted, fontSize: 13, marginBottom: SP.lg }}>ใส่รหัส PIN 6 หลัก</div>
        <input
          type="password" value={loginPassword} autoFocus
          inputMode="numeric" pattern="[0-9]*" maxLength={6}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(0, 6); // ตัวเลขล้วน สูงสุด 6 หลัก
            setLoginPassword(v);
            if (loginState.error) setLoginState({ busy: false, error: null });
            if (v.length === 6) submitLogin(v); // ครบ 6 หลัก → เข้าอัตโนมัติแบบแอปธนาคาร
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') submitLogin(); }}
          placeholder="••••••" aria-label="รหัส PIN 6 หลัก"
          style={{ ...styles.input, width: '100%', boxSizing: 'border-box', textAlign: 'center', marginBottom: SP.sm, fontSize: 26, letterSpacing: 12, fontVariantNumeric: 'tabular-nums' }}
        />
        {loginState.error && (
          <div style={{ color: COLORS.red, fontSize: 12.5, marginBottom: SP.sm }}>{loginState.error}</div>
        )}
        <button className="press-btn" onClick={submitLogin} disabled={loginState.busy}
          style={{ width: '100%', padding: '12px 0', borderRadius: 12, border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 15, color: '#1a1305', background: COLORS.goldGradient || 'linear-gradient(180deg,#F7CE85,#EF9F27)', opacity: loginState.busy ? 0.6 : 1 }}>
          {loginState.busy ? 'กำลังตรวจสอบ...' : 'เข้าสู่ระบบ'}
        </button>
      </div>
    </div>
  );

  if (!authToken) return LoginView();

  return (
    <div style={styles.pageBg}>
      <style>{GLOBAL_CSS}</style>

      <div style={styles.pageContent}>
        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: isMobile ? SP.lg : SP.xl }}>
          <h1 style={{ fontSize: isMobile ? 18 : 25, fontWeight: 700, margin: 0, color: COLORS.text }}>AI Stock Analyzer</h1>
          <button className="icon-btn press-btn" onClick={() => setHideAmounts(v => !v)}
            title="ซ่อน/แสดงตัวเลขเงิน" aria-label="ซ่อนตัวเลขเงิน"
            style={{ width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}`, color: COLORS.muted, cursor: 'pointer', flexShrink: 0 }}>
            {hideAmounts ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>

        {!isMobile && TopNav()}

        {renderTab()}
      </div>

      {popup && PopupModal()}
      {ToastView()}

      {isMobile && BottomNav()}
    </div>
  );
}
