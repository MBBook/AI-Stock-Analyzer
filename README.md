# AI Stock Analyzer - Backend

Multi-agent AI system for stock analysis using Claude API.

## Architecture

```
Sequential Workflow (Daily 22:00):
START → นัตตี้ (News) → หนุ่ม (Stock Analysis) → มด (Validate)
→ แฮรี่ (Portfolio) → เจน (Report) → นน (QA Check)
├─ PASS → Update Dashboard
└─ REJECT → เก้า (Retry)
```

## Tech Stack

- **Backend:** Python + FastAPI
- **AI:** Anthropic Claude API
- **Database:** PostgreSQL
- **Data:** yfinance
- **Scheduling:** APScheduler
- **Deploy:** Railway

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your values:
# - ANTHROPIC_API_KEY
# - DATABASE_URL (PostgreSQL)
```

### 3. Database
```bash
# Create PostgreSQL database
createdb ai_stock_analyzer

# Connect string:
postgresql://username:password@localhost/ai_stock_analyzer
```

### 4. Run Locally
```bash
python main.py
# Server at http://localhost:8000
```

## API Endpoints

```
GET     /                    Health check
GET     /stocks              Get all tracked stocks
POST    /stocks              Add stock (ticker)
DELETE  /stocks/{ticker}     Remove stock
GET     /portfolio           Portfolio summary
POST    /trade-update        Record trade
GET     /analysis/latest     Latest workflow result
```

## Agents

| Agent | Role | Model | Trigger |
|-------|------|-------|---------|
| นัตตี้ | Get news | Opus | Daily 22:00 |
| หนุ่ม | Analyze stocks | Opus | After นัตตี้ |
| มด | Cross-validate | Opus | After หนุ่ม |
| แฮรี่ | Monitor portfolio | Sonnet | After มด |
| เจน | Generate report | Sonnet | After แฮรี่ |
| นน | QA check | Sonnet | After เจน |
| เก้า | Retry manager | Sonnet | On error |
| โคลสัน | Trade updates | Manual | User prompt |
| นิก | Optimize | Opus | Every Friday |
| เอ | Record improvements | Opus | After QA pass |

## Deployment (Railway)

```bash
1. Push to GitHub
2. Connect GitHub to Railway
3. Add environment variables
4. Auto-deploy on push
5. Database: Railway PostgreSQL
```

## Cost Estimate

- **Daily tokens:** ~40,850
- **Monthly:** ~1,548,100 tokens
- **Cost:** ~$9.35/month (Opus + Sonnet mix)
- **Budget:** $30/month

## Next Steps

1. ✅ Prototype complete
2. ⏳ Build actual backend
3. ⏳ Integrate PostgreSQL
4. ⏳ Connect frontend
5. ⏳ Deploy to Railway
6. ⏳ Test workflow
7. ⏳ Launch production

## Notes

- Workflow is **SEQUENTIAL** (not parallel)
- Daily run at 22:00 Thailand time
- Retry up to 3x on failure
- Uses old data if all retries fail
