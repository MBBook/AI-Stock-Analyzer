"""
test_main.py — ทดสอบ FastAPI endpoints ใน main.py
ครอบคลุม: /health, POST /workflow, LINE notification
ไม่ต่อ DB จริง / ไม่ยิง Claude API จริง
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import importlib
import threading
import time

# ===== MOCK DB + AGENTS ก่อน import main =====
# ป้องกัน main.py ไปต่อ PostgreSQL จริงตอน import

def _make_db_mock():
    mock_db = MagicMock()
    mock_db.__enter__ = lambda s: s
    mock_db.__exit__ = MagicMock(return_value=False)
    return mock_db

# Mock engine ก่อน import
engine_mock = MagicMock()
engine_mock.connect.return_value = _make_db_mock()

# Mock orchestrator ก่อน import
orchestrator_mock = MagicMock()
orchestrator_mock.workflow_log = []

_db_mock_module  = MagicMock(get_db=MagicMock(), engine=engine_mock)
_ag_mock_module  = MagicMock(orchestrator=orchestrator_mock)
_sc_mock_module  = MagicMock(setup_scheduler=MagicMock(), shutdown_scheduler=MagicMock())

with patch.dict("sys.modules", {
    "database": _db_mock_module,
    "agents":   _ag_mock_module,
    "scheduler": _sc_mock_module,
}):
    import main as app_module
    from fastapi.testclient import TestClient

# patch.dict restores sys.modules on exit → main + deps ถูก remove ออก
# ต้อง re-inject เพื่อให้ patch("main.requests.post") หา module เจอ
sys.modules["main"]      = app_module
sys.modules["database"]  = _db_mock_module
sys.modules["scheduler"] = _sc_mock_module
# ไม่ re-inject "agents" — ถ้า test_agents.py โหลด real agents ไว้แล้ว
# จะถูก overwrite ทำให้ TestHarryPortfolio/TestCheckpoint พัง
# app_module.orchestrator ชี้ไปที่ orchestrator_mock อยู่แล้วจากตอน import

# Reset _job state ก่อนแต่ละ test
def _reset_job():
    with app_module._job_lock:
        app_module._job.update({
            "job_id": None,
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        })

# DB override — คืน mock session แทน real DB
def _override_get_db():
    db = MagicMock()
    try:
        yield db
    finally:
        pass

app_module.app.dependency_overrides[app_module.get_db] = _override_get_db

# ✅ 2026-07-11: baseline ของ test ทั้งไฟล์ = auth ปิดเสมอ — main.py รัน load_dotenv() ตอน import
# ทำให้เครื่องที่มี DASHBOARD_PASSWORD ใน .env (เครื่อง MBBook ตั้งไว้จริงตั้งแต่ 07-09) auth เปิด
# โดยไม่ตั้งใจ → endpoint ที่ยิงแบบไม่มี token (เช่น TestNikSuggestionsEndpoint) โดน 401 ทั้งชุด
# (เจอจริง: pytest บนเครื่อง MBBook fail 5 ตัว แต่ใน sandbox ที่ไม่มี .env ผ่านหมด)
# คลาสที่ทดสอบ auth โดยเฉพาะ (TestDashboardAuth/TestLoginRateLimit) ตั้ง env เองผ่าน
# patch.dict อยู่แล้ว ไม่กระทบ
os.environ.pop("DASHBOARD_PASSWORD", None)


# ============================================================
# 1. GET /health
# ============================================================
class TestHealth(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app_module.app)

    def test_health_returns_200(self):
        """GET /health ต้องได้ HTTP 200 เสมอ"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_returns_ok_status(self):
        """GET /health body ต้องมี status=ok"""
        resp = self.client.get("/health")
        self.assertEqual(resp.json().get("status"), "ok")

    def test_health_is_fast(self):
        """GET /health ต้องตอบกลับภายใน 1 วินาที"""
        start = time.time()
        self.client.get("/health")
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0, "Health endpoint ช้าเกินไป")


