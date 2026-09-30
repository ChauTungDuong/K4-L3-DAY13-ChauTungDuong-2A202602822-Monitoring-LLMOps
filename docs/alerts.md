# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-2A202602822`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Latency P95 của `response_sent.latency_ms` (ngưỡng SLO 3000ms)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Trải nghiệm người dùng bị chậm, thời gian chờ phản hồi vượt quá ngưỡng chấp nhận được
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở Streamlit dashboard tại panel Latency để xác định thời điểm P95 vượt ngưỡng 3000ms.
  2. **Logs:** Lọc `data/logs.jsonl` tìm các log record `response_sent` có `latency_ms > 3000` để lấy `correlation_id`.
  3. **Traces:** Mở Langfuse Tracing, tìm trace có `correlation_id` tương ứng, kiểm tra span nào (`_retrieve` hay `_generate`) chiếm phần lớn latency.
- Mitigation tạm thời: Nếu do prompt mới làm output token quá dài thì rollback prompt `production` về v1; nếu do retrieval chậm, kiểm tra vector store/mock service hoặc hạ tải.
- Owner: `student-2A202602822`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ lỗi tổng thể `error_rate_pct` (ngưỡng SLO 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng nhận phản hồi lỗi (HTTP 500 hoặc thông báo lỗi hệ thống), dịch vụ gián đoạn
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Kiểm tra panel Errors trên Streamlit dashboard để xác định tỷ lệ lỗi và thời điểm bắt đầu lỗi.
  2. **Logs:** Lọc `data/logs.jsonl` tìm các sự kiện `request_failed`, xem `error_type` và `detail` trong payload cùng `correlation_id`.
  3. **Traces:** Tìm trace của các `correlation_id` bị lỗi trên Langfuse, kiểm tra status span (ERROR) và stack trace exception.
- Mitigation tạm thời: Restart API service, rollback phiên bản code hoặc prompt gần nhất, kiểm tra kết nối API key Langfuse/LLM provider.
- Owner: `student-2A202602822`

## Alert 3

- Tên: `LowRetrievalSuccessRate`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ retrieval thành công `retrieval_success_rate_pct` (ngưỡng SLO 90%)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` trong 10 phút
- Ảnh hưởng tới người dùng: Câu trả lời của AI bị thiếu ngữ cảnh chính xác hoặc AI thông báo không tìm thấy tài liệu
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel Errors trên Dashboard, theo dõi đường biểu diễn `retrieval_success_rate_pct` so với ngưỡng 90%.
  2. **Logs:** Lọc `data/logs.jsonl` tìm các sự kiện có `tool_name: "retrieval"` và `tool_success: false`, lấy `correlation_id`.
  3. **Traces:** Mở Langfuse, kiểm tra span `retrieval` trong trace tương ứng để xem nguyên nhân thất bại (timeout, exception, empty result).
- Mitigation tạm thời: Khởi động lại dịch vụ retrieval/knowledge base, kích hoạt fallback cơ chế retrieval dự phòng.
- Owner: `student-2A202602822`
