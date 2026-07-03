import React, { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const API_URL = 'https://ai-stock-analyzer-msli.onrender.com';

export default function DashboardV4() {
  const [activeTab, setActiveTab] = useState('news');
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

  // ✅ เพิ่ม 2026-07-03 (รอบ 3): mobile UI แยกโครงสร้างจริง ไม่ใช่แค่ย่อขนาด
  // isMobile ใช้ตัดสินว่าจะ render bottom nav bar + เลย์เอาต์ 1 คอลัมน์ หรือ top tab bar + เลย์เอาต์เดสก์ท็อป
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const colors = {
    surface: '#121212',
    surface2: '#1e1e1e',
    surface3: '#272727',
    primary: '#7c4dff',
    primaryLight: '#b39ddb',
    secondary: '#9575cd',
    error: '#cf6679',
    success: '#69f0ae',
    warning: '#ffb74d',
    neutral: '#b0b0b0'
  };

  const tabs = [
    { id: 'news', label: '📰 News' },
    { id: 'stock', label: '📈 Stock' },
    { id: 'agents', label: '🤖 Agents' },
    { id: 'trade', label: '💱 Trade Update' },
    { id: 'portfolio', label: '💼 Portfolio' },
    { id: 'stats', label: '📊 Status' }
  ];

  // Fetch stocks on mount
  useEffect(() => {
    fetchStocks();
    fetchPortfolio();
    fetchHistory();
    fetchNikSuggestions();
    fetchCostSummary();
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

  const MAX_TICKERS = 30;

  const handleAddStock = async () => {
    if (!newTicker.trim()) return;

    if (stocks.length >= MAX_TICKERS) {
      alert(`⚠️ ไม่สามารถเพิ่มได้ — ระบบรองรับสูงสุด ${MAX_TICKERS} tickers เท่านั้น\nปัจจุบัน: ${stocks.length}/${MAX_TICKERS}`);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/stocks?ticker=${newTicker.toUpperCase()}`, {
        method: 'POST'
      });
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
        setTradeParseMessage({ type: 'success', text: '✅ อ่านรูปแล้ว — ตรวจทานข้อมูลด้านล่างก่อนกดบันทึก' });
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
      const params = new URLSearchParams({
        ticker, action: tradeAction, shares: String(shares), price: String(price)
      });
      const response = await fetch(`${API_URL}/trade-update?${params}`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'recorded') {
        setTradeMessage({ type: 'success', text: `✅ บันทึกแล้ว: ${tradeAction} ${ticker} ${shares} หุ้น @ $${price}` });
        setTradeTicker('');
        setTradeShares('');
        setTradePrice('');
        setTradeImageFile(null);
        setTradeImagePreview(null);
        setTradeParseMessage(null);
        fetchPortfolio(); // รีเฟรช portfolio ให้เห็นผลทันที
      } else {
        setTradeMessage({ type: 'error', text: `เกิดข้อผิดพลาด: ${JSON.stringify(data)}` });
      }
    } catch (error) {
      setTradeMessage({ type: 'error', text: `เชื่อมต่อไม่ได้: ${error.message}` });
    }
    setTradeSubmitting(false);
  };

  const filteredStocks = stocks.filter(s =>
    s.ticker.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const usdToThb = (usd) => (usd * 33).toLocaleString('th-TH', { maximumFractionDigits: 2 });

  // ===== TABS =====

  const NewsTab = () => (
    <div className="space-y-4">
      <p style={{ color: colors.neutral }} className="text-sm mb-4">📰 Latest Market News</p>
      <div style={{ padding: '20px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.primary}` }}>
        <p style={{ color: colors.neutral }}>ข่าวหุ้นอัพเดตทุกวัน 22:00 น. ผ่านระบบ Agent นัตตี้</p>
      </div>
    </div>
  );

  const StockTab = () => (
    <div className="space-y-6">
      <div style={{ padding: '20px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.primaryLight}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2 style={{ color: colors.primary }}>➕ เพิ่มหุ้น</h2>
          <span style={{
            color: stocks.length >= MAX_TICKERS ? colors.error : colors.neutral,
            fontSize: '13px',
            fontWeight: stocks.length >= MAX_TICKERS ? 'bold' : 'normal'
          }}>
            {stocks.length >= MAX_TICKERS ? '🚫 เต็มแล้ว' : ''} {stocks.length}/{MAX_TICKERS} tickers
          </span>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddStock()}
            placeholder="เช่น NVDA, META..."
            style={{
              flex: 1,
              padding: '10px 12px',
              backgroundColor: colors.surface3,
              color: '#fff',
              border: `1px solid ${colors.primary}`,
              borderRadius: '6px'
            }}
          />
          <button
            onClick={handleAddStock}
            disabled={loading}
            style={{
              padding: isMobile ? '14px 20px' : '10px 20px',
              minHeight: isMobile ? '48px' : 'auto',
              backgroundColor: colors.success,
              color: '#000',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            {loading ? 'Adding...' : 'Add'}
          </button>
        </div>
      </div>

      <input
        type="text"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        placeholder="ค้นหาหุ้น..."
        style={{
          width: '100%',
          padding: '10px 12px',
          backgroundColor: colors.surface2,
          color: '#fff',
          border: `1px solid ${colors.secondary}`,
          borderRadius: '6px'
        }}
      />

      <div className="space-y-3">
        <p style={{ color: colors.neutral }} className="text-sm">แสดง {filteredStocks.length} / {stocks.length}</p>
        {filteredStocks.map((stock) => (
          <div key={stock.ticker} style={{
            padding: '15px',
            backgroundColor: colors.surface2,
            border: `1px solid ${colors.secondary}`,
            borderRadius: '6px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'relative'
          }}>
            {stock.at_new_high && (
              <span style={{
                position: 'absolute', top: '10px', right: '10px',
                background: '#16a34a', color: '#fff',
                fontSize: '11px', fontWeight: 'bold',
                padding: '3px 9px', borderRadius: '6px', letterSpacing: '0.5px'
              }}>ATH</span>
            )}
            {stock.at_new_low && (
              <span style={{
                position: 'absolute', top: '10px', right: '10px',
                background: '#dc2626', color: '#fff',
                fontSize: '11px', fontWeight: 'bold',
                padding: '3px 9px', borderRadius: '6px', letterSpacing: '0.5px'
              }}>ATL</span>
            )}
            <div style={{ flex: 1 }}>
              <h3 style={{ color: '#fff', fontWeight: 'bold' }}>{stock.ticker}</h3>
              <p style={{ color: colors.neutral, fontSize: '12px' }}>
                Signal: {stock.signal} | Confidence: {(stock.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <button
              onClick={() => handleRemoveStock(stock.ticker)}
              style={{
                marginLeft: '16px',
                padding: '8px 12px',
                backgroundColor: colors.error,
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              ลบ
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  const AgentsTab = () => (
    <div className="space-y-4">
      <p style={{ color: colors.neutral }} className="text-sm mb-4">🤖 Agent Workflow (Sequential)</p>
      <div style={{ 
        padding: '20px',
        backgroundColor: colors.surface2, 
        borderRadius: '8px',
        border: `2px solid ${colors.primary}`
      }}>
        <div style={{ color: '#fff', lineHeight: '2', fontFamily: 'monospace', fontSize: '13px' }}>
          <div>START</div>
          <div style={{ color: colors.primary }}>↓</div>
          <div>📰 นัตตี้ (Get News)</div>
          <div style={{ color: colors.primary }}>↓</div>
          <div>📊 หนุ่ม (Analyze Stocks + yfinance)</div>
          <div style={{ color: colors.primary }}>↓</div>
          <div>✓ มด (Cross-Validate Signals)</div>
          <div style={{ color: colors.primary }}>↓</div>
          <div>💼 แฮรี่ (Monitor Portfolio)</div>
          <div style={{ color: colors.primary }}>↓</div>
          <div>📋 เจน (Generate Report)</div>
          <div style={{ color: colors.primary }}>↓</div>
          <div>🔍 นน (QA Manager Check)</div>
          <div style={{ color: colors.warning }}>├─ PASS → 📝 เอ (Record) → Update Dashboard</div>
          <div style={{ color: colors.error }}>└─ ERROR → 🔄 เก้า (Retry 3x)</div>
        </div>
      </div>
      <div style={{ padding: '15px', backgroundColor: colors.surface2, borderRadius: '6px' }}>
        <p style={{ color: colors.neutral, fontSize: '12px', margin: '8px 0' }}>
          <strong>💰 โคลสัน:</strong> Manual Trade Updates
        </p>
        <p style={{ color: colors.neutral, fontSize: '12px', margin: '8px 0' }}>
          <strong>⚙️ นิก:</strong> Code Optimization (Every Friday)
        </p>
        <p style={{ color: colors.neutral, fontSize: '12px', margin: '8px 0' }}>
          <strong>Schedule:</strong> Tue-Fri 22:00 (24h news) | Mon 22:00 (Sat-Sun-Mon news)
        </p>
      </div>
    </div>
  );

  const TradeTab = () => (
    <div className="space-y-6">
      <div style={{ padding: '20px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.primaryLight}` }}>
        <h2 style={{ color: colors.primary, marginBottom: '15px' }}>💱 บันทึกการซื้อ-ขาย</h2>

        <div style={{
          padding: '14px', backgroundColor: colors.surface3, borderRadius: '8px',
          border: `1px dashed ${colors.primaryLight}`, marginBottom: '16px'
        }}>
          <label style={{ color: colors.neutral, fontSize: '12px', display: 'block', marginBottom: '8px' }}>
            📷 ส่งรูปสลิปซื้อขาย (เช่น screenshot จาก Dime) — ให้โคลสันอ่านค่าให้อัตโนมัติ
          </label>
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleSelectTradeImage}
            style={{ color: colors.neutral, fontSize: '13px', marginBottom: '10px', width: '100%' }}
          />
          {tradeImagePreview && (
            <img
              src={tradeImagePreview}
              alt="trade slip preview"
              style={{ maxWidth: '100%', maxHeight: '220px', borderRadius: '6px', marginBottom: '10px', display: 'block' }}
            />
          )}
          <button
            onClick={handleParseTradeImage}
            disabled={tradeParsing || !tradeImageFile}
            style={{
              width: isMobile ? '100%' : 'auto',
              padding: isMobile ? '14px 16px' : '10px 16px',
              minHeight: isMobile ? '48px' : 'auto',
              backgroundColor: colors.secondary,
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: (tradeParsing || !tradeImageFile) ? 'default' : 'pointer',
              fontWeight: 'bold',
              opacity: (tradeParsing || !tradeImageFile) ? 0.6 : 1
            }}
          >
            {tradeParsing ? 'กำลังอ่านรูป...' : '🔍 อ่านข้อมูลจากรูป'}
          </button>
          {tradeParseMessage && (
            <p style={{
              color: tradeParseMessage.type === 'success' ? colors.success : colors.error,
              fontSize: '13px', marginTop: '8px', marginBottom: 0
            }}>
              {tradeParseMessage.text}
            </p>
          )}
        </div>

        <p style={{ color: colors.neutral, fontSize: '12px', marginBottom: '12px' }}>
          ตรวจทาน/แก้ไขข้อมูลด้านล่างก่อนกดบันทึก (แก้มือได้เสมอ ไม่จำเป็นต้องส่งรูป)
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ color: colors.neutral, fontSize: '12px', display: 'block', marginBottom: '6px' }}>หุ้น (Ticker)</label>
            <input
              type="text"
              value={tradeTicker}
              onChange={(e) => setTradeTicker(e.target.value)}
              placeholder="เช่น WDC, NBIS..."
              style={{
                width: '100%', padding: isMobile ? '14px 12px' : '10px 12px', minHeight: isMobile ? '48px' : 'auto',
                backgroundColor: colors.surface3, fontSize: isMobile ? '16px' : '14px',
                color: '#fff', border: `1px solid ${colors.primary}`, borderRadius: '6px', boxSizing: 'border-box'
              }}
            />
          </div>

          <div>
            <label style={{ color: colors.neutral, fontSize: '12px', display: 'block', marginBottom: '6px' }}>ประเภท</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {['BUY', 'SELL'].map(a => (
                <button
                  key={a}
                  onClick={() => setTradeAction(a)}
                  style={{
                    flex: 1, padding: isMobile ? '14px' : '10px', minHeight: isMobile ? '48px' : 'auto',
                    borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer',
                    border: `1px solid ${a === 'BUY' ? colors.success : colors.error}`,
                    backgroundColor: tradeAction === a ? (a === 'BUY' ? colors.success : colors.error) : 'transparent',
                    color: tradeAction === a ? '#000' : (a === 'BUY' ? colors.success : colors.error)
                  }}
                >
                  {a === 'BUY' ? '🟢 ซื้อ' : '🔴 ขาย'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label style={{ color: colors.neutral, fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              จำนวนหุ้น (ใส่ทศนิยมได้ — ดูจากช่อง "จำนวนหุ้น" ในสลิป Dime)
            </label>
            <input
              type="number"
              step="any"
              value={tradeShares}
              onChange={(e) => setTradeShares(e.target.value)}
              placeholder="เช่น 0.1874433"
              style={{
                width: '100%', padding: isMobile ? '14px 12px' : '10px 12px', minHeight: isMobile ? '48px' : 'auto',
                backgroundColor: colors.surface3, fontSize: isMobile ? '16px' : '14px',
                color: '#fff', border: `1px solid ${colors.primary}`, borderRadius: '6px', boxSizing: 'border-box'
              }}
            />
          </div>

          <div>
            <label style={{ color: colors.neutral, fontSize: '12px', display: 'block', marginBottom: '6px' }}>
              ราคาต่อหุ้น (USD) — ใช้ "ราคาที่ได้จริง" จากสลิป
            </label>
            <input
              type="number"
              step="any"
              value={tradePrice}
              onChange={(e) => setTradePrice(e.target.value)}
              placeholder="เช่น 537.97"
              style={{
                width: '100%', padding: isMobile ? '14px 12px' : '10px 12px', minHeight: isMobile ? '48px' : 'auto',
                backgroundColor: colors.surface3, fontSize: isMobile ? '16px' : '14px',
                color: '#fff', border: `1px solid ${colors.primary}`, borderRadius: '6px', boxSizing: 'border-box'
              }}
            />
          </div>

          <button
            onClick={handleSubmitTrade}
            disabled={tradeSubmitting}
            style={{
              marginTop: '4px',
              width: isMobile ? '100%' : 'auto',
              padding: isMobile ? '16px 20px' : '12px 20px',
              minHeight: isMobile ? '52px' : 'auto',
              fontSize: isMobile ? '16px' : '14px',
              backgroundColor: colors.primary,
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: tradeSubmitting ? 'default' : 'pointer',
              fontWeight: 'bold',
              opacity: tradeSubmitting ? 0.6 : 1
            }}
          >
            {tradeSubmitting ? 'กำลังบันทึก...' : '✅ บันทึกรายการ'}
          </button>

          {tradeMessage && (
            <p style={{
              color: tradeMessage.type === 'success' ? colors.success : colors.error,
              fontSize: '13px', marginTop: '4px'
            }}>
              {tradeMessage.text}
            </p>
          )}
        </div>
      </div>
    </div>
  );

  const PortfolioTab = () => (
    <div className="space-y-6">
      <div style={{ 
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px',
        backgroundColor: colors.surface2,
        borderRadius: '8px',
        border: `1px solid ${colors.primaryLight}`
      }}>
        <h2 style={{ color: colors.primary, margin: 0 }}>💼 Portfolio</h2>
        <button
          onClick={() => setHideBalance(!hideBalance)}
          style={{
            padding: '8px',
            backgroundColor: colors.surface3,
            border: `1px solid ${colors.primary}`,
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          {hideBalance ? '👁️‍🗨️' : '👁️'}
        </button>
      </div>

      {portfolioData && (
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(140px, 1fr))', gap: '15px' }}>
          <div style={{ padding: '15px', backgroundColor: colors.surface2, border: `2px solid ${colors.primary}`, borderRadius: '6px' }}>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Total Value</p>
            <p style={{ color: colors.primary, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              {hideBalance ? '฿****' : `฿${usdToThb(portfolioData.total_value).split('.')[0]}`}
            </p>
          </div>
          <div style={{ padding: '15px', backgroundColor: colors.surface2, border: `1px solid ${colors.secondary}`, borderRadius: '6px' }}>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Total Cost</p>
            <p style={{ color: colors.primary, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              {hideBalance ? '฿****' : `฿${usdToThb(portfolioData.total_cost).split('.')[0]}`}
            </p>
          </div>
          <div style={{ padding: '15px', backgroundColor: colors.surface2, border: `2px solid ${colors.success}`, borderRadius: '6px' }}>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Total Gain</p>
            <p style={{ color: colors.success, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              {hideBalance ? '฿****' : `฿${usdToThb(portfolioData.total_gain).split('.')[0]}`}
            </p>
          </div>
        </div>
      )}

      {portfolioData?.holdings?.length > 0 && (
        <div className="space-y-3">
          {portfolioData.holdings.map(h => {
            const isGain = h.gain >= 0;
            return (
              <div key={h.ticker} style={{
                padding: '15px', backgroundColor: colors.surface2,
                border: `1px solid ${isGain ? colors.success : colors.error}55`,
                borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
              }}>
                <div>
                  <h3 style={{ color: '#fff', fontWeight: 'bold', margin: '0 0 4px 0' }}>{h.ticker}</h3>
                  <p style={{ color: colors.neutral, fontSize: '12px', margin: 0 }}>
                    {h.shares.toFixed(4)} หุ้น @ เฉลี่ย ${h.avg_cost.toFixed(2)} · ราคาปัจจุบัน ${h.current_price.toFixed(2)}
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <p style={{ color: '#fff', fontSize: '14px', fontWeight: 'bold', margin: '0 0 4px 0' }}>
                    {hideBalance ? '฿****' : `$${h.current_value.toFixed(2)}`}
                  </p>
                  <p style={{ color: isGain ? colors.success : colors.error, fontSize: '12px', margin: 0 }}>
                    {isGain ? '+' : ''}{hideBalance ? '****' : `$${h.gain.toFixed(2)}`} ({isGain ? '+' : ''}{h.gain_pct.toFixed(2)}%)
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {portfolioData && portfolioData.holdings_count === 0 && (
        <p style={{ color: colors.neutral, fontSize: '13px' }}>ยังไม่มีการถือครองหุ้น</p>
      )}
    </div>
  );

  const StatusTab = () => {
    const totalCost = historyData?.total_cost_usd ?? 0;
    const runs = historyData?.runs ?? [];
    const lastRun = runs[0];
    const passCount = runs.filter(r => r.status === 'COMPLETE').length;
    const rejectCount = runs.filter(r => r.status === 'REJECTED').length;

    // Monthly cost summary (จาก /costs/summary — SUM/AVG cost_usd จริง ไม่ใช้ LLM)
    const target = costSummary?.budget?.target_monthly_usd ?? 10;
    const ceiling = costSummary?.budget?.ceiling_monthly_usd ?? 12;
    const projected = costSummary?.projected_month_cost_usd;
    const monthCost = costSummary?.month_to_date?.total_cost_usd ?? 0;
    const budgetStatus = costSummary?.budget?.status;
    const statusColor = budgetStatus === 'over_ceiling' ? colors.error
      : budgetStatus === 'over_target_under_ceiling' ? colors.warning
      : colors.success;
    const statusLabel = budgetStatus === 'over_ceiling' ? '🔴 เกินเพดาน'
      : budgetStatus === 'over_target_under_ceiling' ? '🟡 เกินเป้า แต่ยังไม่เกินเพดาน'
      : budgetStatus === 'within_target' ? '🟢 อยู่ในเป้า'
      : 'กำลังรวบรวมข้อมูล...';
    const barPct = projected ? Math.min((projected / ceiling) * 100, 100) : 0;

    return (
      <div className="space-y-6">
        {/* Monthly cost vs target/ceiling */}
        <div style={{ padding: '20px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.primaryLight}` }}>
          <h3 style={{ color: colors.primary, marginBottom: '15px' }}>💰 Monthly Cost (เป้า ${target} / เพดาน ${ceiling})</h3>
          <div style={{ width: '100%', height: '8px', backgroundColor: colors.surface3, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${barPct}%`, height: '100%', backgroundColor: statusColor }}></div>
          </div>
          <p style={{ color: colors.neutral, fontSize: '12px', marginTop: '8px' }}>
            เดือนนี้ (MTD): ${monthCost.toFixed(2)} · คาดการณ์เต็มเดือน: {projected != null ? `$${projected.toFixed(2)}` : '—'} · {statusLabel}
          </p>
          {costSummary?.by_weekday && (
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(5, 1fr)' : 'repeat(auto-fit, minmax(56px, 1fr))', gap: '6px', marginTop: '14px' }}>
              {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'].map(day => {
                const d = costSummary.by_weekday[day];
                return (
                  <div key={day} style={{ padding: '8px', backgroundColor: colors.surface3, borderRadius: '6px', textAlign: 'center' }}>
                    <p style={{ color: colors.neutral, fontSize: '10px', margin: '0 0 4px 0' }}>{day.slice(0, 3)}</p>
                    <p style={{ color: '#fff', fontSize: '12px', fontWeight: 'bold', margin: 0 }}>
                      {d?.avg_cost_usd != null ? `$${d.avg_cost_usd.toFixed(2)}` : '—'}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Cost summary */}
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(140px, 1fr))', gap: '15px', padding: '15px', backgroundColor: colors.surface2, borderRadius: '8px' }}>
          <div>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Total Spent (all-time)</p>
            <p style={{ color: colors.primary, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>${totalCost.toFixed(2)}</p>
          </div>
          <div>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>PASS / REJECT</p>
            <p style={{ color: colors.success, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              {passCount} / <span style={{ color: colors.error }}>{rejectCount}</span>
            </p>
          </div>
          <div>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>เฉลี่ย/run ล่าสุด</p>
            <p style={{ color: colors.success, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              {costSummary?.recent_avg_cost_per_run_usd != null ? `$${costSummary.recent_avg_cost_per_run_usd.toFixed(3)}` : '—'}
            </p>
          </div>
        </div>

        {/* Last run */}
        {lastRun && (
          <div style={{ padding: '15px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.secondary}` }}>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Last Run</p>
            <p style={{ color: '#fff', fontSize: '13px', margin: '4px 0' }}>
              {new Date(lastRun.timestamp).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok' })}
            </p>
            <p style={{ color: lastRun.status === 'COMPLETE' ? colors.success : colors.error, fontSize: '13px', margin: '4px 0' }}>
              {lastRun.status} — 📈 {lastRun.buy_signals} BUY / ⚖️ {lastRun.hold_signals} HOLD / 📉 {lastRun.sell_signals} SELL
            </p>
            {lastRun.cost_usd > 0 && (
              <p style={{ color: colors.neutral, fontSize: '12px', margin: '4px 0' }}>Cost: ${lastRun.cost_usd?.toFixed(4)}</p>
            )}
          </div>
        )}

        {/* นิก Suggestions */}
        <div style={{ padding: '20px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.secondary}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3 style={{ color: colors.primary, margin: 0 }}>🤖 นิก — Code Suggestions</h3>
            {nikSuggestions?.pending_count > 0 && (
              <span style={{ backgroundColor: '#ffb74d22', color: colors.warning, fontSize: '12px', padding: '3px 10px', borderRadius: '12px', border: `1px solid ${colors.warning}` }}>
                {nikSuggestions.pending_count} pending
              </span>
            )}
          </div>

          {!nikSuggestions && (
            <p style={{ color: colors.neutral, fontSize: '13px' }}>Loading...</p>
          )}

          {nikSuggestions?.suggestions?.length === 0 && (
            <p style={{ color: colors.neutral, fontSize: '13px' }}>ยังไม่มี suggestion จากนิก</p>
          )}

          {nikSuggestions?.suggestions?.map(s => {
            const statusColor = s.status === 'complete' ? colors.success : s.status === 'failed' ? colors.error : colors.warning;
            const statusLabel = s.status === 'complete' ? '✅ Complete' : s.status === 'failed' ? '❌ Failed' : '⏳ Pending';
            const dateStr = new Date(s.created_at).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'short', timeStyle: 'short' });
            return (
              <div key={s.id} style={{ padding: '12px', backgroundColor: colors.surface3, borderRadius: '6px', marginBottom: '10px', border: `1px solid ${statusColor}33` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <p style={{ color: '#fff', fontSize: '13px', fontWeight: 'bold', margin: 0, flex: 1, paddingRight: '12px' }}>{s.summary}</p>
                  <span style={{ color: statusColor, fontSize: '12px', whiteSpace: 'nowrap' }}>{statusLabel}</span>
                </div>
                <p style={{ color: colors.neutral, fontSize: '11px', margin: '0 0 8px 0' }}>{dateStr}</p>
                {s.status === 'failed' && s.error_message && (
                  <p style={{ color: colors.error, fontSize: '11px', margin: '0 0 8px 0' }}>⚠️ {s.error_message}</p>
                )}
                {s.status === 'complete' && s.applied_at && (
                  <p style={{ color: colors.neutral, fontSize: '11px', margin: '0 0 8px 0' }}>
                    applied {new Date(s.applied_at).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'short', timeStyle: 'short' })}
                  </p>
                )}
                {s.status === 'pending' && (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => { navigator.clipboard.writeText(`ดู diff ของ นิก suggestion id=${s.id}: ${s.summary}`); }}
                      style={{ fontSize: '11px', padding: '4px 10px', backgroundColor: 'transparent', border: `1px solid ${colors.neutral}`, color: colors.neutral, borderRadius: '4px', cursor: 'pointer' }}
                    >
                      📋 Copy สำหรับขอ Cow ดู diff
                    </button>
                    <button
                      onClick={() => { navigator.clipboard.writeText(`apply นิก suggestion id=${s.id}: ${s.summary}`); }}
                      style={{ fontSize: '11px', padding: '4px 10px', backgroundColor: 'transparent', border: `1px solid ${colors.primary}`, color: colors.primary, borderRadius: '4px', cursor: 'pointer' }}
                    >
                      ✅ Copy สำหรับขอ Cow apply
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
    switch(activeTab) {
      case 'news': return <NewsTab />;
      case 'stock': return <StockTab />;
      case 'agents': return <AgentsTab />;
      case 'trade': return <TradeTab />;
      case 'portfolio': return <PortfolioTab />;
      case 'stats': return <StatusTab />;
      default: return <NewsTab />;
    }
  };

  // ✅ เพิ่ม 2026-07-03 (รอบ 3): label สั้นสำหรับ bottom nav มือถือ (6 แท็บ ต้องพอดีจอแคบ)
  const tabsMobileShort = {
    news: 'ข่าว', stock: 'หุ้น', agents: 'Agents', trade: 'เทรด', portfolio: 'Port', stats: 'สถานะ'
  };
  const tabEmoji = {
    news: '📰', stock: '📈', agents: '🤖', trade: '💱', portfolio: '💼', stats: '📊'
  };

  // ✅ Bottom nav bar — โครงสร้างมือถือจริง (ไม่ใช่ top tab bar ที่ย่อขนาด) fixed ติดล่างจอ กดง่ายด้วยนิ้วโป้ง
  const BottomNav = () => (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 100,
      display: 'flex', backgroundColor: colors.surface2,
      borderTop: `1px solid ${colors.primaryLight}`,
      paddingBottom: 'env(safe-area-inset-bottom, 0px)'
    }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: '2px', minHeight: '56px', padding: '6px 2px',
            backgroundColor: 'transparent', border: 'none',
            color: activeTab === tab.id ? colors.primary : colors.neutral,
            cursor: 'pointer'
          }}
        >
          <span style={{ fontSize: '20px' }}>{tabEmoji[tab.id]}</span>
          <span style={{ fontSize: '10px', fontWeight: activeTab === tab.id ? 'bold' : 'normal' }}>
            {tabsMobileShort[tab.id]}
          </span>
        </button>
      ))}
    </div>
  );

  return (
    <div style={{
      backgroundColor: colors.surface, minHeight: '100vh',
      padding: isMobile ? '12px' : 'clamp(12px, 4vw, 24px)',
      paddingBottom: isMobile ? '76px' : undefined,
      fontFamily: 'system-ui',
      maxWidth: '100vw', overflowX: 'hidden', boxSizing: 'border-box'
    }}>
      {isMobile ? (
        <h1 style={{ color: colors.primary, fontSize: '18px', fontWeight: 'bold', marginBottom: '14px' }}>
          📊 AI Stock Analyzer
        </h1>
      ) : (
        <>
          <h1 style={{ color: colors.primary, fontSize: '32px', fontWeight: 'bold', marginBottom: '8px' }}>📊 AI Stock Analyzer V4</h1>
          <p style={{ color: colors.neutral, marginBottom: '24px', fontSize: '16px' }}>Smart Investment • Automated Analysis • Sequential Workflow</p>
        </>
      )}

      {!isMobile && (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '10px 16px',
                borderRadius: '8px',
                fontWeight: '500',
                fontSize: '15px',
                backgroundColor: activeTab === tab.id ? colors.primary : colors.surface2,
                color: activeTab === tab.id ? '#fff' : colors.neutral,
                border: `1px solid ${colors.primaryLight}`,
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {renderTab()}

      {isMobile && <BottomNav />}
    </div>
  );
}
