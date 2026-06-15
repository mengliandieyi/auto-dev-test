import { Page } from '@playwright/test';
import { BasePage } from '../base/BasePage';

/**
 * LoginPage — 登录页 Page Object
 * 示例：展示如何基于 BasePage 封装具体页面操作。
 * 生成的测试脚本可直接使用此类，也可让 AI 生成类似结构。
 */
export class LoginPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  /** 打开登录页 */
  async open() {
    await this.navigate('/login');
  }

  /** 填写并提交登录表单 */
  async login(username: string, password: string) {
    await this.fillByTestId('username-input', username);
    await this.fillByTestId('password-input', password);
    await this.clickByTestId('login-btn');
  }

  /** 断言登录成功（跳转到 dashboard） */
  async assertLoginSuccess() {
    await this.assertUrl('/dashboard');
  }

  /** 断言登录失败（显示错误提示） */
  async assertLoginError(expectedMessage?: string) {
    await this.assertVisibleByTestId('error-message');
    if (expectedMessage) {
      await this.assertTextByTestId('error-message', expectedMessage);
    }
  }
}
