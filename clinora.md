# Clinora 项目面试概览

> 面试定位：Clinora 是一个面向临床诊断推理场景的多智能体 AI 原型系统。它把患者症状采集、风险分诊、RAG 文献检索、鉴别诊断、诊断审查、医生复核、报告导出和评估看板串成一个完整闭环。
>
> 重要边界：这是 UNSW COMP9900 Capstone 的研究/教育原型，不是认证医疗器械，不能替代医生诊断。

## 1. 一句话介绍

Clinora 是一个前后端分离的多智能体临床诊断推理系统：前端提供患者问诊、文件上传、实时 Agent 推理面板和医生端复核；后端基于 FastAPI 串联 Safety Guard、Interviewer、Diagnostician、Critic 和 Diagnostic Roundtable，并通过 Qdrant + BioLORD + BM25 + MedCPT 构建医学文献 RAG，让诊断建议尽量有证据来源。

面试时可以这样说：

> 我们做的是一个“临床诊断推理协作系统”，核心不是单次问答，而是把诊断过程拆成多个专业角色：先做安全分诊，再用 SOCRATES 结构化问诊，随后用医学文献 RAG 支撑鉴别诊断，再由 Critic 检查证据质量和安全风险，最后用 Roundtable 做多视角复核。前端通过 SSE 把这些阶段实时呈现给用户，形成可解释的诊断流程。

## 2. 项目解决的问题

传统单 LLM 医疗问答有几个风险：

- 容易直接给出结论，缺少结构化病史采集。
- 可能幻觉引用或缺少文献依据。
- 对急症红旗症状响应不稳定。
- 用户看不到模型如何一步步推理，信任成本高。
- 医生端难以复核和标注 AI 诊断结果。

Clinora 的设计思路是把诊断拆成可控流程：

1. Safety Guard 先识别高风险症状。
2. Interviewer 只负责问诊，不负责诊断。
3. Diagnostician 结合 RAG 文献生成鉴别诊断。
4. Critic 独立检查证据质量、遗漏信息和安全风险。
5. Roundtable 模拟多专家讨论，进一步暴露分歧和不确定性。
6. Provider 端可查看患者会话并给出 approve / flag verdict。

## 3. 技术栈

### 前端

- React 19 + Vite
- React Router
- Tailwind CSS / 自定义 CSS / shadcn 风格 UI 组件
- i18next + react-i18next，支持多语言 UI
- Vitest + Testing Library 做组件测试
- Cypress 做 E2E 流程测试

关键文件：

- `clinora-frontend/src/Clinora.jsx`：根应用、路由和 Patient / Provider 入口。
- `clinora-frontend/src/core/api.js`：REST API 与 SSE stream 封装。
- `clinora-frontend/src/pages/ChatPage.jsx`：问诊聊天页、SSE 事件处理、Agent reasoning panel。
- `clinora-frontend/src/pages/ProviderDashboard.jsx`：医生端会话列表、筛选、详情与诊断 verdict。
- `clinora-frontend/src/pages/EvalPage.jsx`：MedQA 评估看板。
- `clinora-frontend/src/components/MediaUploadZone.jsx`：文件、音频、图片上传入口。

### 后端

- FastAPI + Uvicorn
- sse-starlette 做 Server-Sent Events
- Anthropic Claude 作为主要 LLM / Vision 模型
- Qdrant 向量数据库
- BioLORD-2023 dense embedding
- 自定义 BM25 sparse retrieval
- MedCPT Cross-Encoder reranking
- SQLite 存储用户、患者、会话、消息、上传和评估记录
- JWT + bcrypt 做认证
- ReportLab 生成 PDF 报告
- pytest + pytest-cov 做后端测试

关键文件：

- `clinora-backend/main.py`：所有 REST / SSE endpoint、会话流程、上传处理、导出和评估接口。
- `clinora-backend/agents.py`：同步版 Agent prompts 与调用逻辑。
- `clinora-backend/agents_async.py`：异步版 Agent 调用，用于 SSE 实时流。
- `clinora-backend/rag.py`：混合检索、Qdrant 写入、dense/sparse fusion、reranking。
- `clinora-backend/safety.py`：规则 + LLM 双层安全分诊。
- `clinora-backend/db.py`：SQLite schema、迁移和工具函数。
- `clinora-backend/auth.py`：注册、登录、JWT、患者 CRUD。
- `clinora-backend/eval/evaluator.py`：单 LLM vs 多 Agent 的评估逻辑和 Mistral judge。
- `clinora-backend/ingest.py`：从 PubMed 拉取文献并写入 Qdrant。

