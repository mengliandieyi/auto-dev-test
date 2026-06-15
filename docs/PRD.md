---
prd_id: AUTODEV-001
version: 4.4.2
author: admin
date: 2026-06-15
status: spec-only
---

# 产品需求文档（PRD）

> **职责**：产品目标、用户故事、里程碑**验收标准**（checkbox 只在此处）。  
> **技术实现** → [TECH-DESIGN.md](./TECH-DESIGN.md)

---

## 1. 产品概述

### 1.1 一句话

以 **PRD** 为唯一需求源头，自动生成并执行 E2E / 组件测试，产出可追溯验收矩阵；失败时可 AI 诊断并在授权范围内自愈重跑。

### 1.2 目标用户

开发、测试、测试负责人、产品经理、CI/CD 管理员、项目负责人。

### 1.3 主路径

```
编写 PRD → 生成链路 → 执行测试 → 查看追溯报告 → [可选] AI 自愈
```

| 入口 | 说明 |
|------|------|
| 日常 | Web 管理后台（M3 起） |
| CI / 自动化 | CLI `run.py`（M1 起） |
| 设计 | TypeUI + PRD 约定的 `data-testid` |

### 1.4 不在范围内（Out of Scope）

- 替代 Jira / 需求管理系统
- M6 前：自动生成或**部署**业务后端服务；**`run.py dev`（OpenHands）仅 M6 实现**，M1–M5 不得提前接入
- 无 `data-testid` 的 UI 自动定位或 AI 猜测 DOM
- 多租户 SaaS、细粒度 RBAC（首版内网单团队）
- 无人值守自动 merge 生产分支

### 1.5 里程碑导读（M1–M6 是什么）

**M = Milestone（里程碑）**：按顺序交付的产品阶段，不是文档版本号。完成一个 M 再打勾验收，不要跳步。

| 阶段 | 一句话 | 你现在要不要管 |
|------|--------|----------------|
| **M1** | 终端命令：PRD → 生成测试 → 跑测试 → 报告 | ✅ **现在就做** |
| **M2** | 多人改 PRD 不踩坑（指纹、冲突检测、报告卫生） | M1 做完再做 |
| **M3** | 网页点按钮，不用记命令 | 知道即可 |
| **M4** | 组件测试加速（多进程） | 知道即可 |
| **M5** | 网页改 PRD + 接 CI | 知道即可 |
| **M6** | 连真实业务仓 + AI 自愈（`heal-loop` / `dev`） | 最后做 |

**依赖顺序**：`M1 → M2 → M3 → M5 → M6`；`M4` 在 M1 之后可与 M3 并行。

文档里写「M3 起」= 第 3 阶段才有；「M6 前不做」= 前 5 阶段都不要实现。

---

## 2. 背景与痛点

| 痛点 | 期望 |
|------|------|
| PRD 与测试脚本脱节 | 验收标准可量化、可映射到用例 |
| 多项目脚本风格不一 | 统一生成规范，项目配置隔离 |
| PRD 变更后脚本滞后 | 版本 + 内容变更可触发再生成 |
| 操作依赖 CLI | Web 管理台一键触发（M3） |
| 组件只靠 E2E | 分层测试（E2E + Vitest） |
| 失败后排障成本高 | 结构化诊断 + 可选自愈（M6） |

---

## 3. 产品原则

| 原则 | 说明 | 生效里程碑 |
|------|------|------------|
| 生成与执行解耦 | 业务 PR 只跑 `test`，不重复调 LLM 生成 | M1 起 |
| 契约先行 | 无 testid = 不可测 | M1 起 |
| 内容指纹优先 | 改 PRD 正文须 bump `version` 方可合入；**CI 强制**，本地草稿可宽松重生成（见 TECH §4.2） | **M2 起** |
| 环境先于 AI | 环境/鉴权失败不调用 heal 的 LLM | M6 |
| 文档先于代码 | 未验收能力不合入 | 始终 |

---

## 4. 术语

