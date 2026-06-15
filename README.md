# auto-dev-test

**规格仓库（spec-only）** · 文档版本 **4.4.2**（单一来源见根目录 `VERSION`，`python3 scripts/sync_version.py` 同步 npm 包版本）

| 文档 | 职责 |
|------|------|
| [docs/PRD.md](docs/PRD.md) | 产品需求、里程碑验收、**§1.5 里程碑导读** |
| [docs/TECH-DESIGN.md](docs/TECH-DESIGN.md) | 架构、接口契约、配置规范 |

代码按 **M1→M6** 实现；验收以 PRD 为准，实现以 TECH-DESIGN 为准。

## 规格样例

- [templates/prd-template.md](templates/prd-template.md)
- [prds/project-a/PROJ-001_login.md](prds/project-a/PROJ-001_login.md)
- [config/projects/project-a.yaml](config/projects/project-a.yaml)（已与 TECH §11.1 对齐）
- [tests/fixtures/test_data.json](tests/fixtures/test_data.json)

## M1 快速开始

```bash
pip3 install -r requirements.txt
npm install
npx playwright install chromium   # 首次 E2E 需要

# 无 API Key 时默认规则 parse；需 LLM 时可在管理台「API 设置」配置，或：
# export USE_LLM_PARSE=1
# export ANTHROPIC_API_KEY=...   # 全局回退；推荐按 profile 使用 LLM_KEY_SONNET 等

python3 run.py run-full --project project-a --prd prds/project-a/PROJ-001_login.md
```

- E2E：`tests/fixtures/mock-e2e/` + Playwright webServer，`base_url` `http://127.0.0.1:4173`
- 组件：`tests/fixtures/mock-frontend/` + Vitest + MSW
- LLM：**仅 `parse` 可选**；`generate` 为确定性模板、不调 LLM
- 门禁：**ETC-001** + **CTC-001** 必须通过；其余用例生成但 `skip`

## M2 协作安全

- `parse` 写入 `prd_content_hash`；`generate` 按 hash + version 判定 skip / archive / `CONTENT_DRIFT`
- `generate-pipeline` 输出 `*.skeleton.txt`；`test` 后写正式报告并删除 skeleton
- CI 下 hash 变而 version 不变 → exit 1 `CONTENT_DRIFT`；本地仅警告，可用 `--force` 强制重生成

```bash
# 草稿迭代（本地改 PRD 正文未 bump version）
python3 run.py generate-pipeline --project project-a --prd prds/project-a/PROJ-001_login.md

# 强制重生成
python3 run.py generate --project project-a --prd-id PROJ-001 --force
```

## M3 Web 管理后台

```bash
# 终端 1：API（Worker 并发默认 2）
pip3 install -r requirements.txt
python3 -m uvicorn api.main:app --reload --port 8000

# 终端 2：前端（须先启动，否则 5173 无法访问）
cd admin && npm install && npm run dev
# → http://127.0.0.1:5173  （Vite 已绑定 IPv4）
```

- 仪表盘：项目列表 + 最近任务（**按项目筛选**、展开日志时间线）；侧栏显示 **API 在线/离线**
- **API 设置**（`/settings`）：添加多条 LLM API（名称、接口类型、Key、地址、模型）；每条 profile **独立** Key（`.env` 中 `LLM_KEY_<名称>`）与 `base_url`（`global.yaml`）；支持 Anthropic 官方、DashScope 代理、OpenAI 兼容等
- **Skill 库**（`/skills`）：左列表 + 右编辑器；上传/拖放 `.md`、新建空白；默认 **预览**，可切 **源码**
- **项目**：侧栏选项目后 → **工作台** / **环境** / **AI 模型**；支持 **新建项目**（`POST /api/projects`）
- **工作台**：PRD 列表、流水线、业务代码（Skill 下拉）、**dev 完成后提示 repos 路径**、**业务代码变更**（git diff）、追溯报告（Markdown 预览）、产物、Heal 面板；**job-event 时间线**；执行记录默认 10 条可展开；**按项目清理历史**
- **智能修复**：分析 → `ANALYZED`；自动修复循环异步入队；**失败用例未减少则 `NO_IMPROVEMENT` 停止**，可人工采纳补丁；修复记录默认 5 条 + 清理历史
- **环境**（`/projects/:id/config`）：被测地址、repos、Vitest、webServer
- **AI 模型**（`?tab=ai`）：PRD 解析 / 失败分析 / 前端代码 / 后端代码 四项任务绑定 profile（可「使用全局默认」）
- API：`POST /api/pipeline/*` 返回 **202** 异步入队；`GET /api/pipeline/jobs/{id}` 轮询 `log_tail`；失败时返回 `failure_hint`；仪表盘 / 修复记录支持 **清理历史**

## M4 组件测试并行

- Vitest **`pool: forks`** + `isolate: true`（禁止 threads 多 worker，避免 MSW 串扰）
- 默认 `max_workers: 2`（可在 `config/projects/*.yaml` 的 `vitest.max_workers` 调整）
- MSW：各 `it()` 内 `server.use()`，`vitest.setup.ts` 统一 `afterEach(resetHandlers)`
- 按 PRD 分批：`python3 run.py test --project project-a --layer component --prd-id PROJ-001`

```bash
# 对比 forks 与单线程 baseline（CI 可跑）
python3 -m unittest tests.test_m4_vitest -v
```

## M5 编辑与 CI

