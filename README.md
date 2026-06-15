# auto-dev-test

**规格仓库（spec-only）** · 文档版本 **4.4.1**

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

# 无 API Key 时默认规则 parse；需 LLM 时：
# export USE_LLM_PARSE=1 ANTHROPIC_API_KEY=...

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

# 终端 2：前端
cd admin && npm install && npm run dev
# → http://127.0.0.1:5173
```

- 仪表盘：项目列表 + 最近任务
- 项目详情：PRD 只读预览、流水线按钮（含 **一键全流程**）、追溯报告、日志轮询
- API：`POST /api/pipeline/*` 返回 **202** 异步入队；`GET /api/pipeline/jobs/{id}` 轮询 `log_tail`

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
| GET | `/api/projects/{id}/yaml` | 读取 YAML 原文 |
| PUT | `/api/projects/{id}/prds/{file}` | 保存 PRD |
| POST | `/api/projects/{id}/prds/upload` | 上传 `.md`（≤1MB） |

管理台：项目详情 → **编辑项目 YAML** / PRD **预览·编辑** / **上传 PRD**。

**CI 模板**（复制到流水线）：

- `ci/github-actions.yml` — PRD/intermediate 变更跑 `generate-pipeline`，PR 跑 `test`
- `ci/gitlab-ci.yml`、`ci/Jenkinsfile`

自动 commit 生成物：`chore: regenerate tests [skip ci]`

```bash
python3 -m unittest tests.test_m5_write_security -v
```

## M6 业务代码与 AI 自愈

```bash
# 业务开发（需 OpenHands CLI；未安装时打印 repos 指引）
python3 run.py dev --project project-a --prd prds/project-a/PROJ-001_login.md

# 自愈循环（默认 dry-run；--apply 才真正重写 generated spec）
python3 run.py heal-loop --project project-a --prd-id PROJ-001
python3 run.py heal-loop --project project-a --prd-id PROJ-001 --apply
```

- 流程：test → report → flaky 重跑 → preflight → analyze → fix → retest
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

# 或分步：
python3 -m unittest \
  tests.test_acceptance \
  tests.test_m2 \
  tests.test_path_safety \
  tests.test_m4_vitest \
  tests.test_m5_write_security \
  tests.test_m6_heal \
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