| 术语 | 含义 |
|------|------|
| **ETC** | E2E Test Case，Playwright 用例，编号 `ETC-xxx` |
| **CTC** | Component Test Case，Vitest 用例，编号 `CTC-xxx` |
| **intermediate** | `parse` 产出的 JSON，路径见 TECH §3.3 |
| **spec** | `generate` 产出的 `.spec.ts` / `.test.tsx` |
| **追溯报告** | 验收标准 ↔ 用例 ↔ 执行结果的文本矩阵 |
| **生成链路** | validate → parse → generate → report（不跑测试） |
| **占位符** | `parse` 阶段保留 `{{...}}`；`generate` 阶段替换为字面量（见 TECH §3.4） |
| **M1 门禁用例** | 样例 PRD 中**必须执行且通过**的最小集合：**ETC-001** + **CTC-001**（编号规则见 TECH §3.3） |

---

## 5. 用户故事

| 角色 | 我希望… | 以便… |
|------|---------|-------|
| 开发/测试 | 写好标准 PRD 后自动生成测试 | 减少手工维护脚本 |
| 测试负责人 | 看到验收标准与 PASS/FAIL 对应 | 快速定位漏测与失败 |
| 项目负责人 | 多项目独立接入 | 互不干扰 |
| CI 管理员 | PRD 变更跑生成、代码 PR 只跑测试 | 省钱且安全 |
| 前端 | 用 TypeUI + testid 设计页面 | UI 统一且可测 |
| 产品经理 | 在管理台预览/编辑/上传 PRD | 需求快速进流水线（M5） |
| 运维 | 在管理台维护项目 URL、LLM API、鉴权 | 密钥不进 yaml（M5 写配置） |
| 开发 | 在 Skill 库维护 OpenHands 规范，工作台生成业务代码时选择 | M6 `dev` |
| 开发/测试 | 失败后 AI 诊断并可选修复 | 少翻 log；合入前 Review diff（M6） |

---

## 6. 功能说明

### 6.1 流水线（用户可见）

| 能力 | 用户理解 | 跑真实测试 | CLI / 里程碑 |
|------|----------|------------|--------------|
| 生成链路 | 校验→解析→生成→刷新追溯视图 | 否 | `generate-pipeline` · M1 |
| 执行测试 | Playwright + Vitest，刷新 PASS/FAIL | 是 | `test` · M1 |
| 一键全流程 | 生成链路 + 执行测试 | 是 | `run-full` · M1 |
| 业务代码辅助 | OpenHands 在业务仓叠加代码；可按前端/后端分层，Skill 在工作台选择 | 否 | `dev` · **M6** |
| AI 自愈 | 诊断、修复、重跑（有上限）；**无进展自动停止**等人采纳；须显式 `heal-loop` | 是 | `heal-loop` · **M6** |

### 6.2 能力清单

1. 多项目 yaml 隔离；凭据仅环境变量  
2. PRD 校验（章节、格式、行号）  
3. E2E + 组件测试生成（testid 定位）  
4. 追溯报告（验收标准 ↔ ETC/CTC ↔ 结果）  
5. Web 管理台（M3）  
6. 协作安全：指纹、冲突扫描、skeleton 报告（M2）  
7. CI 模板（M5）  
8. 业务代码辅助 OpenHands（M6）  
9. AI 自愈（M6）  

### 6.3 AI 自愈（M6 产品行为）

| 根因分类 | 平台行为 |
|----------|----------|
| 测试脚本问题 | 可自动改生成脚本并重跑 |
| 业务代码问题 | 可改业务仓并重跑 |
| 需求与实现不一致 | **停止**自动修复，仅 diff，PM 处理 |
| 修复无进展 | 连续一轮后失败用例未减少，或补丁为空 → **`NO_IMPROVEMENT` 停止**，保留 diff 供人工采纳 / 放弃 |
| 环境/配置问题 | **不**调用 AI |
| 偶发失败 | 自动重跑 1 次（无 LLM）；仍失败则 `FLAKY_EXHAUSTED` 停止 |

护栏：≤3 轮、墙钟 15min、Token 单次 + 24h/PRD 上限；`heal.stop_on_no_improvement` 默认 **true**；合入主分支前 Review diff。

