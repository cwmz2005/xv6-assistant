# xv6 RAG 知识检索与问答

本项目使用 FastAPI、PostgreSQL + pgvector，以及本地 CPU Embedding 和 Reranker。前端使用 pnpm、Vite、React、TypeScript、Ant Design，Markdown 渲染使用 react-markdown。

## 后端启动

保留已有 .env；新环境参考 .env.example。数据库需启用 vector 扩展，应用账户需具有 public schema 建表权限。WSL 数据库需要先启动。

```powershell
uv sync
uv run python -m backend.init_db
uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

API 文档：http://127.0.0.1:8000/docs。

## 前端启动

```powershell
cd frontend
pnpm install
pnpm dev
```

开发服务通过 Vite 代理 /api 到后端。构建命令为 pnpm build。需要可用的 Node.js 环境。

## 模型

Embedding 使用 intfloat/multilingual-e5-small，384 维，本地 CPU 推理，添加 query: 和 passage: 前缀。Reranker 使用 BAAI/bge-reranker-base，按需缓存。无需 CUDA。

大陆网络可设置 HF_ENDPOINT=https://hf-mirror.com，或使用 HTTP_PROXY、HTTPS_PROXY。缓存位置遵循 HF_HOME。

LLM 配置读取 LLM_BASE_URL、LLM_API_KEY、LLM_MODEL。未配置时问答返回 503，不伪造结果。

## 导入

POST /api/import，请求示例：

```json
{"root":"data/xv6-labs-2022-impl","commit":"dc9153f"}
```

该提交位于 util 分支的个人修改之前；其他实验分支必须分别审计，不能直接使用 HEAD。读取 Git 对象，不修改原始数据。来源、完整提交、路径用于区分版本，内容哈希用于增量导入。源码按函数和结构体边界切分，保留符号与原始行号。长段落进一步切分，当前不是完整 C 语法解析器。

## 测试与评估

```powershell
uv run pytest -q
uv run python -m backend.evaluate evaluation/annotated.jsonl evaluation/results.json --k 5
```

测试集为 JSONL，含 id、question、reference_answer、relevance、type、annotation_status。relevance 为真实 chunk ID 到人工等级的映射。必须人工标注完成并设置 annotation_status=complete 后才能批量评估。

检索评估比较 Dense、Hybrid、Hybrid + Reranker，输出 Recall@K、MRR@K、nDCG@K、检索和重排耗时。空相关集合的 Recall 和 nDCG 为 null。分数表示相关性，不能代替回答准确性。示例数据尚未标注，不是实际实验结果。

## 当前限制

开发尚未完成。待实现普通目录与 PDF 导入、Alembic 版本迁移、SSE、受限搜索工具、完整实验面板、生成准确性评估、分支过滤、并发消息约束与认证。仅用于本机开发。真实知识库规模和效果以运行记录为准。