# ============================================================
# 2. POST /workflow
# ============================================================
class TestWorkflowEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app_module.app)
        _reset_job()

    def _make_db_with_stocks(self, tickers=None):
        """คืน mock DB ที่มีหุ้นอยู่ใน list"""
        if tickers is None:
            tickers = ["AAPL", "MSFT", "GOOGL"]
        db = MagicMock()
        stocks = [MagicMock(ticker=t) for t in tickers]
        db.query.return_value.all.return_value = stocks
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    def test_workflow_starts_immediately_no_blocking(self):
        """POST /workflow ต้องตอบกลับทันที ไม่รอ workflow เสร็จ"""
        app_module.app.dependency_overrides[app_module.get_db] = \
            lambda: (yield self._make_db_with_stocks())

        # ✅ แก้ 2026-07-04: patch("threading.Thread") แบบ global เดิม ไปดักโดน thread
        # ภายในของ starlette TestClient (anyio blocking portal) ด้วย ทำให้ portal ไม่เคย
        # start จริง → self.client.post() ค้างรอ portal ตลอดไป (เจอผ่าน pytest-timeout)
        # แก้โดยเช็คก่อนว่า target ตรงกับ _run_workflow_bg จริงมั้ย ถ้าไม่ใช่ให้ผ่านไปที่ thread จริง
        original_thread = threading.Thread

        def fake_thread(**kwargs):
            if kwargs.get("target") is app_module._run_workflow_bg:
                t = MagicMock()
                t.start = MagicMock()
                return t
            return original_thread(**kwargs)

        with patch.object(app_module, "_run_workflow_bg"):
            with patch("threading.Thread", side_effect=fake_thread):
                start = time.time()
                resp = self.client.post("/workflow")
                elapsed = time.time() - start

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "started")
        self.assertLess(elapsed, 2.0, "POST /workflow blocking — ไม่ควรรอ workflow เสร็จ")

    def test_workflow_normal_mode_flag_false(self):
        """POST /workflow ไม่ส่ง include_weekend → thread รันด้วย include_weekend=False"""
        app_module.app.dependency_overrides[app_module.get_db] = \
            lambda: (yield self._make_db_with_stocks())

        captured = {}
        original_thread = threading.Thread

        def capture_thread(**kwargs):
            # ✅ แก้ 2026-07-04: ดักเฉพาะ thread ของ _run_workflow_bg เท่านั้น — เรื่องเดียวกับ
            # test_workflow_starts_immediately_no_blocking ด้านบน (anyio portal hang)
            if kwargs.get("target") is app_module._run_workflow_bg:
                captured["args"] = kwargs.get("args", ())
                t = MagicMock()
                t.start = MagicMock()
                return t
            return original_thread(**kwargs)

        with patch("threading.Thread", side_effect=capture_thread):
            resp = self.client.post("/workflow")

        self.assertEqual(resp.json()["status"], "started")
        # args = (stocks, include_weekend)
        if captured.get("args"):
            self.assertFalse(captured["args"][1], "include_weekend ควรเป็น False")

    def test_workflow_monday_mode_flag_true(self):
        """POST /workflow?include_weekend=true → thread รันด้วย include_weekend=True"""
        app_module.app.dependency_overrides[app_module.get_db] = \
            lambda: (yield self._make_db_with_stocks())

        captured = {}
        original_thread = threading.Thread

        def capture_thread(**kwargs):
            # ✅ แก้ 2026-07-04: เหตุผลเดียวกับสองเทสต์ด้านบน — ดักเฉพาะ target ที่ตรงกันจริง
            if kwargs.get("target") is app_module._run_workflow_bg:
                captured["args"] = kwargs.get("args", ())
                t = MagicMock()
                t.start = MagicMock()
                return t
            return original_thread(**kwargs)

        with patch("threading.Thread", side_effect=capture_thread):
            resp = self.client.post("/workflow?include_weekend=true")

        self.assertEqual(resp.json()["status"], "started")
        if captured.get("args"):
            self.assertTrue(captured["args"][1], "include_weekend ควรเป็น True (Monday mode)")

    def test_workflow_already_running_returns_already_running(self):
        """POST /workflow ขณะที่ workflow กำลังรันอยู่ → ต้องได้ already_running"""
        with app_module._job_lock:
            app_module._job["status"] = "running"
            app_module._job["job_id"] = "test-001"
            app_module._job["started_at"] = "2026-06-26T22:00:00"

        resp = self.client.post("/workflow")
        self.assertEqual(resp.json()["status"], "already_running")

    def test_workflow_no_stocks_returns_no_stocks(self):
        """POST /workflow เมื่อไม่มีหุ้นใน DB → ต้องได้ no_stocks"""
        db_empty = MagicMock()
        db_empty.query.return_value.all.return_value = []
        app_module.app.dependency_overrides[app_module.get_db] = \
            lambda: (yield db_empty)

        resp = self.client.post("/workflow")
        self.assertEqual(resp.json()["status"], "no_stocks")

    def test_workflow_response_has_job_id(self):
        """POST /workflow response ต้องมี job_id"""
        app_module.app.dependency_overrides[app_module.get_db] = \
            lambda: (yield self._make_db_with_stocks())

        # ✅ แก้ 2026-07-04: เหตุผลเดียวกับ test_workflow_monday_mode_flag_true ด้านบน
        original_thread = threading.Thread

        def fake_thread(**kwargs):
            if kwargs.get("target") is app_module._run_workflow_bg:
                t = MagicMock()
                t.start = MagicMock()
                return t
            return original_thread(**kwargs)

        with patch("threading.Thread", side_effect=fake_thread):
            resp = self.client.post("/workflow")

        self.assertIn("job_id", resp.json())
        self.assertIsNotNone(resp.json()["job_id"])

    def test_workflow_sets_status_to_running(self):
        """POST /workflow ต้องเปลี่ยน _job status เป็น running"""
        app_module.app.dependency_overrides[app_module.get_db] = \
            lambda: (yield self._make_db_with_stocks())

        original_thread = threading.Thread

        def fake_thread(**kwargs):
            if kwargs.get("target") is app_module._run_workflow_bg:
                t = MagicMock()
                t.start = MagicMock()
                return t
            return original_thread(**kwargs)

        with patch("threading.Thread", side_effect=fake_thread):
            self.client.post("/workflow")

        with app_module._job_lock:
            self.assertEqual(app_module._job["status"], "running")