---

## 7. 文档规范

### 7.1 业务功能 PRD（用户编写）

- 模板：`templates/prd-template.md`  
- 基准样例：`prds/project-a/PROJ-001_login.md`  
- **必填**：功能名称、需求说明、验收标准、`页面交互`（**或** `使用流程`）  
- **可选**：组件测试、页面设计、接口设计、测试数据  
- TypeUI（`design/SKILL.md`）辅助 UI；设计稿不参与 parse；**testid** 参与 generate/heal  

**`component_path` 约定**：PM 可省略；引擎在 `vitest.frontend_root` 下检索组件文件（约定路径 → 递归搜索；多命中 → `AMBIGUOUS_COMPONENT_PATH`，见 TECH §3.3）。

**测试数据占位符**：PRD「测试数据」章中的 `{{valid.username}}` 等，在 **`parse` 时原样写入 intermediate**；在 **`generate` 时替换为字面量**写入 spec，spec 不依赖运行时解析。

### 7.2 平台 PRD（本文档）

平台级文档（`AUTODEV-001`）无「页面交互」章节；以里程碑与验收标准描述行为，不受业务 PRD 交互步骤数约束。

---

## 8. 里程碑与验收标准

> 技术映射 → [TECH-DESIGN.md §16](./TECH-DESIGN.md)

### M1 — 命令行引擎

**环境前提（M1 固定，不依赖外部 staging / acme-web）**

| 项 | 约定 |
|----|------|
| E2E | 仓库内 fixture `tests/fixtures/mock-e2e/`；`base_url` `http://127.0.0.1:4173`；Playwright `webServer` 拉起（见 TECH §3.1） |
| 组件测试 | `tests/fixtures/mock-frontend/`（`vitest.frontend_root`） |
| LLM | **`parse` 需 `ANTHROPIC_API_KEY`**；`generate` 为模板生成、**不调 LLM**；CI 可用已提交 intermediate + spec，跳过 `parse` 仅跑 `generate` + `test` |
| E2E 鉴权 | M1 fixture 无真实登录；`AuthHelper` 对 cookie/token/basic **skip** |
| 基准 PRD | `PROJ-001_login.md` |
| **M1 门禁用例** | **ETC-001**（正向登录）+ **CTC-001**（错误密码提示）必须生成、执行且 **PASS**；其余用例可生成但在报告标 **NOT_COVERED** 或 **SKIP** |

**验收**

- [x] `validate`：缺章节输出章节名与行号，退出码 **2**  
- [x] `parse`：产出 `tests/intermediate/project-a/PROJ-001_test-cases.json`（含 ETC、CTC、`source_criterion`）  
- [x] `generate`：e2e `.spec.ts` + component `.test.tsx`；默认 `--type all`  
- [x] 仅 testid 定位；MSW **仅在** `it()` 内 `server.use(...)`，禁止全局挂 handler（见 TECH §3.9）
- [x] `test --layer all`：ETC-001、CTC-001 **PASS**；末尾自动刷新追溯报告  
- [x] `generate-pipeline` **不**执行 Playwright / Vitest  
- [x] `run-full` = `generate-pipeline` + `test` 可一键执行  
- [x] 追溯报告：`reports/project-a/PROJ-001_traceability.txt`；格式见 TECH §3.8；无测试时为 **NOT_RUN**  
- [x] 报告含覆盖率摘要：验收条数、已映射、已执行、PASS/FAIL、未覆盖  
- [x] `project-a` / `project-b`：yaml 加载成功；`intermediate` / `generated` / `reports` 路径互不串写（project-b **不要求**业务 PRD）  
- [x] yaml 无明文密码  

### M2 — 协作与报告卫生

