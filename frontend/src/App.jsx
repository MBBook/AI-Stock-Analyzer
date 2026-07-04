import React, { useState, useEffect } from 'react';
import {
  Eye, EyeOff, Briefcase, ArrowLeftRight, TrendingUp, Settings,
  Plus, Trash2, Upload, Search, Check, Camera, Info
} from 'lucide-react';

const API_URL = 'https://ai-stock-analyzer-msli.onrender.com';

// ✅ รื้อ 2026-07-03 (รอบ 4): ออกแบบ UI ใหม่ทั้งหมดตามที่ MBBook ทักท้วงตรงๆ
// ปัญหาเดิม: tab เยอะ (6 → รก), สีปนกันไม่มีระบบ (ม่วง/เขียว/แดง/ส้ม/ชมพูสุ่มกัน),
// ตัวอักษรเล็ก/contrast ต่ำอ่านยาก, border/background ซ้อนกันเยอะดูรก, emoji เกลื่อนหน้าจอ
// แก้: ลดเหลือ 4 tab (ยุบ News ที่แทบไม่มีเนื้อหาจริง + Agents เข้า System),
// จำกัดสีเหลือ 1 accent + เขียว/แดงเฉพาะความหมายกำไร-ขาดทุน/ซื้อ-ขาย, ใช้ lucide icon แทน emoji,
// กำหนด spacing/typography scale ให้ใช้ซ้ำทั้งไฟล์แทนตัวเลขสุ่ม

const COLORS = {
  bg: '#0b0b0f',
  surface: '#16161d',
  surfaceAlt: '#1e1e27',
  border: '#2a2a35',
  text: '#f2f2f5',
  muted: '#9a9aa8',
  faint: '#65656f',
  accent: '#8b7cf6',
  accentSoft: 'rgba(139,124,246,0.14)',
  success: '#34d399',
  successSoft: 'rgba(52,211,153,0.14)',
  danger: '#f87171',
  dangerSoft: 'rgba(248,113,113,0.14)',
  warning: '#fbbf24',
};

// Spacing scale ใช้ซ้ำทั้งไฟล์ (แทนตัวเลขสุ่ม 6/10/14/15/18/20)
const SP = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };

