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

## 代码结构

后端根目录只保留应用入口、共享请求模型和包目录，基础设施与领域逻辑分别下沉：

```text
backend/
  api.py                 FastAPI 装配、生命周期、前端静态托管
  schemas.py             跨路由共享的请求模型
  core/                  配置、数据库模型、后台任务、会话锁
  ingestion/             文档发现、切分、PDF/目录导入
  retrieval/             Dense/BM25/RRF 召回与重排
  generation/            Prompt、模型客户端、工具循环、引用校验、事件
  chat/                  会话上下文与单轮问答编排
  evaluation/            检索实验、人工核验、辅助评分、评估 CLI
  routers/               catalog / search / sessions / chat HTTP 路由
  ops/                   初始化数据库、迁移链验证等运维脚本
```

前端按聊天工作区、消息渲染和详情渲染拆分：

```text
frontend/src/
  chat/                  会话侧栏、输入区、会话视图、设置/引用/详情抽屉
  components/            消息卡片、过程卡片、知识库/评估/检索面板
  components/generation/ 详情事件渲染（Prompt、证据、候选）
  api/                   普通请求与 SSE 客户端
  types.ts               共享类型
```

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
uv run python -m backend.evaluation.cli evaluation/annotated.jsonl evaluation/results.json --k 5 --warmup
```

测试集为 JSONL，含 id、question、reference_answer、relevance、type、annotation_status。relevance 为真实 chunk ID 到人工等级的映射。必须人工标注完成并设置 annotation_status=complete 后才能批量评估。

检索评估比较 Dense、Hybrid、Hybrid + Reranker，输出 Recall@K、MRR@K、nDCG@K、检索和重排耗时。空相关集合的 Recall 和 nDCG 为 null。分数表示相关性，不能代替回答准确性。示例数据尚未标注，不是实际实验结果。

聊天页高级面板支持粘贴标注 JSONL，运行实验和导出结果。API 为 POST /api/evaluation/run，generate_answers=true 可附加 Baseline 与各 RAG 方案回答，统一生成模型与 temperature=0，并记录端到端耗时。准确性为待人工核验，不自动赋分。检索日志与实验结果保存于数据库。

evaluation/smoke.source-verified.jsonl 是开发者核对源码的单样例冒烟测试，smoke-results.json 为实际结果，不能视为独立评测或泛化性能结论。首次加载模型包含冷启动耗时，不能直接和热启动对比。

聊天支持 SSE，接口为 POST /api/chat/stream；补充搜索开关允许模型按需多轮检索，重复查询复用结果，连续两轮无新增证据时结束。默认不设次数上限，可在问答设置或 tool_call_limit 参数中指定。工具查询使用通用系统提示词约束：优先 2–5 个精确技术关键词，并可按 path_regex 限定源码或教材路径（如 `kernel/.*\.c$`）；不包含题目特定词表。引用只绑定真实证据；唯一的短 ID 前缀会恢复为完整引用，歧义引用移除。

初始 RAG 仅取 Top K 个候选（与返回片段数相同），仅用于给模型一个起点；补充检索仍使用问答设置中的候选数，避免初始重排消耗过多 CPU。

会话列表按最近一次提问时间倒序排列。旧消息没有时间戳，迁移时按原插入顺序补一个初始时间；之后每次提问都会更新该会话的时间。

模型可见的思考与检索过程以可展开卡片显示在回答上方，并随 assistant 消息保存到会话历史。系统 Prompt、每次调用的完整模型输入、RAG 注入证据、工具检索结果与候选融合分数始终通过 detail 事件实时返回，并随消息落库；点击消息右上角的「生成详情」在独立抽屉中查看，历史会话同样可查看。聊天默认开启 Cross-Encoder 重排序。

过程卡片优先展示上游返回的 reasoning_content 显式推理；上游不返回时只展示可观测的检索与工具调用，不伪造思考内容。

LLM_MAX_TOKENS 控制统一输出预算，LLM_REASONING_EFFORT 为可选推理强度。本机已验证 low，其他兼容 API 不支持时应留空。生成返回 finish_reason、usage 和 complete 元数据；达到输出上限会明确提示回答未完成，不能作为完整回答计分。

开发集真实对比与失败分析见 evaluation/ANALYSIS.md。六题结果是开发者源码核对集，不是独立人工测试集。四方案生成的八条回答保存于 development-generation-results.json，未填人工准确率，且旧结果存在截断和短引用未关联的问题，保留原样供分析。

实验面板提供汇总表与逐题人工评分；API POST /api/evaluation/{id}/reviews 保存核验人、0–1 分数和依据。检索相似度绝不自动转为答案评分。会话生成由 PostgreSQL advisory lock 串行化，同一会话并发生成返回 409，消息顺序有数据库唯一约束。

## 当前限制

五阶段的软件实现与本机验收已完成，逐项记录见 ACCEPTANCE.md。当前为课程实验与本机单用户应用，未实现多租户认证；公网部署前应先补齐认证。检索指标、模型辅助分与人工分分别保存，未伪造第三方人工评分。PDF 的图形和复杂表格语义、完整 C 语法树解析、超大规模 ANN 与 LangGraph 不属于本版承诺。

导入与评估页面使用 PostgreSQL 持久化任务状态，进程内用一个后台线程池串行执行，不引入 Redis 或 Celery。进度、结果和错误可通过 GET /api/jobs/{id} 查看；启动时只将本机失活进程的未完成任务标记为失败，需重新提交以重试。推荐单个 Uvicorn worker。保留同步接口供脚本使用。

任务接口：POST /api/import/jobs、POST /api/evaluation/jobs、POST /api/evaluation/{id}/judge。历史实验可重载和导出，辅助评分逐题保存并可续跑。模型辅助评分需要上游支持 JSON mode；失败会明确记录，不补造分数。

留出集与完整对比见 evaluation/HELDOUT_REPORT.md：八题、32 条真实回答和32 条同模型辅助核验。题目与开发集分开，标注来源是开发者源码核对，不是第三方人工标注。留出集上 Dense 的排序指标更好，没有宣称 Hybrid 或 Reranker 必然提高效果。

更换 Embedding 模型时必须保持数据库向量维度一致并完整重建索引，不要混用不同模型的向量。

## 一体启动与验收

```powershell
uv sync
pnpm --dir frontend install
pnpm --dir frontend build
uv run alembic upgrade head
uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000 --workers 1
```

构建后由 FastAPI 托管前端，访问 http://127.0.0.1:8000。开发模式可单独执行 pnpm --dir frontend dev，默认使用 5173 端口，通过代理调用 8000 后端。

```powershell
uv run ruff check backend migrations tests
uv run pytest -q -p no:cacheprovider --basetemp=.test-tmp
uv run python -m backend.ops.verify_migrations
pnpm --dir frontend lint
```

verify_migrations 在 PostgreSQL 临时表空间从零执行迁移，再回滚，不删除现有知识库。单元测试不需要 LLM 凭据；浏览器真实问答需要模型凭据和已导入数据。

## 浏览器验收

使用独立 Playwright Chromium，不依赖 Codex 浏览器。测试会启动本地 8010 端口后端，使用已有构建产物。需要先执行 pnpm build；真实问答用例需要 .env 中的 LLM 配置和已导入知识库，会清理自己创建的测试会话。

```powershell
cd frontend
pnpm exec playwright install chromium
pnpm build
pnpm exec playwright test
```

截图和失败 trace 写入 tmp/browser，已从 Git 排除。每轮截图使用独立目录，避免 Windows 文件占用。三项浏览器验收覆盖首页与按需加载、后台增量导入、策略对比与历史实验、真实流式问答和引用抽屉。历史实验测试自行创建标为 E2E 的接线验证记录，不依赖本机既有实验 ID，也不将它作为课程性能数据。
