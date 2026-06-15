/**
 * tests/msw/server.ts — MSW Node.js 拦截服务
 *
 * 供 vitest.setup.ts 引用，管理 MSW server 生命周期。
 * 测试文件中通过 server.use(http.post(...)) 动态添加 handler。
 *
 * Phase 1.5 实现时，generate_component.py 生成的 .test.tsx 文件
 * 会自动引入此 server 并注册 mock handler。
 */

import { setupServer } from 'msw/node';

// 默认不添加任何 handler；各测试文件自行注入
export const server = setupServer();