export default function DashboardV4() {
  const [activeTab, setActiveTab] = useState('portfolio');
  const [hideBalance, setHideBalance] = useState(false);
  const [stocks, setStocks] = useState([]);
  const [newTicker, setNewTicker] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [tradeTicker, setTradeTicker] = useState('');
  const [tradeAction, setTradeAction] = useState('BUY');
  const [tradeShares, setTradeShares] = useState('');
  const [tradePrice, setTradePrice] = useState('');
  const [tradeSubmitting, setTradeSubmitting] = useState(false);
  const [tradeMessage, setTradeMessage] = useState(null); // { type: 'success'|'error', text }
  const [tradeImageFile, setTradeImageFile] = useState(null);
  const [tradeImagePreview, setTradeImagePreview] = useState(null);
  const [tradeParsing, setTradeParsing] = useState(false);
  const [tradeParseMessage, setTradeParseMessage] = useState(null); // { type: 'success'|'error', text }
  const [loading, setLoading] = useState(false);
  const [portfolioData, setPortfolioData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [nikSuggestions, setNikSuggestions] = useState(null);
  const [costSummary, setCostSummary] = useState(null);
  const [reportList, setReportList] = useState(null);

  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // ===== Design-system style helpers (ใช้ซ้ำทุก tab แทนสไตล์แยกกันแบบเดิม) =====
  const styles = {
    page: {
      backgroundColor: COLORS.bg, minHeight: '100vh',
      padding: isMobile ? SP.md : SP.xl,
      paddingBottom: isMobile ? 84 : SP.xl,
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
      maxWidth: '100vw', overflowX: 'hidden', boxSizing: 'border-box', color: COLORS.text
    },
    card: {
      backgroundColor: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 12,
      padding: isMobile ? SP.lg : SP.xl,
    },
    cardTight: {
      backgroundColor: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 12,
      padding: SP.lg,
    },
    sectionTitle: { fontSize: 15, fontWeight: 600, color: COLORS.text, margin: 0 },
    label: { color: COLORS.muted, fontSize: 12, display: 'block', marginBottom: SP.xs },
    input: {
      width: '100%', boxSizing: 'border-box',
      padding: isMobile ? '12px 14px' : '10px 12px',
      backgroundColor: COLORS.surfaceAlt,
      color: COLORS.text,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 8,
      fontSize: isMobile ? 16 : 14,
      minHeight: isMobile ? 46 : 'auto',
    },
    stack: (gap) => ({ display: 'flex', flexDirection: 'column', gap: gap ?? SP.lg }),
    row: (gap) => ({ display: 'flex', alignItems: 'center', gap: gap ?? SP.sm }),
  };

  const btn = (variant = 'primary', extra = {}) => {
    const base = {
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: SP.xs,
      padding: isMobile ? '13px 18px' : '10px 16px',
      minHeight: isMobile ? 46 : 'auto',
      borderRadius: 8,
      fontSize: isMobile ? 15 : 14,
      fontWeight: 600,
      cursor: 'pointer',
      border: '1px solid transparent',
      transition: 'opacity 0.15s',
    };
    const variants = {
      primary: { backgroundColor: COLORS.accent, color: '#fff' },
      success: { backgroundColor: COLORS.success, color: '#0b0b0f' },
      danger: { backgroundColor: COLORS.danger, color: '#0b0b0f' },
      ghost: { backgroundColor: 'transparent', color: COLORS.muted, border: `1px solid ${COLORS.border}` },
      outline: { backgroundColor: 'transparent', color: COLORS.accent, border: `1px solid ${COLORS.accent}` },
    };
    return { ...base, ...variants[variant], ...extra };
  };

  const tabs = [
    { id: 'portfolio', label: 'พอร์ต', icon: Briefcase },
    { id: 'trade', label: 'บันทึกเทรด', icon: ArrowLeftRight },
    { id: 'stocks', label: 'หุ้น', icon: TrendingUp },
    { id: 'system', label: 'ระบบ', icon: Settings },
  ];

  // Fetch on mount
  useEffect(() => {
    fetchStocks();
    fetchPortfolio();
    fetchHistory();
    fetchNikSuggestions();
    fetchCostSummary();
    fetchReports();
  }, []);

  const fetchStocks = async () => {
    try {
      const response = await fetch(`${API_URL}/stocks`);
      const data = await response.json();
      setStocks(data.stocks || []);
    } catch (error) {
      console.error('Error fetching stocks:', error);
    }
  };

  const fetchPortfolio = async () => {
    try {
      const response = await fetch(`${API_URL}/portfolio`);
      const data = await response.json();
      setPortfolioData(data);
    } catch (error) {
      console.error('Error fetching portfolio:', error);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_URL}/workflow/history?limit=30`);
      const data = await response.json();
      setHistoryData(data);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  const fetchNikSuggestions = async () => {
    try {
      const response = await fetch(`${API_URL}/nik/suggestions`);
      const data = await response.json();
      setNikSuggestions(data);
    } catch (error) {
      console.error('Error fetching nik suggestions:', error);
    }
  };

  const fetchCostSummary = async () => {
    try {
      const response = await fetch(`${API_URL}/costs/summary`);
      const data = await response.json();
      setCostSummary(data);
    } catch (error) {
      console.error('Error fetching cost summary:', error);
    }
  };

  const fetchReports = async () => {
    try {
      const response = await fetch(`${API_URL}/workflow/reports?limit=7`);
      const data = await response.json();
      setReportList(data);
    } catch (error) {
      console.error('Error fetching reports:', error);
    }
  };

  const MAX_TICKERS = 30;

  const handleAddStock = async () => {
    if (!newTicker.trim()) return;
    if (stocks.length >= MAX_TICKERS) {
      alert(`ไม่สามารถเพิ่มได้ — ระบบรองรับสูงสุด ${MAX_TICKERS} tickers เท่านั้น (ปัจจุบัน ${stocks.length}/${MAX_TICKERS})`);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/stocks?ticker=${newTicker.toUpperCase()}`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'added' || data.status === 'exists') {
        setNewTicker('');
        fetchStocks();
      }
    } catch (error) {
      console.error('Error adding stock:', error);
    }
    setLoading(false);
  };

  const handleRemoveStock = async (ticker) => {
    try {
      await fetch(`${API_URL}/stocks/${ticker}`, { method: 'DELETE' });
      fetchStocks();
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
      const response = await fetch(`${API_URL}/trade-parse-image`, { method: 'POST', body: formData });
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

  const handleSubmitTrade = async () => {
    const ticker = tradeTicker.trim().toUpperCase();
    const shares = parseFloat(tradeShares);
    const price = parseFloat(tradePrice);

    if (!ticker) {
      setTradeMessage({ type: 'error', text: 'กรอกชื่อหุ้นก่อนครับ' });
      return;
    }
    if (!shares || shares <= 0) {
      setTradeMessage({ type: 'error', text: 'จำนวนหุ้นต้องมากกว่า 0 (ใส่ทศนิยมได้ เช่น 0.1874433)' });
      return;
    }
    if (!price || price <= 0) {
      setTradeMessage({ type: 'error', text: 'ราคาต้องมากกว่า 0' });
      return;
    }

    setTradeSubmitting(true);
    setTradeMessage(null);
    try {
      const params = new URLSearchParams({ ticker, action: tradeAction, shares: String(shares), price: String(price) });
      const response = await fetch(`${API_URL}/trade-update?${params}`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'recorded') {
        setTradeMessage({ type: 'success', text: `บันทึกแล้ว: ${tradeAction === 'BUY' ? 'ซื้อ' : 'ขาย'} ${ticker} ${shares} หุ้น @ $${price}` });
        setTradeTicker('');
        setTradeShares('');
        setTradePrice('');
        setTradeImageFile(null);
        setTradeImagePreview(null);
        setTradeParseMessage(null);
        fetchPortfolio();
      } else {
        setTradeMessage({ type: 'error', text: `เกิดข้อผิดพลาด: ${JSON.stringify(data)}` });
      }
    } catch (error) {
      setTradeMessage({ type: 'error', text: `เชื่อมต่อไม่ได้: ${error.message}` });
    }
    setTradeSubmitting(false);
  };

  const filteredStocks = stocks.filter(s => s.ticker.toLowerCase().includes(searchTerm.toLowerCase()));
  const usdToThb = (usd) => (usd * 33).toLocaleString('th-TH', { maximumFractionDigits: 2 });

  // ===== Small reusable pieces =====

  const InlineMessage = ({ msg }) => {
    if (!msg) return null;
    const ok = msg.type === 'success';
    return (
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: SP.sm,
        padding: '10px 12px', borderRadius: 8, marginTop: SP.sm,
        backgroundColor: ok ? COLORS.successSoft : COLORS.dangerSoft,
        color: ok ? COLORS.success : COLORS.danger, fontSize: 13,
      }}>
        {ok ? <Check size={16} style={{ flexShrink: 0, marginTop: 1 }} /> : <Info size={16} style={{ flexShrink: 0, marginTop: 1 }} />}
        <span>{msg.text}</span>
      </div>
    );
  };

  // ===== TABS =====

  const PortfolioTab = () => {
    const holdings = portfolioData?.holdings ?? [];
    return (
      <div style={styles.stack(SP.lg)}>
        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between' }}>
          <h2 style={{ ...styles.sectionTitle, fontSize: 18 }}>พอร์ตของบุ๊ค</h2>
          <button
            onClick={() => setHideBalance(!hideBalance)}
            style={btn('ghost', { padding: 10 })}
            aria-label="ซ่อน/แสดงยอด"
          >
            {hideBalance ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        {portfolioData && (
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: SP.md }}>
            {[
              { label: 'มูลค่ารวม', value: portfolioData.total_value, color: COLORS.text },
              { label: 'ต้นทุนรวม', value: portfolioData.total_cost, color: COLORS.text },
              { label: 'กำไร/ขาดทุนรวม', value: portfolioData.total_gain, color: portfolioData.total_gain >= 0 ? COLORS.success : COLORS.danger },
            ].map((stat) => (
              <div key={stat.label} style={styles.cardTight}>
                <p style={styles.label}>{stat.label}</p>
                <p style={{ fontSize: 20, fontWeight: 700, margin: 0, color: stat.color }}>
                  {hideBalance ? '฿ ••••' : `฿${usdToThb(stat.value).split('.')[0]}`}
                </p>
              </div>
            ))}
          </div>
        )}

        {holdings.length > 0 && (
          <div style={styles.stack(SP.sm)}>
            {holdings.map(h => {
              const isGain = h.gain >= 0;
              return (
                <div key={h.ticker} style={{ ...styles.cardTight, ...styles.row(SP.md), justifyContent: 'space-between' }}>
                  <div>
                    <p style={{ fontSize: 16, fontWeight: 700, margin: '0 0 4px 0', color: COLORS.text }}>{h.ticker}</p>
                    <p style={{ fontSize: 12, margin: 0, color: COLORS.muted }}>
                      {h.shares.toFixed(4)} หุ้น · เฉลี่ย ${h.avg_cost.toFixed(2)} · ปัจจุบัน ${h.current_price.toFixed(2)}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <p style={{ fontSize: 14, fontWeight: 700, margin: '0 0 4px 0', color: COLORS.text }}>
                      {hideBalance ? '฿ ••••' : `$${h.current_value.toFixed(2)}`}
                    </p>
                    <p style={{ fontSize: 12, margin: 0, color: isGain ? COLORS.success : COLORS.danger, fontWeight: 600 }}>
                      {isGain ? '+' : ''}{hideBalance ? '••••' : `$${h.gain.toFixed(2)}`} ({isGain ? '+' : ''}{h.gain_pct.toFixed(2)}%)
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {portfolioData && holdings.length === 0 && (
          <div style={{ ...styles.card, textAlign: 'center', color: COLORS.muted, fontSize: 13 }}>
            ยังไม่มีการถือครองหุ้น — ไปที่แท็บ "บันทึกเทรด" เพื่อเพิ่มรายการแรก
          </div>
        )}
      </div>
    );
  };

  const TradeTab = () => (
    <div style={styles.stack(SP.lg)}>
      <h2 style={{ ...styles.sectionTitle, fontSize: 18 }}>บันทึกการซื้อ-ขาย</h2>

      <div style={styles.card}>
        <p style={{ ...styles.row(SP.xs), color: COLORS.muted, fontSize: 13, marginBottom: SP.md, marginTop: 0 }}>
          <Camera size={16} /> ส่งรูปสลิปซื้อขาย (เช่น screenshot จาก Dime) ให้อ่านค่าอัตโนมัติ
        </p>

        <label style={{
          ...styles.row(SP.sm), justifyContent: 'center',
          padding: '14px', border: `1.5px dashed ${COLORS.border}`, borderRadius: 8,
          cursor: 'pointer', color: COLORS.muted, fontSize: 13, marginBottom: SP.md,
        }}>
          <Upload size={16} />
          {tradeImageFile ? tradeImageFile.name : 'เลือกรูปสลิป'}
          <input type="file" accept="image/*" capture="environment" onChange={handleSelectTradeImage} style={{ display: 'none' }} />
        </label>

        {tradeImagePreview && (
          <img src={tradeImagePreview} alt="trade slip preview"
            style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 8, marginBottom: SP.md, display: 'block', border: `1px solid ${COLORS.border}` }} />
        )}

        <button
          onClick={handleParseTradeImage}
          disabled={tradeParsing || !tradeImageFile}
          style={btn('outline', { width: isMobile ? '100%' : 'auto', opacity: (tradeParsing || !tradeImageFile) ? 0.5 : 1, cursor: (tradeParsing || !tradeImageFile) ? 'default' : 'pointer' })}
        >
          {tradeParsing ? 'กำลังอ่านรูป...' : 'อ่านข้อมูลจากรูป'}
        </button>
        <InlineMessage msg={tradeParseMessage} />
      </div>

      <div style={styles.card}>
        <p style={{ color: COLORS.faint, fontSize: 12, marginTop: 0, marginBottom: SP.lg }}>
          ตรวจทาน/แก้ไขข้อมูลก่อนกดบันทึก — แก้มือได้เสมอ ไม่จำเป็นต้องส่งรูป
        </p>

        <div style={styles.stack(SP.md)}>
          <div>
            <label style={styles.label}>หุ้น (Ticker)</label>
            <input type="text" value={tradeTicker} onChange={(e) => setTradeTicker(e.target.value)}
              placeholder="เช่น WDC, NBIS..." style={styles.input} />
          </div>

          <div>
            <label style={styles.label}>ประเภท</label>
            <div style={styles.row(SP.sm)}>
              {['BUY', 'SELL'].map(a => {
                const active = tradeAction === a;
                const c = a === 'BUY' ? COLORS.success : COLORS.danger;
                return (
                  <button key={a} onClick={() => setTradeAction(a)} style={{
                    flex: 1, padding: isMobile ? 14 : 10, minHeight: isMobile ? 46 : 'auto',
                    borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: 'pointer',
                    border: `1px solid ${c}`,
                    backgroundColor: active ? c : 'transparent',
                    color: active ? '#0b0b0f' : c,
                  }}>
                    {a === 'BUY' ? 'ซื้อ' : 'ขาย'}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label style={styles.label}>จำนวนหุ้น (ใส่ทศนิยมได้ — ดูช่อง "จำนวนหุ้น" ในสลิป)</label>
            <input type="number" step="any" value={tradeShares} onChange={(e) => setTradeShares(e.target.value)}
              placeholder="เช่น 0.1874433" style={styles.input} />
          </div>

          <div>
            <label style={styles.label}>ราคาต่อหุ้น (USD) — ใช้ "ราคาที่ได้จริง" จากสลิป</label>
            <input type="number" step="any" value={tradePrice} onChange={(e) => setTradePrice(e.target.value)}
              placeholder="เช่น 537.97" style={styles.input} />
          </div>

          <button onClick={handleSubmitTrade} disabled={tradeSubmitting}
            style={btn('primary', { width: isMobile ? '100%' : 'auto', opacity: tradeSubmitting ? 0.6 : 1, marginTop: SP.xs })}>
            <Check size={16} /> {tradeSubmitting ? 'กำลังบันทึก...' : 'บันทึกรายการ'}
          </button>
          <InlineMessage msg={tradeMessage} />
        </div>
      </div>
    </div>
  );

  const StockTab = () => (
    <div style={styles.stack(SP.lg)}>
      <div style={styles.card}>
        <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: SP.md }}>
          <h2 style={{ ...styles.sectionTitle, fontSize: 18 }}>เพิ่มหุ้น</h2>
          <span style={{ color: stocks.length >= MAX_TICKERS ? COLORS.danger : COLORS.muted, fontSize: 12, fontWeight: 600 }}>
            {stocks.length}/{MAX_TICKERS}
          </span>
        </div>
        <div style={styles.row(SP.sm)}>
          <input type="text" value={newTicker} onChange={(e) => setNewTicker(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddStock()}
            placeholder="เช่น NVDA, META..." style={{ ...styles.input, flex: 1 }} />
          <button onClick={handleAddStock} disabled={loading} style={btn('primary', { flexShrink: 0 })}>
            <Plus size={16} /> {loading ? 'กำลังเพิ่ม...' : 'เพิ่ม'}
          </button>
        </div>
      </div>

      <div style={{ position: 'relative' }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: COLORS.faint }} />
        <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="ค้นหาหุ้น..." style={{ ...styles.input, paddingLeft: 38 }} />
      </div>

      <div style={styles.stack(SP.sm)}>
        <p style={{ color: COLORS.faint, fontSize: 12, margin: 0 }}>แสดง {filteredStocks.length} จาก {stocks.length}</p>
        {filteredStocks.map((stock) => (
          <div key={stock.ticker} style={{ ...styles.cardTight, position: 'relative' }}>
            <div style={{ ...styles.row(SP.md), justifyContent: 'space-between' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={styles.row(SP.sm)}>
                  <p style={{ fontSize: 15, fontWeight: 700, margin: 0, color: COLORS.text }}>{stock.ticker}</p>
                  {stock.at_new_high && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6, backgroundColor: COLORS.successSoft, color: COLORS.success }}>ATH</span>
                  )}
                  {stock.at_new_low && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6, backgroundColor: COLORS.dangerSoft, color: COLORS.danger }}>ATL</span>
                  )}
                </div>
                <p style={{ color: COLORS.muted, fontSize: 12, margin: '4px 0 0 0' }}>
                  Signal: {stock.signal || '—'} · Confidence: {stock.confidence != null ? `${(stock.confidence * 100).toFixed(0)}%` : '—'}
                </p>
              </div>
              <button onClick={() => handleRemoveStock(stock.ticker)} style={btn('ghost', { padding: 10, flexShrink: 0, color: COLORS.danger })} aria-label="ลบ">
                <Trash2 size={16} />
              </button>
            </div>
            {stock.reasoning && (
              <p style={{ color: COLORS.muted, fontSize: 12, lineHeight: 1.6, margin: `${SP.sm}px 0 0 0`, paddingTop: SP.sm, borderTop: `1px solid ${COLORS.border}` }}>
                {stock.reasoning}
              </p>
            )}
          </div>
        ))}
        {filteredStocks.length === 0 && (
          <p style={{ color: COLORS.faint, fontSize: 13, textAlign: 'center', padding: SP.lg }}>ไม่พบหุ้นที่ค้นหา</p>
        )}
      </div>
    </div>
  );

  const SystemTab = () => {
    const totalCost = historyData?.total_cost_usd ?? 0;
    const runs = historyData?.runs ?? [];
    const lastRun = runs[0];
    const passCount = runs.filter(r => r.status === 'COMPLETE').length;
    const rejectCount = runs.filter(r => r.status === 'REJECTED').length;

    const target = costSummary?.budget?.target_monthly_usd ?? 10;
    const ceiling = costSummary?.budget?.ceiling_monthly_usd ?? 12;
    const projected = costSummary?.projected_month_cost_usd;
    const monthCost = costSummary?.month_to_date?.total_cost_usd ?? 0;
    const budgetStatus = costSummary?.budget?.status;
    const statusColor = budgetStatus === 'over_ceiling' ? COLORS.danger
      : budgetStatus === 'over_target_under_ceiling' ? COLORS.warning
      : COLORS.success;
    const statusLabel = budgetStatus === 'over_ceiling' ? 'เกินเพดาน'
      : budgetStatus === 'over_target_under_ceiling' ? 'เกินเป้า แต่ยังไม่เกินเพดาน'
      : budgetStatus === 'within_target' ? 'อยู่ในเป้า'
      : 'กำลังรวบรวมข้อมูล...';
    const barPct = projected ? Math.min((projected / ceiling) * 100, 100) : 0;

    const pipeline = ['นัตตี้', 'หนุ่ม', 'มด', 'แฮรี่', 'เจน', 'นน', 'เอ'];

    return (
      <div style={styles.stack(SP.lg)}>
        <h2 style={{ ...styles.sectionTitle, fontSize: 18 }}>ระบบ</h2>

        {/* รายงานตลาดย้อนหลัง — เพิ่ม 2026-07-03: เจนเขียนรายงานนี้ทุกคืนอยู่แล้ว
            เดิมไม่เคยถูกบันทึกถาวรหรือแสดงที่ไหนเลย ตอนนี้ให้ MBBook อ่านแทนการหาข่าวเอง
            ✅ แก้ 2026-07-03 (รอบ 2): เดิมโชว์แค่ "ล่าสุด" อันเดียว — ถ้าไม่ว่างเข้ามาดูหลายวัน
            รายงานของคืนก่อนๆ ที่ยังอยู่ใน DB จริงจะดูไม่ได้ ตอนนี้แสดงย้อนหลังได้สูงสุด 7 คืน */}
        <div style={styles.card}>
          <p style={{ ...styles.sectionTitle, marginBottom: SP.md }}>รายงานตลาดย้อนหลัง</p>

          {!reportList && <p style={{ color: COLORS.faint, fontSize: 13 }}>กำลังโหลด...</p>}
          {reportList && reportList.count === 0 && (
            <p style={{ color: COLORS.faint, fontSize: 13 }}>ยังไม่มีรายงานที่บันทึกไว้ — รอ workflow รันรอบถัดไป (22:00 น.)</p>
          )}

          {reportList?.reports?.map((r, idx) => (
            <div key={r.id} style={{
              paddingTop: idx === 0 ? 0 : SP.lg,
              marginTop: idx === 0 ? 0 : SP.lg,
              borderTop: idx === 0 ? 'none' : `1px solid ${COLORS.border}`,
            }}>
              <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: SP.sm }}>
                <span style={{ color: COLORS.text, fontSize: 13, fontWeight: 700 }}>
                  {new Date(r.timestamp).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'medium', timeStyle: 'short' })}
                </span>
                <span style={{ color: COLORS.muted, fontSize: 12 }}>
                  BUY {r.buy_signals} · HOLD {r.hold_signals} · SELL {r.sell_signals}
                </span>
              </div>
              <p style={{ color: COLORS.text, fontSize: 13, lineHeight: 1.7, margin: 0, whiteSpace: 'pre-wrap' }}>
                {r.report}
              </p>
            </div>
          ))}
        </div>

        {/* Monthly cost */}
        <div style={styles.card}>
          <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: SP.md }}>
            <p style={{ ...styles.sectionTitle }}>ค่าใช้จ่ายรายเดือน</p>
            <span style={{ color: COLORS.muted, fontSize: 12 }}>เป้า ${target} / เพดาน ${ceiling}</span>
          </div>
          <div style={{ width: '100%', height: 6, backgroundColor: COLORS.surfaceAlt, borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${barPct}%`, height: '100%', backgroundColor: statusColor, borderRadius: 4 }} />
          </div>
          <p style={{ color: COLORS.muted, fontSize: 12, marginTop: SP.sm, marginBottom: 0 }}>
            เดือนนี้: ${monthCost.toFixed(2)} · คาดการณ์เต็มเดือน: {projected != null ? `$${projected.toFixed(2)}` : '—'} ·{' '}
            <span style={{ color: statusColor, fontWeight: 600 }}>{statusLabel}</span>
          </p>

          {costSummary?.by_weekday && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: SP.xs, marginTop: SP.lg }}>
              {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'].map(day => {
                const d = costSummary.by_weekday[day];
                return (
                  <div key={day} style={{ padding: SP.sm, backgroundColor: COLORS.surfaceAlt, borderRadius: 6, textAlign: 'center' }}>
                    <p style={{ color: COLORS.faint, fontSize: 10, margin: '0 0 4px 0' }}>{day.slice(0, 3)}</p>
                    <p style={{ color: COLORS.text, fontSize: 12, fontWeight: 700, margin: 0 }}>
                      {d?.avg_cost_usd != null ? `$${d.avg_cost_usd.toFixed(2)}` : '—'}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Run stats */}
        <div style={{ ...styles.card, display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: SP.lg }}>
          <div>
            <p style={styles.label}>ใช้ไปทั้งหมด</p>
            <p style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>${totalCost.toFixed(2)}</p>
          </div>
          <div>
            <p style={styles.label}>PASS / REJECT</p>
            <p style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
              <span style={{ color: COLORS.success }}>{passCount}</span> / <span style={{ color: COLORS.danger }}>{rejectCount}</span>
            </p>
          </div>
          <div>
            <p style={styles.label}>เฉลี่ย/run ล่าสุด</p>
            <p style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
              {costSummary?.recent_avg_cost_per_run_usd != null ? `$${costSummary.recent_avg_cost_per_run_usd.toFixed(3)}` : '—'}
            </p>
          </div>
        </div>

        {/* Last run */}
        {lastRun && (
          <div style={styles.card}>
            <p style={styles.label}>รันล่าสุด</p>
            <p style={{ fontSize: 13, margin: '4px 0', color: COLORS.text }}>
              {new Date(lastRun.timestamp).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok' })}
            </p>
            <p style={{ fontSize: 13, margin: '4px 0', color: lastRun.status === 'COMPLETE' ? COLORS.success : COLORS.danger, fontWeight: 600 }}>
              {lastRun.status} — BUY {lastRun.buy_signals} / HOLD {lastRun.hold_signals} / SELL {lastRun.sell_signals}
            </p>
            {lastRun.cost_usd > 0 && (
              <p style={{ fontSize: 12, margin: '4px 0 0 0', color: COLORS.muted }}>ค่าใช้จ่าย: ${lastRun.cost_usd?.toFixed(4)}</p>
            )}
          </div>
        )}

        {/* Agent pipeline — ย่อเป็นแถวสั้นๆ แทน ASCII art เดิม */}
        <div style={styles.card}>
          <p style={{ ...styles.sectionTitle, marginBottom: SP.md }}>ลำดับการทำงานอัตโนมัติ</p>
          <div style={{ ...styles.row(SP.xs), flexWrap: 'wrap' }}>
            {pipeline.map((name, i) => (
              <React.Fragment key={name}>
                <span style={{ padding: '4px 10px', borderRadius: 6, backgroundColor: COLORS.surfaceAlt, fontSize: 12, color: COLORS.text }}>
                  {name}
                </span>
                {i < pipeline.length - 1 && <span style={{ color: COLORS.faint, fontSize: 12 }}>→</span>}
              </React.Fragment>
            ))}
          </div>
          <p style={{ color: COLORS.faint, fontSize: 12, marginTop: SP.md, marginBottom: 0 }}>
            ทำงานทุกวัน 22:00 น. (จันทร์ดึงข่าวย้อน 72 ชม. · ศุกร์เพิ่มนิกปรับโค้ด) · โคลสันบันทึกเทรดตามคำสั่งจากแท็บ "บันทึกเทรด"
          </p>
        </div>

        {/* นิก suggestions */}
        <div style={styles.card}>
          <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: SP.md }}>
            <p style={styles.sectionTitle}>Code Suggestions (นิก)</p>
            {nikSuggestions?.pending_count > 0 && (
              <span style={{ backgroundColor: COLORS.surfaceAlt, color: COLORS.warning, fontSize: 12, padding: '2px 10px', borderRadius: 12 }}>
                {nikSuggestions.pending_count} pending
              </span>
            )}
          </div>

          {!nikSuggestions && <p style={{ color: COLORS.faint, fontSize: 13 }}>กำลังโหลด...</p>}
          {nikSuggestions?.suggestions?.length === 0 && <p style={{ color: COLORS.faint, fontSize: 13 }}>ยังไม่มี suggestion จากนิก</p>}

          {nikSuggestions?.suggestions?.map(s => {
            const sColor = s.status === 'complete' ? COLORS.success : s.status === 'failed' ? COLORS.danger : COLORS.warning;
            const sLabel = s.status === 'complete' ? 'Complete' : s.status === 'failed' ? 'Failed' : 'Pending';
            const dateStr = new Date(s.created_at).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'short', timeStyle: 'short' });
            return (
              <div key={s.id} style={{ padding: SP.md, backgroundColor: COLORS.surfaceAlt, borderRadius: 8, marginBottom: SP.sm }}>
                <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <p style={{ fontSize: 13, fontWeight: 600, margin: 0, flex: 1, color: COLORS.text }}>{s.summary}</p>
                  <span style={{ color: sColor, fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>{sLabel}</span>
                </div>
                <p style={{ color: COLORS.faint, fontSize: 11, margin: '6px 0 0 0' }}>{dateStr}</p>
                {s.status === 'failed' && s.error_message && (
                  <p style={{ color: COLORS.danger, fontSize: 11, margin: '6px 0 0 0' }}>{s.error_message}</p>
                )}
                {s.status === 'pending' && (
                  <div style={{ ...styles.row(SP.sm), marginTop: SP.sm }}>
                    <button onClick={() => navigator.clipboard.writeText(`ดู diff ของ นิก suggestion id=${s.id}: ${s.summary}`)}
                      style={btn('ghost', { padding: '4px 10px', fontSize: 11, minHeight: 'auto' })}>
                      Copy — ดู diff
                    </button>
                    <button onClick={() => navigator.clipboard.writeText(`apply นิก suggestion id=${s.id}: ${s.summary}`)}
                      style={btn('outline', { padding: '4px 10px', fontSize: 11, minHeight: 'auto' })}>
                      Copy — apply
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'portfolio': return <PortfolioTab />;
      case 'trade': return <TradeTab />;
      case 'stocks': return <StockTab />;
      case 'system': return <SystemTab />;
      default: return <PortfolioTab />;
    }
  };

  const BottomNav = () => (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 100,
      display: 'flex', backgroundColor: COLORS.surface,
      borderTop: `1px solid ${COLORS.border}`,
      paddingBottom: 'env(safe-area-inset-bottom, 0px)',
    }}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.id;
        return (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: 3, minHeight: 58, padding: '6px 2px',
            backgroundColor: 'transparent', border: 'none',
            color: active ? COLORS.accent : COLORS.muted, cursor: 'pointer',
          }}>
            <Icon size={20} strokeWidth={active ? 2.4 : 2} />
            <span style={{ fontSize: 10, fontWeight: active ? 700 : 500 }}>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );

  return (
    <div style={styles.page}>
      <div style={{ ...styles.row(SP.sm), justifyContent: 'space-between', marginBottom: isMobile ? SP.lg : SP.xl }}>
        <h1 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, margin: 0, color: COLORS.text }}>
          AI Stock Analyzer
        </h1>
      </div>

      {!isMobile && (
        <div style={{ ...styles.row(SP.xs), marginBottom: SP.xl, flexWrap: 'wrap' }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                ...styles.row(SP.xs),
                padding: '9px 16px', borderRadius: 8, fontWeight: 600, fontSize: 14,
                backgroundColor: active ? COLORS.accent : 'transparent',
                color: active ? '#fff' : COLORS.muted,
                border: `1px solid ${active ? COLORS.accent : COLORS.border}`,
                cursor: 'pointer', whiteSpace: 'nowrap',
              }}>
                <Icon size={16} /> {tab.label}
              </button>
            );
          })}
        </div>
      )}

      {renderTab()}

      {isMobile && <BottomNav />}
    </div>
  );
}
