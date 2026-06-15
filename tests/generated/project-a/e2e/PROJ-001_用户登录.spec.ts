/**
 * AUTO-GENERATED — DO NOT EDIT MANUALLY
 * PRD: PROJ-001 v1.0.0 (project-a)
 * Hash: 9efe329dcd748d46138792c49219da0672d224531d6aae41b270714a13cc6850
 * Layer: e2e
 * Generated: 2026-06-15T10:36:59.863222+00:00
 */
import { test, expect } from '@playwright/test';

test.describe('用户登录', () => {
  test('ETC-001: 正向登录', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('username-input').fill("test@example.com");
    await page.getByTestId('password-input').fill("Test1234!");
    await page.getByTestId('login-btn').click();
    await expect(page).toHaveURL(new RegExp("/dashboard"));
    await expect(page.getByTestId('user-name')).toBeVisible();
  });

  test('ETC-002: 错误密码', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('username-input').fill("test@example.com");
    await page.getByTestId('password-input').fill("WrongPass!");
    await page.getByTestId('login-btn').click();
    await expect(page.getByTestId('error-message')).toContainText("账号或密码错误");
  });

});
