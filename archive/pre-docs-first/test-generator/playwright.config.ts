import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 多项目配置
 * 每个业务项目对应一个 Playwright project，通过 --project 参数指定。
 * base_url 优先从环境变量读取（CI 注入），其次使用 yaml 中的默认值。
 */
export default defineConfig({
  testDir: '../tests/generated',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['list'],
    ['json', { outputFile: 'reports/pw-results.json' }],
    ['html', { outputFolder: 'reports/playwright-report', open: 'never' }],
  ],

  use: {
    // 截图/视频：失败时保留
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'project-a',
      testDir: '../tests/generated/project-a/e2e',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.PROJECT_A_BASE_URL || 'https://staging.project-a.com',
        actionTimeout: 30_000,
        navigationTimeout: 60_000,
      },
    },
    // 新增项目时复制上方 project 块，修改 name / testDir / baseURL
  ],
});
