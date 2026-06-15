/**
 * vitest.setup.ts — 全局测试环境设置
 *
 * 职责：
 * 1. 扩展 expect 断言（@testing-library/jest-dom）
 * 2. 启动/重置/关闭 MSW Node server（拦截组件内的 API 请求）
 *
 * MSW mock 定义在各测试文件中通过 server.use(http.post(...)) 注入；
 * 此处只负责生命周期管理。
 */

import '@testing-library/jest-dom';
import { server } from '@testing/msw/server';

// 在所有测试前启动 MSW server
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
});

// 每个测试后重置 handler，防止污染下一个测试
afterEach(() => {
  server.resetHandlers();
});

// 所有测试结束后关闭 server
afterAll(() => {
  server.close();
});
