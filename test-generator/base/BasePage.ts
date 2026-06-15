import { Page, expect } from '@playwright/test';

/** E2E 页面对象基类（TECH §3.5） */
export class BasePage {
  constructor(
    protected readonly page: Page,
    protected readonly baseUrl: string,
  ) {}

  async navigate(path: string) {
    const url = path.startsWith('http') ? path : `${this.baseUrl.replace(/\/$/, '')}${path}`;
    await this.page.goto(url);
  }

  async fillByTestId(testId: string, value: string) {
    await this.page.getByTestId(testId).fill(value);
  }

  async clickByTestId(testId: string) {
    await this.page.getByTestId(testId).click();
  }

  async assertTextByTestId(testId: string, text: string) {
    await expect(this.page.getByTestId(testId)).toContainText(text);
  }

  async assertVisibleByTestId(testId: string) {
    await expect(this.page.getByTestId(testId)).toBeVisible();
  }

  async assertUrl(pathFragment: string) {
    await expect(this.page).toHaveURL(new RegExp(pathFragment));
  }

  async waitForTestId(testId: string) {
    await this.page.getByTestId(testId).waitFor();
  }
}
