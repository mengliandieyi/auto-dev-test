---
prd_id: PROJ-XXX          # 唯一ID，格式：{项目前缀}-{三位数字}，如 PROJ-001
version: 1.0.0            # 语义化版本，版本升级才触发测试重新生成
project: project-name     # 对应 config/projects/{project-name}.yaml
author: 作者姓名
date: YYYY-MM-DD
---

## 功能名称

<!-- 简短描述功能名，如：用户登录、商品搜索、订单提交 -->

## 需求说明

<!-- 每条必须包含 "作为/希望/以便" 三要素，每行一条 -->
- 作为 [用户角色]，我希望 [完成某操作]，以便 [达成某目标]

## 验收标准

<!-- 使用 checkbox 格式，每条对应一个测试用例；条件要具体可验证 -->
<!-- 每条验收标准会同时驱动 E2E（ETC-xxx）和组件测试（CTC-xxx）的追溯 -->
- [ ] 验收条件1（正向场景）
- [ ] 验收条件2（错误场景，如：输入错误时显示 "xxx" 提示）
- [ ] 验收条件3（边界场景）

## 接口设计

<!-- 列出本功能涉及的 API，格式：Method /path  body: {...}  response: {...} -->
<!-- 组件测试的 MSW mock 应与此保持一致 -->
- METHOD /api/path  body: {field1, field2}  response: {result}

## 页面交互

<!-- 与「使用流程」二选一；平台级 PRD 可用「使用流程」 -->
<!-- 步骤必须 ≥ 2 步；DOM 元素须标注 data-testid -->
<!-- 此章节驱动 Playwright E2E 测试生成 -->
1. 用户 [操作描述]（data-testid="元素id"）
2. 系统 [响应描述]
3. 用户 [操作描述]（data-testid="元素id"）
4. 成功路径：[最终状态描述]
5. 失败路径：显示 [错误提示]（data-testid="error-message"）

## 组件测试（可选）

<!-- 无此章节则只生成 E2E，不生成 Vitest 组件测试 -->
<!-- 每条对应一个 it() 用例（CTC-xxx）；关注组件逻辑，不重复 E2E 的完整链路 -->

**`component` 与 `component_path` 填写约定（重要）**

| 字段 | 谁填 | 规则 |
|------|------|------|
| `component` | **PM 必填** | React 组件名，如 `LoginForm`（与业务代码命名一致） |
| `component_path` | **PM 选填** | 前端源码相对路径；**不确定时可省略** |
| 路径解析 | **引擎** | 省略时在 `vitest.frontend_root` 下约定路径 → 递归搜索；多命中报 `AMBIGUOUS_COMPONENT_PATH` |

> PM **不应**猜测复杂目录结构。优先只写 `component: LoginForm`；`component_path` 由 generate 阶段自动解析。业务代码辅助（`run.py dev`）为 **M6** 能力。

<!-- 格式：
1. [用例描述]
   component: 组件名（必填）
   component_path: src/components/组件名.tsx（选填；省略则由引擎按组件名检索）
   props: { prop1: value }（可选，组件初始 props）
   actions:
     - type: fill | click | change
       testid: 元素 data-testid
       value: 输入值（可选）
   assertions:
     - type: text_visible | not_visible | enabled | disabled
       testid: 元素 data-testid
       text: 期望文本（type=text_visible 时必填）
   mocks:（可选，对应接口设计中的 API）
     - method: POST | GET | PUT | DELETE
       path: /api/path
       status: 200
       body: { response data }
-->

1. [正向用例描述]
   component: ComponentName
   # component_path 可省略，由引擎按组件名在业务仓检索
   actions:
     - type: fill
       testid: input-testid
       value: 正常值
     - type: click
       testid: submit-btn
   assertions:
     - type: text_visible
       testid: success-message
       text: 成功提示文案
   mocks:
     - method: POST
       path: /api/path
       status: 200
       body: { success: true }

## 测试数据

<!-- parse 阶段保留 {{valid.username}} 占位符；generate 阶段从 tests/fixtures/test_data.json 替换为字面量 -->
- 正向：username={{valid.username}}, password={{valid.password}}
- 反向：username={{valid.username}}, password={{invalid.password}}
- 边界：username=, password={{valid.password}}

## 页面设计（可选）

<!-- 供 TypeUI + Agent 设计业务 React 页面；不参与 parse（generate 为模板渲染） -->
<!-- 按复杂度分级填写，详见下方说明 -->

**复杂度**：简单 | 中等 | 复杂
（简单=登录表单；中等=列表+筛选；复杂=仪表盘多 Tab）

- 设计系统：design/SKILL.md（TypeUI slug: clean）
- 设计稿：无 | Figma 链接 | TypeUI 变体 #N | 截图路径
- 目标页面：/path
- 布局说明：（居中卡片、侧栏+内容区等）
- 组件清单：ComponentName → src/components/ComponentName.tsx
- data-testid 约定（与「页面交互」保持一致）：
  - element-id：说明

### 分级填写指南

| 复杂度 | 何时使用 | 设计稿 | 布局说明 |
|--------|----------|--------|----------|
| 简单 | 登录、单表单、确认页 | 不需要，TypeUI 即可 | 2～3 句即可 |
| 中等 | 列表、分步向导 | TypeUI 出 2～3 版，PRD 写明选用哪版 | 需要写清信息架构 |
| 复杂 | 仪表盘、复杂表格 | **必须** Figma 链接或截图 | 需要分区、Tab、状态说明 |