### 部署

- `docker-compose.yml` 编排 3 个服务：`qdrant`、`backend`、`frontend`。
- 前端容器通过 Nginx 暴露 80 端口，并代理 `/api/*` 到后端。
- 后端容器连接 Qdrant，并挂载 SQLite 数据库和 uploads 目录。

## 4. 总体架构

系统可以理解为三层：

1. 表现层：React 前端
   - 患者端：症状输入、问诊聊天、文件上传、结果查看、历史记录。
   - 医生端：会话筛选、诊断查看、approve / flag 标注、RAG ingestion 管理。
   - 评估端：运行 MedQA 风格题目，对比 single LLM 与 multi-agent。

2. 应用编排层：FastAPI 后端
   - 管理认证、会话、消息、上传、导出和权限。
   - 串联 Agent pipeline。
   - 提供 REST 和 SSE 两套诊断路径。

3. AI 与知识层
   - Claude：问诊、诊断、Critic、Vision、多 Agent commentary。
   - Qdrant：医学文献向量库。
   - PubMed ingestion：构建医学知识库。
   - Mistral/OpenRouter：独立二次评审和评估 judge。

## 5. 端到端用户流程

### 患者流程

1. 用户注册或登录，可选择 patient / provider role。
2. 患者在 Input Page 输入主诉、部位、持续时间、严重程度、补充病史。
3. 可在问诊前或问诊中上传 PDF、TXT、图片、DICOM、音频、视频等材料。
4. 后端创建 session，Interviewer 先发起 SOCRATES 问诊。
5. 用户每次发送消息后：
   - Safety Guard 检查是否存在急症风险。
   - Interviewer 追问缺失信息。
   - 前端实时展示 Agent reasoning log 和 quick-reply chips。
6. 当 Interviewer 输出 `[READY_FOR_DIAGNOSIS]` 或达到最大轮数时，进入 diagnosis 阶段。
7. Diagnostician 基于问诊 transcript + 上传材料 + RAG 文献生成鉴别诊断。
8. Critic 检查诊断质量、证据缺口、安全红旗和下一步建议。
9. Roundtable 生成多 Agent 讨论日志。
10. 用户进入 Results Page，查看 diagnosis、critic review、RAG refs、transcript，并导出 PDF / JSON。

### 医生流程

1. Provider 登录后进入 Provider Dashboard。
2. 可以按状态、严重程度、关键词、日期筛选会话。
3. 查看某个 session 的原始消息、AI 诊断、Critic review、Mistral peer review。
4. 对诊断进行 `approved` 或 `flagged` 标注，并写 provider note。
5. 可以触发或查看 RAG ingestion 状态。

## 6. 多 Agent 设计

### Safety Guard

位置：`clinora-backend/safety.py`

职责：

- 每次患者输入先过安全分诊。
- 第一层是 regex rule-based classifier，例如 chest pain + shortness of breath、unconscious、severe bleeding、hemoptysis。
- 第二层是 Claude LLM classifier。
- 最终风险取 rule risk 和 LLM risk 的最大值。
- 高风险时前端显示 emergency warning，不让风险提示依赖诊断阶段。

面试亮点：

> 我们没有完全依赖 LLM 做安全判断，而是用规则层兜住明确红旗，再用 LLM 补充语义理解。最终风险取两者最大值，宁可保守提醒，也避免急症被漏掉。

### Interviewer Agent

位置：`clinora-backend/agents.py`、`clinora-backend/agents_async.py`

职责：

- 使用 SOCRATES 框架做结构化病史采集。
- 一次只问 1 个聚焦问题，最多 3 个短问题，避免审问式体验。
- 不做诊断，只收集信息。
- 根据缺失维度动态追问。
- 输出 quick replies，前端渲染成快捷选项。
- 信息足够时输出 `[READY_FOR_DIAGNOSIS]`。

面试亮点：

> Interviewer 被明确限制“不诊断”，这是一种职责隔离。它让模型先收集足够上下文，再把诊断交给后续 Agent，减少过早下结论。

### Diagnostician Agent

位置：`clinora-backend/agents.py`

职责：

- 将患者 case、transcript、上传材料分析结果整合成 case_text。
- 对患者自然语言做 medical query rewrite。
- 生成多个 RAG query，提高召回。
- 从 Qdrant 检索文献并格式化为 prompt context。
- 输出 specialist routing、top differential diagnoses、confidence、supporting features、recommended investigations 和 clinical summary。

