# xv6 RAG 知识检索与问答

本项目使用 FastAPI、PostgreSQL + pgvector，以及本地 CPU Embedding 和 Reranker。前端使用 pnpm、Vite、React、TypeScript、Ant Design，Markdown 渲染使用 react-markdown。

## 后端启动

保留已有 .env；新环境参考 .env.example。数据库需启用 vector 扩展，应用账户需具有 public schema 建表权限。WSL 数据库需要先启动。

```powershell
uv sync
uv run alembic upgrade head
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

该提交位于 util 分支的个人修改之前；其他实验分支必须分别审计，不能直接使用 HEAD。读取 Git 对象，不修改原始数据。来源、完整提交、路径用于区分版本，内容哈希用于增量导入。源码按函数和结构体边界切分，保留符号与原始行号。长段落进一步切分，当前不是完整 C 语法解析器。普通目录导入可不传 commit，HTML 提取正文，行号明确标记基于提取文本。

预置的 data 下三个 PDF、data/labs 和 data/xv6-labs-2022-impl 来源为系统文档，数据库持久化保护标记，API 禁止删除；普通导入文档可在确认后删除。搜索参数 version 可限制完整提交版本，并保留教材和实验指导。默认使用 util 原始提交，避免混合多个代码版本。

当前已导入 706 个文档、6991 个片段：十个实验分支原始提交、13 个实验网页、三个 PDF。分支提交与作者核对记录见 evaluation/source-versions.json，已排除 2026 年个人修改。相同文本复用已有向量，但保留各版本独立定位信息。

PDF 共 679 页、1784 个片段：网卡手册 410 页/973 片段，教材 114 页/370 片段，特权规范 155 页/441 片段。教材 9 个仅含页码的留白页不索引。详见 evaluation/pdf-extraction-report.json。PDF 保留实际页序号、印刷页标签和章节；引用不伪造代码行号。PDF 图形和复杂表格的视觉语义尚不能由纯文本提取完整表达，旋转文字保留但阅读顺序可能降级。

导入三个 PDF：POST /api/import，请求为 `{"root":"data"}`。预置 data 根目录仅导入 PDF，避免递归混入个人源码工作区。索引处理版本持久化为 index_profile，切块规则升级时可重建。

## 测试与评估

```powershell
uv run pytest -q
uv run python -m backend.evaluate evaluation/annotated.jsonl evaluation/results.json --k 5 --warmup
```

测试集为 JSONL，含 id、question、reference_answer、relevance、type、annotation_status。relevance 为真实 chunk ID 到人工等级的映射。必须人工标注完成并设置 annotation_status=complete 后才能批量评估。

检索评估比较 Dense、Hybrid、Hybrid + Reranker，输出 Recall@K、MRR@K、nDCG@K、检索和重排耗时。空相关集合的 Recall 和 nDCG 为 null。分数表示相关性，不能代替回答准确性。示例数据尚未标注，不是实际实验结果。

聊天页高级面板支持粘贴标注 JSONL，运行实验和导出结果。API 为 POST /api/evaluation/run，generate_answers=true 可附加 Baseline 与各 RAG 方案回答，统一生成模型与 temperature=0，并记录端到端耗时。准确性为待人工核验，不自动赋分。检索日志与实验结果保存于数据库。

evaluation/smoke.source-verified.jsonl 是开发者核对源码的单样例冒烟测试，smoke-results.json 为实际结果，不能视为独立评测或泛化性能结论。首次加载模型包含冷启动耗时，不能直接和热启动对比。

聊天支持 SSE，接口为 POST /api/chat/stream；补充搜索开关允许模型按需多轮检索，重复查询复用结果，连续两轮无新增证据时结束。默认不设次数上限，可在问答设置或 tool_call_limit 参数中指定。引用只绑定真实证据；唯一的短 ID 前缀会恢复为完整引用，歧义引用移除。

LLM_MAX_TOKENS 控制统一输出预算，LLM_REASONING_EFFORT 为可选推理强度。本机已验证 low，其他兼容 API 不支持时应留空。生成返回 finish_reason、usage 和 complete 元数据；达到输出上限会明确提示回答未完成，不能作为完整回答计分。

开发集真实对比与失败分析见 evaluation/ANALYSIS.md。六题结果是开发者源码核对集，不是独立人工测试集。四方案生成的八条回答保存于 development-generation-results.json，未填人工准确率，且旧结果存在截断和短引用未关联的问题，保留原样供分析。

实验面板提供汇总表与逐题人工评分；API POST /api/evaluation/{id}/reviews 保存核验人、0–1 分数和依据。检索相似度绝不自动转为答案评分。会话生成由 PostgreSQL advisory lock 串行化，同一会话并发生成返回 409，消息顺序有数据库唯一约束。

## 当前限制

开发尚未完全验收。仍需扩充独立人工标注测试集并实际完成人工评分；当前只有明确标注来源的开发验证结果。认证和长任务进度可作为后续扩展。前端通过 React.lazy 拆分消息渲染、语法高亮、知识库与评估面板，构建不再出现大于 500 kB 的 chunk 提示。仅用于本机开发；长时间导入和评估目前为同步接口。

## 浏览器验收

使用独立 Playwright Chromium，不依赖 Codex 浏览器。测试会启动本地 8010 端口后端，使用已有构建产物。需要先执行 pnpm build；真实问答用例需要 .env 中的 LLM 配置和已导入知识库，会清理自己创建的测试会话。

```powershell
cd frontend
pnpm exec playwright install chromium
pnpm build
pnpm exec playwright test
```

截图和失败 trace 写入 tmp/browser，已从 Git 排除。测试包括首页、延迟加载、知识库保护标记、真实流式问答和引用抽屉。
