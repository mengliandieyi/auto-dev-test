---
prd_id: PROJ-001
version: 1.0.0
project: project-a
author: 示例作者
date: 2026-06-15
---

## 功能名称

用户登录

## 需求说明

- 作为 注册用户，我希望 通过账号密码登录系统，以便 访问个人中心和系统功能
- 作为 注册用户，我希望 在多次输错密码后账号被临时锁定，以便 防止暴力破解

## 验收标准

- [ ] 正确的账号密码登录成功后，跳转至 /dashboard 页面，顶部显示用户姓名
- [ ] 错误密码登录失败时，原地显示"账号或密码错误"提示，密码框内容清空
- [ ] 账号不存在时，显示"账号或密码错误"提示（不区分账号不存在和密码错误，安全考虑）
- [ ] 连续 5 次密码错误后，账号锁定 15 分钟，提示"账号已锁定，请 15 分钟后重试"
- [ ] 账号或密码为空时，"登录"按钮不可点击

## 接口设计

- POST /api/auth/login  body: {username: string, password: string}  response: {token: string, user: {id, name, email}}
- POST /api/auth/logout  header: Authorization  response: {success: boolean}

## 页面交互

<!-- 驱动 Playwright E2E 测试 -->
1. 用户打开登录页 /login
2. 输入账号（邮箱格式）（data-testid="username-input"）
3. 输入密码（至少 8 位）（data-testid="password-input"）
4. 点击"登录"按钮（data-testid="login-btn"）
5. 成功路径：跳转至 /dashboard，顶部导航显示用户姓名（data-testid="user-name"）
6. 失败路径：原地显示错误提示（data-testid="error-message"），密码框清空，账号框保留内容
7. 锁定路径：显示锁定提示（data-testid="lock-message"），"登录"按钮变为不可用

## 组件测试（可选）

<!-- 驱动 Vitest + RTL 组件测试；关注组件内部逻辑，不重复 E2E 完整链路 -->

1. 错误密码时 LoginForm 显示错误提示
   component: LoginForm
   component_path: src/components/LoginForm.tsx
   actions:
     - type: fill
       testid: username-input
       value: test@example.com
     - type: fill
       testid: password-input
       value: WrongPass!
     - type: click
       testid: login-btn
   assertions:
     - type: text_visible
       testid: error-message
       text: 账号或密码错误
   mocks:
     - method: POST
       path: /api/auth/login
       status: 401
       body: { "message": "账号或密码错误" }

2. 账号或密码为空时登录按钮禁用
   component: LoginForm
   component_path: src/components/LoginForm.tsx
   actions:
     - type: fill
       testid: username-input
       value: test@example.com
     - type: fill
       testid: password-input
       value: ""
   assertions:
     - type: disabled
       testid: login-btn

3. 账号被锁定时显示锁定提示
   component: LoginForm
   component_path: src/components/LoginForm.tsx
   actions:
     - type: fill
       testid: username-input
       value: locked@example.com
     - type: fill
       testid: password-input
       value: AnyPass1!
     - type: click
       testid: login-btn
   assertions:
     - type: text_visible
       testid: lock-message
       text: 账号已锁定，请 15 分钟后重试
     - type: disabled
       testid: login-btn
   mocks:
     - method: POST
       path: /api/auth/login
       status: 423
       body: { "message": "账号已锁定，请 15 分钟后重试" }

## 页面设计（可选）

<!-- 此章节供 TypeUI + Agent 设计 React 页面时参考，不影响测试生成 -->
**复杂度**：简单

- 设计系统：design/SKILL.md（TypeUI slug: clean）
- 设计稿：无（简单页面，TypeUI + 文字布局即可）
- 目标页面：/login
- 布局说明：居中卡片，最大宽度 400px，主按钮 primary 色，圆角 md
- 组件清单：LoginForm → src/components/LoginForm.tsx
- data-testid 约定（与「页面交互」章节保持一致）：
  - username-input：账号输入框
  - password-input：密码输入框
  - login-btn：登录按钮
  - error-message：错误提示
  - lock-message：锁定提示
  - user-name：登录成功后顶部导航用户名

## 测试数据

- 正向：username=test@example.com, password=Test1234!
- 反向（错误密码）：username=test@example.com, password=WrongPass!
- 反向（不存在账号）：username=notexist@example.com, password=Test1234!
- 反向（已锁定账号）：username=locked@example.com, password=AnyPass1!
- 边界（空账号）：username=, password=Test1234!
- 边界（空密码）：username=test@example.com, password=