面试亮点：

> Diagnostician 不只是把用户问题丢给 LLM，而是先把 layperson language 改写成医学检索词，再用 hybrid RAG 找文献，要求回答只引用检索到的证据，从 prompt 层降低 hallucination 风险。

### Critic Agent

位置：`clinora-backend/agents.py`

职责：

- 独立审查 Diagnostician 的输出。
- 关注证据质量、遗漏信息、潜在 bias、红旗症状和下一步建议。
- 输出 APPROVED / NEEDS REVISION 风格的 verdict。

面试亮点：

> Critic 是一个独立角色，不共享 Diagnostician 的职责。它相当于第二医生复核，专门寻找证据薄弱和安全风险。

### Diagnostic Roundtable

位置：`clinora-backend/agents.py`、`agents_async.py`

职责：

- 生成 Diagnostician、Critic、Safety 之间的简短 debate。
- 用于前端 Agent reasoning panel，帮助用户理解 AI 内部如何复核诊断。
- 即使 roundtable 失败，也不会影响主诊断结果持久化。

面试亮点：

> Roundtable 是解释性增强层，不是核心诊断依赖。系统把“结果生成”和“解释展示”解耦，所以辅助日志失败不会让诊断主流程失败。

## 7. RAG 设计

位置：`clinora-backend/rag.py`、`clinora-backend/ingest.py`

RAG pipeline：

1. PubMed ingestion
   - `ingest.py` 内置 78 个跨科室搜索词。
   - 通过 NCBI Entrez API 搜索 PMID，再拉取 title、abstract、authors、journal、year、URL。
   - 过滤无 abstract 或 abstract 太短的文献。

2. 向量写入
   - dense vector：BioLORD-2023，768 维医学领域 embedding。
   - sparse vector：自定义 BM25，保存 corpus IDF。
   - Qdrant collection 同时包含 dense 和 sparse fields。

3. 查询改写
   - Diagnostician 会先把患者描述改写为医学术语。
   - 追加多个 query 视角，例如 `treatment and diagnosis of ...`、`What is ...`。

4. 混合检索
   - dense semantic search 捕捉语义相近的文献。
   - BM25 sparse search 捕捉关键词精确匹配。
   - Qdrant RRF fusion 融合多路结果。

5. Reranking
   - MedCPT Cross-Encoder 对候选文献重新排序。
   - 最终取 top references 注入诊断 prompt。

面试亮点：

> 我们没有只做 dense embedding，而是 dense + sparse hybrid。医学场景里术语、缩写、疾病名称很重要，BM25 能补足 dense embedding 对精确词的不足；MedCPT reranker 再从医学语义上重排候选结果。

## 8. SSE 实时流设计

位置：`clinora-backend/main.py`、`clinora-frontend/src/core/api.js`、`ChatPage.jsx`

后端提供两类接口：

- Blocking REST：`/api/session/chat`、`/api/session/diagnose`
- Streaming SSE：`/api/session/chat/stream`、`/api/session/diagnose/stream`

Chat stream 事件顺序：

1. `safety_result`
2. `interviewer_reply`
3. `agent_message`，用于 Safety ↔ Interviewer commentary
4. `done`

Diagnose stream 事件顺序：

1. `phase_sep`
2. `agent_message`，显示 diagnostician / critic / roundtable 消息
3. `diagnosis_ready`
4. `done`

前端 `api.js` 使用 fetch + ReadableStream 手动解析 SSE 的 `data:` 行。这里专门处理了 `\r\n\r\n` 和 `\n\n` 两种事件分隔符，避免 Nginx / sse-starlette 换行差异导致解析失败。

面试亮点：

> 我们用 SSE 而不是 WebSocket，是因为这个场景主要是服务端推送阶段性 Agent 事件，不需要复杂双向低延迟通道。SSE 简化了部署和代理配置，也更贴合诊断 pipeline 的单向流式输出。

## 9. 多模态输入

位置：`clinora-backend/main.py`

支持的输入类型：

- 图片：jpg、jpeg、png、gif、bmp、webp，通过 Claude Vision 分析。
- DICOM：读取像素数据，转换为 JPEG 后做 Vision 分析。
- PDF：用 pypdf 抽取文本。
- TXT：读取文本。
- 音频：SpeechRecognition + Google Speech API 转录。
- 视频：OpenCV 抽取关键帧，再对关键帧做 Vision 分析。

