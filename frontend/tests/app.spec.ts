import { test, expect } from '@playwright/test';

test('App loads without parsing errors and shows AuthPage when unauthenticated', async ({ page }) => {
  let consoleErrors = [];
  page.on('pageerror', err => consoleErrors.push(err.message));

  // Mock backend endpoints so auth fails normally and brings us to login screen
  await page.route('**/api/v1/auth/me', route => {
    route.fulfill({ status: 401, body: 'Unauthorized' });
  });

  await page.goto('http://localhost:5173');

  // Ensure login screen renders and no syntax error occurred
  await expect(page.locator('text=Login to Vidyalaya Saathi').first()).toBeVisible({ timeout: 10000 });
  expect(consoleErrors.length).toBe(0);
});