**Web 写接口（需启动 API）：**

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/projects/{id}` | 保存项目 YAML |
| GET/PUT | `/api/projects/{id}/settings` | 项目环境 / AI 任务路由表单 |
| POST | `/api/projects` | 新建项目 |
| GET | `/api/projects/{id}/yaml` | 读取 YAML 原文 |
| PUT | `/api/projects/{id}/prds/{file}` | 保存 PRD |
| POST | `/api/projects/{id}/prds/upload` | 上传 `.md`（≤1MB） |
| GET/PUT | `/api/settings/ai` | 读取/保存多模型 profile（含每 profile `base_url`、独立 Key） |
| GET | `/api/settings/ai-resolved` | 解析后实际模型（可选 `?project_id=`） |
| PUT | `/api/settings/credentials` | 保存 `USE_LLM_PARSE` 等全局开关 |
| GET/PUT/DELETE | `/api/skills/{id}` | Skill 库读写 |
| POST | `/api/skills/import` | 上传 `.md` |
| GET | `/api/projects/{id}/artifacts/{prd_id}/*` | intermediate / 生成物 / 变更列表 |
| GET | `/api/projects/{id}/repos/changes?layer=all` | 业务仓 git status / diff（只读） |

管理台：侧栏 **API 设置**、**Skill 库**；项目 **工作台** PRD 预览/编辑/上传；**环境** / **AI 模型** 分 tab 保存。

**CI 模板**（复制到流水线）：

- `ci/github-actions.yml` — PRD/intermediate 变更跑 `generate-pipeline`，PR 跑 `test`
- `ci/gitlab-ci.yml`、`ci/Jenkinsfile`

自动 commit 生成物：`chore: regenerate tests [skip ci]`

```bash
python3 -m unittest tests.test_m5_write_security -v
```

## M6 业务代码与 AI 自愈

**业务仓样板**（与 `config/projects/project-a.yaml` 的 `repos` 相对路径对应）：

```bash
bash scripts/setup-business-repos.sh   # 检查 acme-web/acme-api、npm install、OpenHands
```

**OpenHands CLI**（`dev` 必需）：

```bash
uv tool install openhands --python 3.12   # 需 ~/.local/bin 在 PATH
openhands --version
```

```bash
# 业务开发（需 OpenHands CLI；未安装时打印 repos 指引）
python3 run.py dev --project project-a --prd prds/project-a/PROJ-001_login.md
python3 run.py dev --project project-a --prd prds/project-a/PROJ-001_login.md --layer frontend
python3 run.py dev --project project-a --prd prds/project-a/PROJ-001_login.md --layer backend --skill-frontend clean-ui --skill-backend go-api

# 自愈循环（默认 dry-run；--apply 才真正重写 generated spec）
python3 run.py heal-loop --project project-a --prd-id PROJ-001
python3 run.py heal-loop --project project-a --prd-id PROJ-001 --apply
```

- `dev`：`--layer frontend|backend|all`；Skill 默认读 `config/projects/*.yaml` 的 `dev.frontend_skill` / `dev.backend_skill`，可用 `--skill-*` 或工作台下拉覆盖
- 工作台 **dev 成功**后提示业务仓路径，**业务代码变更**面板只读展示 `repos` 下 `git status` / `git diff`（`GET /api/projects/{id}/repos/changes`）
- 流程：test → report → flaky 重跑 → preflight → analyze → fix → retest
- **无进展停止**：`config/global.yaml` → `heal.stop_on_no_improvement: true`（默认）；失败用例集合未缩小或补丁为空 → `NO_IMPROVEMENT`，管理台可采纳 / 放弃
- 管理台采纳补丁：复制 `heal/fix-runs/{id}/tests/generated/` 预览文件到正式目录（非盲目重新 generate）
- 审计：`heal_runs` 表（`tests/generated/jobs.db`）
- 管理台：**分析失败** / **heal-loop** / diff 预览 / 采纳·放弃

```bash
python3 -m unittest tests.test_m6_heal -v
```

## 里程碑验收（M1–M6）

一键跑通 PRD §8 关键项 + 单元测试：

```bash
# 一键验收
bash scripts/verify.sh

# 仅单元测试
bash scripts/run-unit-tests.sh

# 或分步：
python3 -m unittest \
  tests.test_acceptance \
  tests.test_m2 \
  tests.test_path_safety \
  tests.test_m4_vitest \
  tests.test_m5_write_security \
  tests.test_m6_heal \
  tests.test_env_store \
  tests.test_ai_resolver \
  tests.test_skills_api \
  tests.test_dev_layer \
  tests.test_heal_fix \
  tests.test_list_prds \
  tests.test_project_settings \
  tests.test_create_project \
  tests.test_artifacts_api \
  tests.test_component_path_resolver \
  tests.test_validator_optional -v
```

| 里程碑 | 验收要点 |
|--------|----------|
| M1 | CLI、`AuthHelper` fixture skip、`run-full` 门禁 PASS |
| M2 | `prd_content_hash`、skeleton 报告、`CONTENT_DRIFT` / `VERSION_DRIFT` |
| M3 | API + Admin；`uvicorn api.main:app --port 8000` |
| M4 | Vitest `pool: forks`；`test_m4_vitest` baseline 一致 |
| M5 | 写接口安全单测；`ci/` + `.github/workflows/` |
| M6 | `dev` / `heal-loop`；`heal_runs` 审计 |

`test-generator/base/` 含 `BasePage.ts`、`AuthHelper.ts`（M1 默认 skip 鉴权；M6 设 `AUTH_MODE=real`）。

历史实现：[archive/pre-docs-first/](archive/pre-docs-first/)