安全处理：

- 文件名会 sanitize。
- 图片超过大小时用 Pillow 压缩。
- 上传材料内容会包在 `<uploaded_document>` 或 `<uploaded_documents>` 标签内，明确告诉模型这是患者提供的数据，不是系统指令。
- 长文本会截断到 `MAX_UPLOAD_CONTEXT_CHARS`，避免 prompt 过长。

面试亮点：

> 多模态内容不是直接替代诊断，而是先转成结构化临床上下文，再参与问诊和 RAG 查询。比如图片报告会被改写成医学术语后参与检索，避免视觉描述和文献检索之间的语义断层。

## 10. 数据模型

位置：`clinora-backend/db.py`

主要表：

- `users`：账号、邮箱、密码 hash、role。
- `patients`：患者档案，归属于 user。
- `sessions`：一次问诊会话，包含症状、状态、诊断、review、refs、provider verdict。
- `messages`：规范化消息表，记录 user / agent / system 消息和 agent_type。
- `uploads`：上传文件元数据、路径、抽取文本。
- `eval_runs`：评估运行结果，记录 single/multi/judge 正确性。

会话状态：

- `interviewing`：正在问诊。
- `analyzing`：已触发诊断。
- `done`：诊断完成。

权限设计：

- Patient 默认只能访问自己的 session。
- Provider 可以查看 provider sessions，并提交 verdict。
- JWT token 默认有效期 7 天。

## 11. 认证与角色

位置：`clinora-backend/auth.py`

实现点：

- bcrypt hash password，且截断到 bcrypt 支持的 72 bytes。
- JWT 使用 HS256，payload 包含 `sub`、`username`、`exp`。
- `get_current_user` 是可选认证，未登录时返回 None。
- `require_user` 是强制认证，用于 provider dashboard、历史记录等接口。
- 用户角色限制为 `patient` 或 `provider`。

面试可以强调：

> 这个项目里我们把体验做成“可匿名开始”和“登录后持久化/医生端管理”兼容，所以后端同时有 optional auth 和 required auth 两类 dependency。

## 12. 评估模块

位置：`clinora-backend/eval/evaluator.py`、`clinora-backend/eval/questions/clinical_cases.json`、`clinora-frontend/src/pages/EvalPage.jsx`

功能：

- 提供临床 benchmark cases / MedQA 风格问题。
- 跑 single LLM baseline。
- 跑 multi-agent pipeline：Interviewer 提取临床特征，Diagnostician 分析鉴别诊断，Critic 给最终答案。
- 用 Mistral Large / OpenRouter 作为独立 judge，评估 Claude multi-agent 输出。
- 前端 Eval Page 展示 total、single accuracy、multi accuracy、improvement。

面试亮点：

> 我们不仅实现了功能，还做了评估闭环。通过 single LLM vs multi-agent 的对照实验，可以把“多 Agent 是否真的有收益”从主观体验变成可量化结果。

## 13. 测试与质量保障

项目有一键测试脚本：

- `run_tests.sh`
- `run_tests.bat`

后端测试：

- pytest
- pytest-cov
- 覆盖 auth、session、streaming、RAG、safety、agents、export、eval、ingest、provider routes 等。

前端测试：

- ESLint
- Vitest unit tests
- Cypress E2E

README 中记录的结果：

- Backend pytest：210 passed
- Backend coverage：96% overall
- Frontend Vitest：8 passed
- Cypress：3 scenarios passed
- ESLint：0 errors / 0 warnings

面试亮点：

> 外部依赖都被 mock 掉，包括 Claude、Qdrant、Google SpeechRecognition、OpenCV/Pillow、PubMed API。这样测试不依赖网络和真实 API key，CI 更稳定。

## 14. 你可以重点讲的技术亮点

### 亮点 1：职责隔离的多 Agent pipeline

不是一个 LLM 完成所有事情，而是把临床流程拆成 Safety、Interviewer、Diagnostician、Critic、Roundtable。

价值：

- 降低 prompt 复杂度。
- 每个 Agent 有明确边界。
- 便于测试、替换和解释。
- 更贴近真实临床中的分诊、问诊、诊断、复核流程。

### 亮点 2：安全分诊前置

Safety Guard 在每轮用户输入后都运行，而不是等到最终诊断才提示风险。

价值：

- 高风险症状可以立即显示 warning。
- regex 兜底明确红旗，LLM 补充语义判断。
- 对医疗场景更稳妥。