- [x] `parse` 写入 `prd_content_hash`；`generate` 按指纹 skip / 阻断 / 归档  
- [x] 仅 version 变、hash 不变：**skip generate** 并 stderr 警告 `VERSION_DRIFT`  
- [x] 仅 hash 变、version 不变：**CI**（`CI=true`）exit 1 **`CONTENT_DRIFT`**；**本地** stderr 警告并允许继续，或使用 `--force` 强制重新生成（见 TECH §4.2）
- [x] **`parse` 与 `generate` 入口**均检测 Git 合并冲突标记 → **`MERGE_CONFLICT`**  
- [x] 版本升级：旧 spec 归档（旧版本号 + 时间戳）  
- [x] 生成链路写 `*.skeleton.txt`；`test` 后写正式报告并删除 skeleton  
- [x] `generate` / `generate-pipeline` 支持 `--force` 强制重生成  
- [x] 可选：`source_git_sha` 写入 intermediate（仅追溯）  

### M3 — Web 管理后台

- [x] 启动后端 + 前端，可访问仪表盘与项目详情  
- [x] 只读：PRD 列表、**Markdown 预览**、追溯报告  
- [x] **API 设置**：多条 LLM API（独立 Key / 接口地址 / 模型）；表单保存，无需手写 YAML；刷新后保留 Key 预览  
- [x] **Skill 库**：`.md` 规范上传、预览与编辑；工作台生成业务代码时选择 Skill（非环境页）  
- [x] 侧栏：仪表盘 / API 设置 / Skill 库；项目下 **工作台 / 环境 / AI 模型**  
- [x] **新建项目**（`POST /api/projects`）  
- [x] 触发：校验 / 解析 / 生成 / 生成链路 / 执行测试 / **一键全流程** / **分层 dev**（`POST /api/pipeline/dev`）  
- [x] 异步入队 + 日志轮询；Worker 并发默认 2；**任务取消**、**failure_hint**、**job-event 时间线**（持久化 `events_json`）  
- [x] 仪表盘 / 工作台：**按项目筛选**任务、展开日志、**清理历史**  
- [x] 读接口路径安全（防穿越、防 symlink）；**ensure_project_dirs** 自动创建项目 PRD 目录  

### M4 — 组件测试性能

- [x] Vitest 多 worker（**`pool: forks`**，禁止 threads 并行）；与 M1 单线程 baseline **pass/fail 集合一致**  
- [x] MSW mock 在并行下无串扰（各 `it()` 独立 `server.use`，`afterEach` 统一 `resetHandlers`）  
- [x] 可按 PRD 分批 `test --layer component`  

### M5 — 编辑与 CI

- [x] PRD / YAML 在线编辑与上传（写接口 + 安全单测）  
- [x] 项目 **环境** 表单：被测地址、repos、Vitest、webServer（`GET/PUT /api/projects/{id}/settings`）  
- [x] 项目 **AI 模型**：PRD 解析 / 失败分析 / 前端代码 / 后端代码 任务路由（可覆盖全局）  
- [x] PRD **Markdown 预览**（默认渲染正文；编辑时 **源码 | 预览** 切换）  
- [x] GitHub Actions / GitLab CI / Jenkins 模板（`ci/`）  
- [x] PRD 或 intermediate 变更 → `generate-pipeline`；日常 PR → `test`  
- [x] 自动 commit 生成物带 `[skip ci]`  

### M6 — 业务代码与 AI 自愈

- [x] `run.py dev`：OpenHands + `resolve_ai_for_task(dev_*)`；`--layer frontend|backend|all`；Skill 可覆盖  
- [x] 工作台：前端/后端 Skill 下拉 + 分层生成；**dev 完成提示** + **业务代码变更**（repos `git diff`）；产物面板；任务取消 / failure_hint / job-event 时间线  
- [x] `heal-loop`：须**显式调用**；202 异步入队；分析完成 `ANALYZED`；**无进展 `NO_IMPROVEMENT` 停止**；修复记录回收与清理  
- [x] 管理台：`heal-diff-preview`、采纳 / 放弃（含 `NO_IMPROVEMENT` / `PRD_DRIFT`）；`heal_runs` 审计含 token、`abort_reason`  

---

## 9. 用户流程

### 9.1 Web（M3）

选择项目 → **工作台**：PRD **预览**（或编辑）→ 生成链路 → 执行测试 → 查看追溯报告 / 产物 / **业务代码变更**（dev 后）  