# ============================================================
# 3. POST /workflow/resume
# ============================================================
class TestWorkflowResume(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app_module.app)
        _reset_job()

    def test_resume_already_running_skips(self):
        """POST /workflow/resume ขณะที่ workflow รันอยู่ → already_running"""
        with app_module._job_lock:
            app_module._job["status"] = "running"

        db = MagicMock()
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        resp = self.client.post("/workflow/resume")
        self.assertEqual(resp.json()["status"], "already_running")

    def test_resume_all_done_today_returns_complete(self):
        """POST /workflow/resume เมื่อทุกตัว updated_at=today → already_complete"""
        from datetime import date
        today_dt = MagicMock()
        today_dt.date.return_value = date.today()

        db = MagicMock()
        stocks = [MagicMock(ticker="AAPL", updated_at=today_dt),
                  MagicMock(ticker="MSFT", updated_at=today_dt)]
        db.query.return_value.all.return_value = stocks
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        resp = self.client.post("/workflow/resume")
        self.assertEqual(resp.json()["status"], "already_complete")

    def test_resume_pending_stocks_starts_workflow(self):
        """POST /workflow/resume เมื่อมีหุ้นค้างอยู่ → ต้องได้ resumed"""
        db = MagicMock()
        # updated_at = None หมายถึงยังไม่เคยวิเคราะห์
        stocks = [MagicMock(ticker="AAPL", updated_at=None),
                  MagicMock(ticker="MSFT", updated_at=None)]
        db.query.return_value.all.return_value = stocks
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        # ✅ แก้ 2026-07-04: เหตุผลเดียวกับ test_workflow_monday_mode_flag_true ด้านบน
        original_thread = threading.Thread

        def fake_thread(**kwargs):
            if kwargs.get("target") is app_module._run_workflow_bg:
                t = MagicMock()
                t.start = MagicMock()
                return t
            return original_thread(**kwargs)

        with patch("threading.Thread", side_effect=fake_thread):
            resp = self.client.post("/workflow/resume")

        self.assertEqual(resp.json()["status"], "resumed")
        self.assertEqual(resp.json()["pending_stocks"], 2)