### 亮点 3：医学 RAG 不是简单向量搜索

RAG 包含 query rewrite、multi-query expansion、dense/sparse hybrid search、RRF fusion、MedCPT reranking。

价值：

- 增强医学术语召回。
- 减少 LLM 幻觉引用。
- 输出引用可以回溯到 PubMed 来源。

### 亮点 4：SSE 实时展示 Agent 状态

前端不是等完整诊断生成后一次性展示，而是流式展示 safety、interviewer、diagnostician、critic、roundtable 的阶段性消息。

价值：

- 用户体验更好。
- 长耗时 AI pipeline 不会像“卡死”。
- 提升过程透明度和可解释性。

### 亮点 5：多模态临床上下文

支持图片、DICOM、PDF、音频、视频，并把材料统一转换为文本/视觉分析上下文。

价值：

- 更接近真实就医资料场景。
- 视觉结果还能参与 RAG query。
- 上传材料被标记为 data，降低 prompt injection 风险。

### 亮点 6：医生端 Human-in-the-loop

Provider Dashboard 允许医生查看、筛选和标注 AI 诊断。

价值：

- 不把 AI 结果当最终医疗结论。
- 让系统可以支持临床审核流程。
- provider verdict 能作为后续改进和审计数据。

### 亮点 7：评估闭环

Eval Page 能比较 single LLM 和 multi-agent，并引入 Mistral judge。

价值：

- 可以量化多 Agent 是否提升结果。
- 有利于面试中回答“你如何证明系统有效”。

## 15. 可能被问到的架构问题

### Q1：为什么要用多 Agent，而不是一个大 prompt？

可以回答：

> 医疗诊断流程天然分阶段：分诊、问诊、诊断、复核。用单个 prompt 会让模型同时承担所有职责，容易过早诊断或忽略安全检查。多 Agent 让每个角色边界更清晰，也方便单独测试。例如 Interviewer 被明确禁止诊断，Critic 专门找证据缺口和安全问题。

### Q2：RAG 如何减少 hallucination？

可以回答：

> Diagnostician 的 prompt 要求只使用检索到的知识作为证据，并使用指定 citation key。检索侧使用 dense + BM25 hybrid，兼顾语义召回和医学术语精确匹配，再用 MedCPT cross-encoder rerank。这样比直接让 LLM 自己凭记忆回答更可追溯。

### Q3：为什么选择 SSE 而不是 WebSocket？

可以回答：

> 我们的核心场景是后端把 Agent pipeline 的阶段性事件推给前端，主要是单向流。SSE 更简单，浏览器原生支持，和 HTTP/Nginx 部署更容易兼容。前端用 fetch stream 解析 `data:` 事件，后端用 sse-starlette 生成事件。

### Q4：如何处理高风险医疗场景？

可以回答：

> Safety Guard 在 session start 和每次 chat message 都运行。它有规则层和 LLM 层，最终取更高风险。比如胸痛合并呼吸困难、昏迷、大出血、咳血会被识别为高风险。高风险会立即在前端显示 emergency warning，而不是等诊断完成。

### Q5：上传文件会不会导致 prompt injection？

可以回答：

> 项目里对用户输入有 injection pattern 检查。上传内容不会作为系统指令，而是包在 `<uploaded_document>` 标签中，并在 prompt 里明确说明这是 patient-provided data，不能当作指令。文件名也会 sanitize，长文本会截断。

### Q6：系统状态如何持久化？

可以回答：

> SQLite 保存 users、patients、sessions、messages、uploads 和 eval_runs。session 中保存 status、symptoms、diagnosis、review、refs、provider verdict 等。messages 表保留规范化消息流，方便历史记录、医生端查看和导出。

### Q7：如何证明多 Agent 比 single LLM 更好？

可以回答：

> 项目有 eval 模块和 Eval Page，可以对临床 benchmark case 分别跑 single LLM baseline 和 multi-agent pipeline，并记录正确率和 improvement。此外还引入 Mistral Large 作为独立 judge，避免只用同一个 Claude 模型自评。

### Q8：如果 RAG 数据库为空怎么办？

可以回答：

> 后端启动时会打印 RAG collection size，并提供 `/api/rag/status` 和 `/api/rag/ingest`。Docker 场景下 Qdrant 有 volume 持久化。首次运行需要执行 ingestion，从 PubMed 拉取文献后写入 Qdrant。

### Q9：为什么使用 SQLite，而不是 PostgreSQL？

