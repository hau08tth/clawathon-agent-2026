# clawathon-agent-2026

Hầu hết nhân viên ngại bán hàng hoặc chia sẻ sản phẩm của công ty vì họ không biết viết văn bản quảng cáo (copywriting), ngại thiết kế hình ảnh, hoặc không biết cách tư vấn. Dự án này sẽ xây dựng một nền tảng/app nội bộ tích hợp Generative AI giúp "bình dân hóa" việc bán hàng cho toàn bộ nhân viên.

## News Summary Agent

Repo này hiện có một GreenNode AgentBase agent tối giản để tóm tắt một trang báo từ URL.

Agent nhận payload:

```json
{
  "url": "https://example.com/news/article",
  "language": "vi",
  "max_words": 500
}
```

Agent trả về tiêu đề, URL nguồn và bản tóm tắt một trang. Nếu có `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, agent dùng endpoint OpenAI-compatible để tạo tóm tắt. Nếu chưa cấu hình LLM, agent vẫn chạy bằng chế độ tóm tắt trích xuất để smoke test local.

## Local Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python main.py
```

Gọi agent:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/news/article","language":"vi","max_words":500}'
```

Health check:

```bash
curl http://localhost:8080/health
```

## Docker

```bash
docker build -t clawathon-news-summary-agent .
docker run --rm -p 8080:8080 --env-file .env clawathon-news-summary-agent
```

## AgentBase Skills

Toàn bộ skills từ `vngcloud/greennode-agentbase-skills` đã được đưa vào project tại:

```text
.agents/skills/
```

Các skill chính gồm `agentbase-wizard`, `agentbase`, `agentbase-deploy`, `agentbase-identity`, `agentbase-llm`, `agentbase-memory`, `agentbase-monitor`, `agentbase-gateway`, `agentbase-policy`, và `agentbase-teardown`.