# ============================================================
# 4. LINE Notification — เซิร์ฟเวอร์ต้องไม่พัง
# ============================================================
class TestLineNotification(unittest.TestCase):

    def test_no_token_no_crash(self):
        """ไม่มี LINE_CHANNEL_ACCESS_TOKEN → ฟังก์ชันต้องไม่ raise"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)
            os.environ.pop("LINE_USER_ID", None)
            try:
                app_module._send_line_notification("test message")
            except Exception as e:
                self.fail(f"_send_line_notification raise unexpected: {e}")

    def test_network_error_no_crash(self):
        """requests.post raise ConnectionError → เซิร์ฟเวอร์ต้องไม่พัง"""
        with patch.dict(os.environ, {
            "LINE_CHANNEL_ACCESS_TOKEN": "fake-token",
            "LINE_USER_ID": "fake-user"
        }):
            with patch("main.requests.post", side_effect=ConnectionError("network down")):
                try:
                    app_module._send_line_notification("test")
                except Exception as e:
                    self.fail(f"Server crashed on network error: {e}")

    def test_timeout_no_crash(self):
        """requests.post raise Timeout → เซิร์ฟเวอร์ต้องไม่พัง"""
        import requests as req
        with patch.dict(os.environ, {
            "LINE_CHANNEL_ACCESS_TOKEN": "fake-token",
            "LINE_USER_ID": "fake-user"
        }):
            with patch("main.requests.post", side_effect=req.exceptions.Timeout):
                try:
                    app_module._send_line_notification("test")
                except Exception as e:
                    self.fail(f"Server crashed on timeout: {e}")

    def test_api_400_no_crash(self):
        """LINE API คืน 400 Bad Request → เซิร์ฟเวอร์ต้องไม่พัง"""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Invalid token"
        with patch.dict(os.environ, {
            "LINE_CHANNEL_ACCESS_TOKEN": "bad-token",
            "LINE_USER_ID": "fake-user"
        }):
            with patch("main.requests.post", return_value=mock_resp):
                try:
                    app_module._send_line_notification("test")
                except Exception as e:
                    self.fail(f"Server crashed on 400 response: {e}")

    def test_api_500_no_crash(self):
        """LINE API คืน 500 Server Error → เซิร์ฟเวอร์ต้องไม่พัง"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch.dict(os.environ, {
            "LINE_CHANNEL_ACCESS_TOKEN": "fake-token",
            "LINE_USER_ID": "fake-user"
        }):
            with patch("main.requests.post", return_value=mock_resp):
                try:
                    app_module._send_line_notification("test")
                except Exception as e:
                    self.fail(f"Server crashed on 500 response: {e}")

    def test_empty_message_no_crash(self):
        """ส่ง message ว่าง → ต้องไม่พัง"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.dict(os.environ, {
            "LINE_CHANNEL_ACCESS_TOKEN": "fake-token",
            "LINE_USER_ID": "fake-user"
        }):
            with patch("main.requests.post", return_value=mock_resp):
                try:
                    app_module._send_line_notification("")
                except Exception as e:
                    self.fail(f"Server crashed on empty message: {e}")


# ============================================================
# 5. Bonus: _run_workflow_bg error handling
# ============================================================
class TestWorkflowBackground(unittest.TestCase):

    def setUp(self):
        _reset_job()

    def test_bg_exception_sets_error_status(self):
        """ถ้า orchestrator.run_workflow raise → _job status ต้องเป็น error ไม่ crash"""
        app_module.orchestrator.run_workflow.side_effect = RuntimeError("Claude API down")

        with patch("main._send_line_notification"):
            app_module._run_workflow_bg(["AAPL"], False)

        with app_module._job_lock:
            self.assertEqual(app_module._job["status"], "error")
            self.assertIn("Claude API down", app_module._job["error"])

    def test_bg_exception_sends_line_notification(self):
        """ถ้า workflow พัง → ต้องส่ง LINE แจ้ง MBBook เสมอ"""
        app_module.orchestrator.run_workflow.side_effect = RuntimeError("crash")

        with patch("main._send_line_notification") as mock_line:
            app_module._run_workflow_bg(["AAPL"], False)

        mock_line.assert_called_once()
        call_msg = mock_line.call_args[0][0]
        self.assertIn("ล้มเหลว", call_msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ============================================================
# 6. GET /nik/suggestions
# ============================================================
class TestNikSuggestionsEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app_module.app)
        # test_agents.py set sys.modules["models"] = MagicMock() ตลอด session
        # desc(NikSuggestion.created_at) ใน endpoint ต้องการ Column จริง ไม่ใช่ Mock
        # restore real models ชั่วคราวระหว่าง test class นี้
        import importlib
        self._orig_models = sys.modules.get("models")
        # ต้อง pop ก่อน ไม่งั้น import_module คืน cache MagicMock เดิม
        sys.modules.pop("models", None)
        try:
            sys.modules["models"] = importlib.import_module("models")
        except Exception:
            if self._orig_models:
                sys.modules["models"] = self._orig_models

    def tearDown(self):
        if self._orig_models is not None:
            sys.modules["models"] = self._orig_models

    def _make_suggestion(self, id, status="pending", summary="แก้ timeout", diff="<<<DIFF>>>"):
        from datetime import datetime as dt
        s = MagicMock()
        s.id            = id
        s.created_at    = dt(2026, 6, 26, 10, 0, 0)
        s.summary       = summary
        s.diff_text     = diff
        s.status        = status
        s.error_message = None
        s.applied_at    = None
        return s

    def test_empty_db_returns_zero_count(self):
        """ไม่มี suggestion ใน DB → count=0, suggestions=[]"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        resp = self.client.get("/nik/suggestions")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)
        self.assertEqual(resp.json()["suggestions"], [])

    def test_response_has_required_fields(self):
        """response ต้องมี count, pending_count, suggestions"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            self._make_suggestion(1, status="pending")
        ]
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        resp = self.client.get("/nik/suggestions")
        data = resp.json()
        self.assertIn("count",         data)
        self.assertIn("pending_count", data)
        self.assertIn("suggestions",   data)

    def test_pending_count_correct(self):
        """pending_count นับเฉพาะ status=pending"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            self._make_suggestion(1, status="pending"),
            self._make_suggestion(2, status="complete"),
            self._make_suggestion(3, status="pending"),
        ]
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        resp = self.client.get("/nik/suggestions")
        self.assertEqual(resp.json()["pending_count"], 2)
        self.assertEqual(resp.json()["count"], 3)

    def test_suggestion_item_has_required_fields(self):
        """แต่ละ item ใน suggestions ต้องมีฟิลด์ครบ"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
            self._make_suggestion(1, status="pending", summary="แก้ timeout")
        ]
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        resp = self.client.get("/nik/suggestions")
        item = resp.json()["suggestions"][0]
        for field in ["id", "created_at", "summary", "diff_text", "status",
                      "error_message", "applied_at"]:
            self.assertIn(field, item, f"Missing field: {field}")

    def test_limit_10_records(self):
        """ต้อง limit 10 เท่านั้น — ไม่ดึงทั้งหมด"""
        db = MagicMock()
        limit_mock = MagicMock()
        limit_mock.all.return_value = []
        db.query.return_value.order_by.return_value.limit.return_value = limit_mock
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

        self.client.get("/nik/suggestions")
        db.query.return_value.order_by.return_value.limit.assert_called_with(10)

# ============================================================
# SECTION: Dashboard Auth (ระบบ password — เพิ่ม 2026-07-09)
# ============================================================
import hashlib as _hashlib


class TestDashboardAuth(unittest.TestCase):
    """DASHBOARD_PASSWORD auth — middleware + /auth/login
    หลัก: ไม่ตั้ง env = auth ปิด (backward compat) / ตั้งแล้ว endpoint ข้อมูลต้องมี X-Auth-Token
    ส่วน endpoint ที่ cron-job.org ใช้ (/health, /workflow, /workflow/resume, /prefetch) เปิดเสมอ"""

    PW = "test-secret-123"
    TOKEN = _hashlib.sha256(f"dash:test-secret-123".encode()).hexdigest()

    def setUp(self):
        _reset_job()
        self.client = TestClient(app_module.app)

    # --- auth ปิด (ไม่ตั้ง env) ---
    def test_no_env_auth_disabled_protected_route_open(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DASHBOARD_PASSWORD", None)
            resp = self.client.get("/workflow/status")
            self.assertEqual(resp.status_code, 200)

    def test_no_env_login_returns_auth_disabled_flag(self):
        os.environ.pop("DASHBOARD_PASSWORD", None)
        resp = self.client.post("/auth/login", json={"password": "anything"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("auth_disabled"))

    # --- auth เปิด ---
    def test_protected_route_without_token_401(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.get("/workflow/status")
            self.assertEqual(resp.status_code, 401)

    def test_protected_route_wrong_token_401(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.get("/workflow/status", headers={"X-Auth-Token": "wrong"})
            self.assertEqual(resp.status_code, 401)

    def test_protected_route_with_token_200(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.get("/workflow/status", headers={"X-Auth-Token": self.TOKEN})
            self.assertEqual(resp.status_code, 200)

    def test_login_correct_password_returns_token(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.post("/auth/login", json={"password": self.PW})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["token"], self.TOKEN)

    def test_login_wrong_password_401(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.post("/auth/login", json={"password": "guess"})
            self.assertEqual(resp.status_code, 401)

    def test_health_stays_public_when_auth_on(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.get("/health")
            self.assertEqual(resp.status_code, 200)

    def test_options_preflight_not_blocked(self):
        """OPTIONS (CORS preflight) ต้องไม่โดน 401 — ไม่งั้น browser ยิงอะไรไม่ได้เลย"""
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.options("/stocks")
            self.assertNotEqual(resp.status_code, 401)

    def test_401_response_has_cors_header(self):
        """401 จาก middleware อยู่นอก CORSMiddleware — ต้องใส่ ACAO เองให้ browser อ่าน status ได้"""
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            resp = self.client.get("/workflow/status")
            self.assertEqual(resp.headers.get("access-control-allow-origin"), "*")

class TestLoginRateLimit(unittest.TestCase):
    """Lockout หน้า login (เพิ่ม 2026-07-09 รอบ 2 — รองรับ PIN 6 หลัก):
    ผิดครบ LOGIN_MAX_FAILS ครั้ง → 429 ล็อก LOGIN_LOCK_MINUTES นาที แม้ใส่รหัสถูกก็ต้องรอ"""

    PW = "482913"

    def setUp(self):
        _reset_job()
        app_module._login_attempts.clear()
        self.client = TestClient(app_module.app)

    def test_lockout_after_max_fails(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            for _ in range(app_module.LOGIN_MAX_FAILS):
                resp = self.client.post("/auth/login", json={"password": "000000"})
                self.assertEqual(resp.status_code, 401)
            resp = self.client.post("/auth/login", json={"password": "000000"})
            self.assertEqual(resp.status_code, 429)

    def test_locked_even_with_correct_password(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            for _ in range(app_module.LOGIN_MAX_FAILS):
                self.client.post("/auth/login", json={"password": "000000"})
            resp = self.client.post("/auth/login", json={"password": self.PW})
            self.assertEqual(resp.status_code, 429)  # ล็อกคือล็อก — เหมือนแอปธนาคาร

    def test_success_resets_fail_count(self):
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            for _ in range(app_module.LOGIN_MAX_FAILS - 1):
                self.client.post("/auth/login", json={"password": "000000"})
            resp = self.client.post("/auth/login", json={"password": self.PW})
            self.assertEqual(resp.status_code, 200)  # ยังไม่ครบ 5 → เข้าได้
            # หลังเข้าถูก ประวัติผิดถูกล้าง — ผิดอีก 1 ครั้งต้องยังเป็น 401 ไม่ใช่ 429
            resp = self.client.post("/auth/login", json={"password": "000000"})
            self.assertEqual(resp.status_code, 401)

    def test_lock_expires_after_window(self):
        from datetime import datetime as _dt, timedelta as _td
        with patch.dict(os.environ, {"DASHBOARD_PASSWORD": self.PW}):
            for _ in range(app_module.LOGIN_MAX_FAILS):
                self.client.post("/auth/login", json={"password": "000000"})
            # ย้อน lock_until ให้หมดอายุแล้ว → ต้องเข้าได้ปกติ
            for rec in app_module._login_attempts.values():
                rec["lock_until"] = _dt.utcnow() - _td(seconds=1)
            resp = self.client.post("/auth/login", json={"password": self.PW})
            self.assertEqual(resp.status_code, 200)


# ============================================================
# 8. GET /news (✅ เพิ่ม 2026-07-11 — ปิดงานค้าง #51: ข่าวจริงจาก news_cache)
# ============================================================
class TestNewsEndpoint(unittest.TestCase):
    """หน้า News เดิมโชว์ MOCK_NEWS 4 ข่าววนซ้ำ — endpoint นี้คือท่อส่งข่าวจริงชุดแรก
    ต้องกัน 3 เคสหลัก: cache ว่าง / dedup ข่าวเดียวกันข้าม ticker / news_json เสียห้ามล้มทั้ง endpoint"""

    def setUp(self):
        self.client = TestClient(app_module.app)

    def _override_db_rows(self, rows):
        db = MagicMock()
        # /news เรียก db.query 2 ครั้ง: (1) subquery หา fetched_at ล่าสุดต่อ ticker (chain MagicMock
        # เฉยๆ ไม่ต้อง setup) (2) db.query(NewsCache).join(...).all() → คืน rows ที่ seed ไว้
        db.query.return_value.join.return_value.all.return_value = rows
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)

    def test_news_empty_cache_returns_empty_list(self):
        """cache ว่าง → 200 + articles [] (ไม่ error)"""
        self._override_db_rows([])
        resp = self.client.get("/news")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)
        self.assertEqual(resp.json()["articles"], [])

    def test_news_dedup_across_tickers_and_sort(self):
        """ข่าวเดียวกันโผล่ 2 ticker → รวมเป็นข่าวเดียว (tickers 2 ตัว) + เรียงใหม่→เก่า"""
        import json as _json
        shared = {"title": "NVIDIA and partner announce quantum computing deal",
                  "summary": "s1", "source": "Reuters", "published_at": 2000, "from_source": "finnhub"}
        solo = {"title": "Micron faces NAND pricing pressure",
                "summary": "s2", "source": "Bloomberg", "published_at": 3000, "from_source": "yfinance"}
        rows = [
            MagicMock(ticker="NVDA", news_json=_json.dumps([shared])),
            MagicMock(ticker="IONQ", news_json=_json.dumps([shared])),
            MagicMock(ticker="MU",   news_json=_json.dumps([solo])),
        ]
        self._override_db_rows(rows)
        resp = self.client.get("/news")
        data = resp.json()
        self.assertEqual(data["count"], 2)  # 3 รายการดิบ → dedup เหลือ 2
        # เรียงตาม published_at ใหม่→เก่า: MU (3000) ก่อน NVDA/IONQ (2000)
        self.assertEqual(data["articles"][0]["tickers"], ["MU"])
        self.assertEqual(sorted(data["articles"][1]["tickers"]), ["IONQ", "NVDA"])
        # id ต้อง deterministic (md5 จาก title) — ยิงซ้ำได้ id เดิม (ระบบ mark อ่านแล้วฝั่ง frontend พึ่งสิ่งนี้)
        resp2 = self.client.get("/news")
        self.assertEqual(data["articles"][0]["id"], resp2.json()["articles"][0]["id"])

    def test_news_broken_json_row_skipped_not_500(self):
        """news_json เสีย 1 แถว → ข้ามแถวนั้น ข่าวจาก ticker อื่นยังมาครบ (ห้าม 500)"""
        import json as _json
        good = {"title": "WDC beats earnings estimates", "summary": "", "source": "CNBC",
                "published_at": 1000, "from_source": "yfinance"}
        rows = [
            MagicMock(ticker="NVDA", news_json="{broken json!!"),
            MagicMock(ticker="WDC",  news_json=_json.dumps([good])),
        ]
        self._override_db_rows(rows)
        resp = self.client.get("/news")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)
        self.assertEqual(resp.json()["articles"][0]["headline"], "WDC beats earnings estimates")