可以回答：

> 这是 capstone 原型，SQLite 降低本地运行和评估部署复杂度，足够支持用户、会话、消息和评估记录。项目通过 schema migration 保持迭代灵活。如果进入生产，数据库层可以迁移到 PostgreSQL，并保留相同的表结构设计。

### Q10：你们如何保证测试稳定？

可以回答：

> 测试中对外部服务做 mock，例如 Claude、Qdrant、SpeechRecognition、OpenCV/Pillow、PubMed API。这样测试不需要真实网络和 API key，能稳定覆盖 happy path 和 error path。

## 16. 如果面试官问你的个人贡献

如果你主讲前端，可以重点说：

- 负责 React/Vite 前端页面架构和用户流程串联。
- 在 `Clinora.jsx` 中组织 patient/provider/eval/history 等路由。
- 在 `ChatPage.jsx` 中处理 SSE 事件，把 safety、interviewer、diagnostician、critic、roundtable 转成可视化 reasoning log。
- 实现或维护上传、quick replies、SOCRATES progress、结果页和历史记录体验。
- 做 i18n、多语言 UI、主题和交互细节。
- 写 Vitest / Cypress 测试覆盖认证、问诊、文件上传、诊断导出等关键流程。

如果你主讲后端，可以重点说：

- 设计 FastAPI session lifecycle。
- 串联多 Agent pipeline 和 RAG。
- 实现双层 Safety Guard。
- 实现 SSE streaming endpoint。
- 设计 SQLite schema 和 provider role 权限。
- 实现 PDF/JSON export、Mistral peer review 和 eval pipeline。

如果你想强调团队协作，可以说：

> 我们把项目拆成前端体验、后端编排、RAG 知识库、评估测试几个模块。接口通过 `core/api.js` 和 FastAPI schema 对齐，AI pipeline 的每个阶段都有明确输入输出，方便多人并行开发。

## 17. 面试时可以展示的 Demo 路线

推荐 5 分钟 demo：

1. 登录或注册 patient。
2. 输入一个症状，例如 chest pain 或 headache。
3. 展示 Safety Guard 和 Interviewer 的实时问诊。
4. 上传一个 PDF / 图片，说明系统会抽取或分析上传资料。
5. 触发诊断，展示 Diagnostician、Critic、Roundtable 的 SSE 日志。
6. 打开 Results Page，展示 diagnosis、critic review、RAG references、transcript。
7. 导出 PDF / JSON。
8. 切换 provider dashboard，展示医生端 review 和 verdict。
9. 打开 Eval Page，说明 single LLM vs multi-agent 的评估闭环。

## 18. 项目可改进点

这些点适合在面试结尾主动说，体现你知道系统边界：

- 数据库：生产环境应从 SQLite 迁移到 PostgreSQL，并加强审计日志。
- 安全：增加更系统的 PHI/PII 脱敏、rate limit、文件病毒扫描和更严格的 prompt injection 防护。
- 医疗合规：需要临床专家评审、IRB/伦理审批、免责声明、责任边界和医疗器械合规评估。
- RAG：增加文献版本管理、引用质量评分、guideline 优先级、过期文献过滤。
- 评估：扩大 benchmark case 数量，引入真实医生标注，做 sensitivity / specificity / safety recall 评估。
- 可观测性：增加 tracing、token 成本统计、Agent latency 分析和失败重试策略。
- Streaming：可加入 cancellation、timeout、backpressure 和更细粒度 token streaming。
- 前端：进一步优化移动端体验、可访问性和医生端批量审核工作流。

## 19. 快速启动命令

Docker 推荐：

```bash
docker compose up --build -d
docker compose exec backend python ingest.py
```

手动启动后端：

```bash
cd clinora-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 ingest.py
uvicorn main:app --reload --port 8000
```

手动启动前端：

```bash
cd clinora-frontend
npm run dev
```

测试：

```bash
bash run_tests.sh
```

## 20. 面试总结话术

可以用这段作为结尾：

> Clinora 的核心价值在于把 LLM 医疗问答从“黑盒回答”改造成“可分阶段、可复核、可追溯”的诊断辅助流程。技术上它结合了多 Agent 编排、医学 RAG、SSE 实时可视化、多模态资料处理、医生端 human-in-the-loop 和评估闭环。虽然它只是教育研究原型，但架构上已经考虑了安全分诊、证据引用、权限、历史记录、导出和测试，这些都是把 AI demo 推向真实应用时必须面对的问题。