侧栏全局：**API 设置**（多 profile LLM）、**Skill 库**（维护 OpenHands 规范）。  

项目子导航：**工作台**（流水线 + 业务代码生成时选 Skill + 智能修复） / **环境**（URL、repos） / **AI 模型**（任务→profile 路由）。

测试失败后：**分析失败原因** → 可选 **自动修复循环**；若无进展则停止并提示人工采纳补丁。

### 9.2 CI

- PRD / intermediate 变更：`generate-pipeline`  
- 已提交 spec / fixture / 业务仓变更：`test`  

### 9.3 本地调试（M1）

```bash
# 仅 parse 需要 LLM；generate 为模板、无 Key 也可跑（需已有 intermediate）
# 推荐在管理台「API 设置」配置；或环境变量：
export USE_LLM_PARSE=1
export ANTHROPIC_API_KEY=...          # 全局回退
export LLM_KEY_SONNET=...             # 按 profile 独立 Key（可选）

python3 run.py run-full \
  --project project-a \
  --prd prds/project-a/PROJ-001_login.md
```

---

## 10. 非功能需求

| 类别 | 要求 |
|------|------|
| 运行时 | Python 3.9+，Node.js 18+（依赖见 TECH §17） |
| 密钥 | LLM Key 存本地 `.env`（不进 git）：按 profile `LLM_KEY_<名称>`（如 `LLM_KEY_SONNET`）+ 可选全局 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`；`base_url` 进 `global.yaml`；项目鉴权凭据仅环境变量 |
| Git 资产 | 生成脚本、intermediate 提交；`meta.db`、`jobs.db` 不提交 |
| 报告 | M1 文本矩阵必达；Playwright HTML 为可选（`report.format` 含 html 时） |
| 可用性 | M3 起管理台内网可用；首版无登录 |
| 可观测 | CLI 非 0 退出 + 人类可读 stderr；M3 起任务 log 可轮询 |
| 错误码 | M2 起：`CONTENT_DRIFT`（CI 阻断）、`MERGE_CONFLICT`、`VERSION_DRIFT`（警告）、`AMBIGUOUS_COMPONENT_PATH`（generate） |

---

## 11. 里程碑依赖

| 里程碑 | 交付 | 依赖 |
|--------|------|------|
| M1 | CLI + fixture E2E/组件 | — |
| M2 | 指纹、skeleton、冲突扫描 | M1 |
| M3 | Web + 任务队列 | M1 |
| M4 | Vitest 并行 | M1 |
| M5 | 编辑 + CI | M2, M3 |
| M6 | dev + heal + 真实业务仓 | M2, M3, M5 |

---

## 12. 规格样例索引

| 文件 | 用途 |
|------|------|
| `templates/prd-template.md` | 业务 PRD 模板 |
| `prds/project-a/PROJ-001_login.md` | M1 基准 PRD |
| `config/projects/project-a.yaml` | M1 项目配置（与 TECH §11.1 一致） |
| `config/projects/project-b.yaml` | 多项目路径隔离（与 TECH §11.2 一致） |
| `config/global.yaml` | 全局配置（多模型 profile、`base_url`、`tasks.parse/heal/dev_*`；与 TECH §11.3 一致） |
| `skills/*.md` | OpenHands 开发规范（管理台 Skill 库；`dev` 引用，工作台可临时覆盖） |
| `.env.example` | 本地密钥模板（复制为 `.env`） |
| `tests/fixtures/mock-e2e/` | M1 E2E 静态站（实现时按 TECH §3.1 创建） |
| `tests/fixtures/mock-frontend/` | M1 Vitest 目标仓（实现时按 TECH §3.1 创建） |
| `tests/fixtures/test_data.json` | 全局占位符数据源（可被 `tests/fixtures/{project}/test_data.json` 覆盖） |
| `design/SKILL.md` | TypeUI 规范（M3 管理台 UI 前需就位） |

技术细节 → [TECH-DESIGN.md](./TECH-DESIGN.md)
