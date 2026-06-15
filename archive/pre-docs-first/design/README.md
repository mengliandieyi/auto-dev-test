# TypeUI 设计规范层

## 目录说明

```
design/
├── SKILL.md   # TypeUI 设计系统（Clean 主题，由 npx typeui.sh pull 拉取）
└── README.md  # 本文件：团队流程与约定
```

`SKILL.md` 是 TypeUI 生成的设计规范文件，供 AI Agent（Cursor / Claude Code）在设计业务前端页面时参考。

---

## 层级分工

| 层级 | 工具 | PRD 章节 | 输出位置 |
|------|------|----------|----------|
| 设计 | TypeUI + Agent | 页面设计（可选）+ 页面交互 | 业务仓库（如 `../acme-web`） |
| E2E 测试 | Playwright | 页面交互 | `tests/generated/{project}/e2e/` |
| 组件测试 | Vitest + RTL | 组件测试（可选） | `tests/generated/{project}/component/` |

**data-testid 是设计层与测试层的唯一契约**：TypeUI Agent 生成的 React 组件必须包含 PRD「页面交互」章节里标注的所有 `data-testid`，否则 E2E 测试无法通过。

---

## 团队使用流程

### 第一步：写 PRD

按 `templates/prd-template.md` 格式编写，关键点：

- `## 页面交互` 步骤里标注所有 `data-testid`（必填）
- `## 组件测试` 写 Vitest 用例（可选）
- `## 页面设计` 写 UI 布局说明（可选，供 TypeUI Agent 使用）

示例见 `prds/project-a/PROJ-001_login.md`。

### 第二步：用 TypeUI Agent 设计页面

在业务前端仓（如 `../acme-web`）中，通过以下任一方式接入 TypeUI：

**方式 A：本地 SKILL.md 引用**

在 Cursor / Claude Code 的 AI 提示中直接引用本文件：

```
根据 auto-dev-test 仓库 prds/project-a/PROJ-001_login.md 的页面交互，
使用 auto-dev-test/design/SKILL.md 的 TypeUI 设计规范实现登录页。

要求：
1. React + TypeScript；样式遵循 SKILL.md 的 colors/typography/spacing tokens
2. 页面路由与 PRD「页面交互」步骤一一对应
3. 所有交互元素必须添加 PRD 中标注的 data-testid（这是测试的唯一定位依据）
4. 禁止用不稳定的 CSS 类名替代 data-testid

需要多版布局时可以说：Give me three variations for this login card.
```

**方式 B：TypeUI MCP（推荐，需账号）**

1. 在 [typeui.sh](https://www.typeui.sh) 注册账号，上传或创建设计系统
2. 在控制台点击 Publish，获取 MCP URL：`https://mcp.typeui.sh/mcp`
3. 在 Cursor 的 MCP 设置中添加该 URL
4. Cursor Agent 会自动读取设计规范，无需手动引用文件

### 第三步：运行测试验证

页面开发完成后，回到 `auto-dev-test` 仓库运行完整测试链路：

```bash
# 全流程：PRD 校验 → 解析 → 生成测试脚本 → 报告
python3 run.py generate-pipeline --project project-a --prd prds/project-a/PROJ-001_login.md

# 单独运行 E2E 测试
npx playwright test tests/generated/project-a/e2e/

# 单独运行组件测试（Phase 1.5）
npm run test:component
```

---

## data-testid 命名约定

TypeUI Agent 生成 UI 时必须遵守以下约定：

| 元素类型 | 命名规则 | 示例 |
|----------|----------|------|
| 输入框 | `{字段名}-input` | `username-input` |
| 按钮 | `{动作}-btn` | `login-btn` |
| 错误提示 | `{场景}-message` 或 `error-message` | `error-message`、`lock-message` |
| 导航/展示 | `{内容名}` | `user-name`、`dashboard-title` |

PRD「页面交互」里标注的 testid 即为约束，Agent 不得自行创造新名称。

---

## 更新设计规范

如需切换或更新 TypeUI 主题：

```bash
# 查看可用主题
npx typeui.sh list

# 拉取新主题（覆盖当前 SKILL.md）
cd /Users/admin/Desktop/auto-dev-test
npx typeui.sh pull <slug> --format design
mv DESIGN.md design/SKILL.md

# 或直接拉取 skill 格式到对应工具目录
npx typeui.sh pull <slug> --format skill --providers claude
```

当前主题：**Clean**（slug: `clean`）
可选主题包括：`paper`、`neumorphism`、`bento`、`premium`、`glassmorphism`、`neobrutalism`、`bold` 等（共 77 个）
