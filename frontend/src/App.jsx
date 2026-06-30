import React, { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const API_URL = 'https://ai-stock-analyzer-msli.onrender.com';

export default function DashboardV4() {
  const [activeTab, setActiveTab] = useState('news');
  const [hideBalance, setHideBalance] = useState(false);
  const [stocks, setStocks] = useState([]);
  const [newTicker, setNewTicker] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [tradeInput, setTradeInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [portfolioData, setPortfolioData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [nikSuggestions, setNikSuggestions] = useState(null);

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
              padding: '10px 20px',
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
        <h2 style={{ color: colors.primary, marginBottom: '15px' }}>💱 Trade Update</h2>
        <textarea
          value={tradeInput}
          onChange={(e) => setTradeInput(e.target.value)}
          placeholder="BUY AAPL 100 shares at $150..."
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: colors.surface3,
            color: '#fff',
            border: `1px solid ${colors.primary}`,
            borderRadius: '6px',
            minHeight: '100px'
          }}
        />
        <button style={{ 
          marginTop: '12px',
          padding: '10px 20px',
          backgroundColor: colors.primary,
          color: '#fff',
          border: 'none',
          borderRadius: '6px',
          cursor: 'pointer',
          fontWeight: 'bold'
        }}>
          Submit to โคลสัน
        </button>
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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
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
    </div>
  );

  const StatusTab = () => {
    const totalCost = historyData?.total_cost_usd ?? 0;
    const runs = historyData?.runs ?? [];
    const budget = 30;
    const budgetUsedPct = Math.min((totalCost / budget) * 100, 100).toFixed(0);
    const lastRun = runs[0];
    const passCount = runs.filter(r => r.status === 'COMPLETE').length;
    const rejectCount = runs.filter(r => r.status === 'REJECTED').length;

    return (
      <div className="space-y-6">
        {/* Budget usage */}
        <div style={{ padding: '20px', backgroundColor: colors.surface2, borderRadius: '8px', border: `1px solid ${colors.primaryLight}` }}>
          <h3 style={{ color: colors.primary, marginBottom: '15px' }}>💰 Budget Usage</h3>
          <div style={{ width: '100%', height: '8px', backgroundColor: colors.surface3, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${budgetUsedPct}%`, height: '100%', backgroundColor: totalCost > 25 ? colors.error : colors.primary }}></div>
          </div>
          <p style={{ color: colors.neutral, fontSize: '12px', marginTop: '8px' }}>
            ${totalCost.toFixed(2)} / ${budget} ({budgetUsedPct}%) — {historyData ? `${runs.length} runs` : 'Loading...'}
          </p>
        </div>

        {/* Cost summary */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px', padding: '15px', backgroundColor: colors.surface2, borderRadius: '8px' }}>
          <div>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Total Spent</p>
            <p style={{ color: colors.primary, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>${totalCost.toFixed(2)}</p>
          </div>
          <div>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>PASS / REJECT</p>
            <p style={{ color: colors.success, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              {passCount} / <span style={{ color: colors.error }}>{rejectCount}</span>
            </p>
          </div>
          <div>
            <p style={{ color: colors.neutral, fontSize: '12px', margin: '0 0 8px 0' }}>Budget Left</p>
            <p style={{ color: budget - totalCost < 5 ? colors.error : colors.success, fontSize: '18px', fontWeight: 'bold', margin: 0 }}>
              ${(budget - totalCost).toFixed(2)}
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

  return (
    <div style={{ backgroundColor: colors.surface, minHeight: '100vh', padding: '24px', fontFamily: 'system-ui' }}>
      <h1 style={{ color: colors.primary, fontSize: '32px', fontWeight: 'bold', marginBottom: '8px' }}>📊 AI Stock Analyzer V4</h1>
      <p style={{ color: colors.neutral, marginBottom: '24px' }}>Smart Investment • Automated Analysis • Sequential Workflow</p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 16px',
              borderRadius: '8px',
              fontWeight: '500',
              backgroundColor: activeTab === tab.id ? colors.primary : colors.surface2,
              color: activeTab === tab.id ? '#fff' : colors.neutral,
              border: `1px solid ${colors.primaryLight}`,
              cursor: 'pointer'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {renderTab()}
    </div>
  );
}
