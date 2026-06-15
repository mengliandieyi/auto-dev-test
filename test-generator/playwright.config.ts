import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const reportDir = process.env.PLAYWRIGHT_REPORT_DIR || path.join(__dirname, '../reports/project-a');

export default defineConfig({
  testDir: path.join(__dirname, '../tests/generated'),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,

  reporter: [
    ['list'],
    ['json', { outputFile: path.join(reportDir, 'pw-results.json') }],
  ],

  webServer: {
    command: 'npx serve ../tests/fixtures/mock-e2e -l 4173',
    url: 'http://127.0.0.1:4173/login/',
    reuseExistingServer: process.env.CI ? false : true,
    cwd: __dirname,
  },

  use: {
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'project-a',
      testDir: path.join(__dirname, '../tests/generated/project-a/e2e'),
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.PROJECT_A_BASE_URL || 'http://127.0.0.1:4173',
        actionTimeout: 30_000,
        navigationTimeout: 60_000,
      },
    },
  ],
});
