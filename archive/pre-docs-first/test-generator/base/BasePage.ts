import { Page, expect } from '@playwright/test';

/**
 * BasePage — 所有 Page Object 的基类
 * 统一封装 data-testid 选择器操作，与 React 组件的 data-testid 属性对应。
 * 生成的测试脚本通过此基类操作页面，不直接使用 CSS/XPath 选择器。
 */
export class BasePage {
  constructor(protected page: Page) {}

  // ── 导航 ─────────────────────────────────────────────────────────────────

  async navigate(path: string) {
    const baseUrl = process.env.BASE_URL || 'http://localhost:3000';
    await this.page.goto(`${baseUrl}${path}`);
  }

  async waitForUrl(urlPattern: string | RegExp) {
    await this.page.waitForURL(urlPattern);
  }

  // ── 元素操作（data-testid） ────────────────────────────────────────────

  async fillByTestId(testId: string, value: string) {
    await this.page.getByTestId(testId).fill(value);
  }

  async clickByTestId(testId: string) {
    await this.page.getByTestId(testId).click();
  }

  async selectByTestId(testId: string, value: string) {
    await this.page.getByTestId(testId).selectOption(value);
  }

  async clearByTestId(testId: string) {
    await this.page.getByTestId(testId).clear();
  }

  async typeByTestId(testId: string, value: string) {
    await this.page.getByTestId(testId).pressSequentially(value);
  }

  // ── 等待 ─────────────────────────────────────────────────────────────────

  async waitForTestId(testId: string) {
    await this.page.getByTestId(testId).waitFor({ state: 'visible' });
  }

  async waitForTestIdHidden(testId: string) {
    await this.page.getByTestId(testId).waitFor({ state: 'hidden' });
  }

  // ── 断言 ─────────────────────────────────────────────────────────────────

  async assertTextByTestId(testId: string, expectedText: string) {
    await expect(this.page.getByTestId(testId)).toContainText(expectedText);
  }

  async assertVisibleByTestId(testId: string) {
    await expect(this.page.getByTestId(testId)).toBeVisible();
  }

  async assertHiddenByTestId(testId: string) {
    await expect(this.page.getByTestId(testId)).toBeHidden();
  }

  async assertUrl(expectedPath: string) {
    await expect(this.page).toHaveURL(new RegExp(expectedPath.replace('/', '\\/')));
  }

  async assertTitle(expectedTitle: string) {
    await expect(this.page).toHaveTitle(expectedTitle);
  }

  async assertValueByTestId(testId: string, expectedValue: string) {
    await expect(this.page.getByTestId(testId)).toHaveValue(expectedValue);
  }

  async assertEnabledByTestId(testId: string) {
    await expect(this.page.getByTestId(testId)).toBeEnabled();
  }

  async assertDisabledByTestId(testId: string) {
    await expect(this.page.getByTestId(testId)).toBeDisabled();
  }

  // ── 截图（失败时自动调用） ──────────────────────────────────────────────

  async screenshot(name: string) {
    await this.page.screenshot({
      path: `reports/screenshots/${name}-${Date.now()}.png`,
      fullPage: true,
    });
  }
}
