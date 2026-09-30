# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Châu Tùng Dương
- **MSSV:** 2A202602822
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/ChauTungDuong/K4-L3-DAY13-ChauTungDuong-2A202602822-Monitoring-LLMOps
- **Commit SHA cuối:** _(điền sau khi nộp)_
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602822`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08a-trace-metadata.png` |
| Generation metadata | `evidence/08b-generation-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Promote & rollback | `evidence/10a-promote.png`, `evidence/10b-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | ≥ 80/100 | CP1 fix correlation ID, metadata enrichment và PII scrubber |
| `validate_dashboard.py` | 6/6 | 6/6 | Dashboard YAML hợp lệ ngay từ đầu |
| `pytest` | 22 passed | 26 passed | Thêm 4 test PII (CCCD + credit card) |
| Số traces hợp lệ | 0 | ≥ 10 | lab-agent-run → retrieval + generation, đủ cây |
| Số PII leak | 0 | 0 | PII scrubber hoạt động từ CP0 |
| Latency P95 / TTFT P95 | ~155ms / 50ms | 2657ms / 50ms | P95 tăng ~17× khi inject rag_slow incident |
| Retrieval success rate | 100% | 100% | Không có tool_fail incident trong challenge |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware `CorrelationIdMiddleware` kiểm tra header `x-request-id` đến — nếu đúng format `req-XXXXXXXX` (8 hex chars) thì dùng, còn lại sinh `req-` + `uuid.uuid4().hex[:8]`. ID được bind vào structlog contextvars, gắn vào `request.state.correlation_id`, và trả về trong response header `x-request-id`.
- **Các metadata được ghi vào structured log:** Mỗi request có: `ts` (UTC ISO), `level`, `event`, `service`, `correlation_id` (từ contextvars), `user_id_hash` (SHA-256 12 ký tự), `session_id`, `feature`, `model`, `env`. `response_sent` thêm: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Hàm `scrub_event` được đăng ký trong structlog processor chain **trước** `JsonlFileProcessor`. Nó scrub field `payload.*` (string) và field `event` bằng regex patterns email, phone_vn, cccd, credit_card.
- **Cách kiểm chứng kết quả:** Gửi request với message chứa email/phone/CCCD/thẻ; kiểm tra log hiện `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]` thay vì giá trị thật. Chạy `python scripts/validate_logs.py` đạt ≥ 80/100.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Langfuse project `day13-k4-l3b-2A202602822` dùng key riêng — mọi trace hiện trong project đó đều do API này sinh ra.
- **Cấu trúc root/retrieval/generation observations:** `day13-agent-request` (root trace) → `lab-agent-run` (agent span, `@observe`) → `retrieval` (span, `@observe` trên `_retrieve`) + `generation` (generation span, `@observe` trên `_generate`). Generation có model, usage (input/output tokens) và cost.
- **Cách nối trace với log:** `correlation_id` được truyền vào `propagate_attributes(metadata={..., "correlation_id": correlation_id})` → hiện trong tab Metadata của `lab-agent-run` trên Langfuse. Cùng `correlation_id` có trong `data/logs.jsonl`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 — labels: `baseline`, `production`
- **Version/label candidate:** v2 — labels: `candidate`
- **Trace ID của mỗi version:** Xem ảnh `10a-promote.png` (production → v2) và `10b-rollback.png` (production → v1). Trace ID cụ thể có trong metadata Langfuse, trường `correlation_id` khớp với log tương ứng.
- **Cách promote và rollback `production`:** Promote: vào Langfuse → Prompts → day13-chat → v2 → Edit labels → thêm `production`. Rollback: làm tương tự với v1. Sau mỗi lần đổi label, restart API và gửi 1 request để confirm.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard Streamlit tại `dashboard/app.py`. 6 panel: Latency (P50/P95/P99/TTFT), Traffic (req/min), Errors (error rate + retrieval success rate), Cost (USD/min), Tokens (tokens_in/out/min), Quality (avg quality_score/min). Mỗi panel có đường threshold màu đỏ.
- **SLO và lý do chọn:** SLO 99.5% `fast_successful_requests`: request phải có `latency_ms ≤ 3000ms`. Ngưỡng 3000ms vì baseline P95 ≈ 410ms, 3000ms là điểm người dùng bắt đầu nhận thấy chậm rõ rệt theo UX research (Miller's Law).
- **Cách tính error budget:** Window 28 ngày ≈ 403,200 request (dựa trên ~10 req/phút). Error budget 0.5% = tối đa 2,016 request được phép chậm hơn 3000ms hoặc lỗi trong 28 ngày.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (P95 > 3000ms / 5 phút), `HighErrorRate` (error_rate > 2% / 5 phút), `LowRetrievalSuccessRate` (retrieval_success < 90% / 10 phút). Runbook chi tiết tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 2026-09-30 12:24–12:25 (ICT / UTC+7) — tương đương 05:24–05:25 UTC
- **Triệu chứng từ metrics:** Dashboard (ảnh `12-incident-metric.png`) cho thấy Latency P95 và P99 đột ngột tăng từ ~155ms (baseline) lên **2657ms** (~17× SLO threshold 3000ms), trong khi error rate vẫn 0% và retrieval success 100% — đây là triệu chứng latency spike thuần túy, không kèm lỗi.
- **Log line và correlation ID liên quan:** `correlation_id: req-68aef9c5` — log (ảnh `13-incident-log.png`) ghi `latency_ms: 2657`, `session_id: k4-l3b-challenge-s04`, `ts: 2026-09-30T05:24:58.065924Z`. Tổng 4 request challenge đều bị ảnh hưởng (req-52ad93ad, req-68aef9c5, req-81ed7305, req-f4f02b8a), latency ~2654–2657ms.
- **Trace ID và span gây ảnh hưởng:** Trace `c1eb1d9d6da74a9204e36390ea09d80f` (ảnh `14-incident-trace.png`). Span **`retrieval` chiếm 2.50s / 2.66s tổng** — chiếm 94% thời gian. Span `generation` chỉ 0.16s. Rõ ràng bottleneck nằm ở bước retrieval.
- **Root cause:** Script `inject_incident.py --scenario rag_slow` thêm delay nhân tạo vào bước vector search/retrieval của `_retrieve()`. Kết quả: mọi request phải chờ retrieval ~2.5s thay vì <200ms baseline. Đây là *slow retrieval* chứ không phải lỗi LLM hay lỗi API — giải thích tại sao HTTP status vẫn 200 và error rate = 0%.
- **Fix action:** (1) Tắt incident: `python scripts/inject_incident.py --scenario rag_slow --disable`. (2) Trong thực tế: thêm index cho vector store, bật caching kết quả retrieval cho query tương tự, hoặc set timeout để fail fast thay vì chờ.
- **Preventive measure:** (1) Tách alert riêng cho retrieval span duration (≥ 500ms → warning, ≥ 1500ms → critical), không chỉ dựa vào end-to-end P95. (2) Export metric `retrieval_duration_ms` từ log/trace vào dashboard. (3) Thêm SLO con cho bước retrieval: P99 ≤ 800ms. (4) Đặt circuit breaker: nếu retrieval timeout > 2s, trả cached/fallback response thay vì block.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt `scrub_event` processor **trước** `JsonlFileProcessor` trong structlog chain để đảm bảo PII không bao giờ được ghi ra file, kể cả khi JsonlFileProcessor fail.
- **Một lỗi/blocker đã gặp:** File `data/logs.jsonl` bị lock bởi API đang chạy nên không Move-Item được. Phải Ctrl+C API trước.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra `Access is denied` → biết file đang bị lock → dừng process → move thành công.
- **Cách hiểu luồng Metrics → Logs → Traces:** Dashboard cho thấy *triệu chứng* (P95 tăng, error_rate tăng) → lọc log bằng `correlation_id` của request bị ảnh hưởng → mở trace trên Langfuse để xem *span nào chậm/lỗi* → kết luận root cause từ evidence.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version cho phép A/B test và rollback an toàn mà không cần deploy lại code; token/cost giúp phát hiện prompt quá dài hoặc cost spike; SLO định nghĩa "tốt" theo tiêu chí user-facing, không phải implementation.
- **Điều quan trọng nhất đã học:** HTTP 200 không có nghĩa là ổn — cần đo latency, token, cost, và quality riêng biệt.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** CP3 đã hoàn thành. Evidence 01–14 đầy đủ. Một hạn chế: dashboard không export metric riêng cho `retrieval_duration_ms`, nên phải dùng Langfuse trace để phân tích root cause — điều này sẽ cải thiện ở lần sau bằng cách ghi thêm field đó vào log.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace (correlation_id: req-68aef9c5).
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân `day13-k4-l3b-2A202602822` và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs. _(điền sau khi commit và push cuối)_
