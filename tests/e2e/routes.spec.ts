import { test, expect } from '@playwright/test';

test.describe('QUIZVERSE Route Smoke Tests', () => {
  test('Landing page renders title and 3D status badge', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/QUIZVERSE/);
    await expect(page.locator('text=The Next Dimension of')).toBeVisible();
    await expect(page.locator('text=Interactive 3D Core')).toBeVisible();
  });

  test('Candidate exam portal placeholder loads token route', async ({ page }) => {
    await page.goto('/exam/demo-2024');
    await expect(page.locator('text=Candidate Examination Portal')).toBeVisible();
    await expect(page.locator('text=demo-2024')).toBeVisible();
  });

  test('Login page placeholder renders access gateway form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('text=Sign In to QUIZVERSE')).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('Admin dashboard renders command center', async ({ page }) => {
    await page.goto('/admin/dashboard');
    await expect(page.locator('text=Platform Command Center')).toBeVisible();
    await expect(page.locator('text=Module Readiness Matrix')).toBeVisible();
  });

  test('Admin question bank route renders', async ({ page }) => {
    await page.goto('/admin/question-bank');
    await expect(page.locator('text=Question Bank')).toBeVisible();
  });

  test('Admin quizzes route renders', async ({ page }) => {
    await page.goto('/admin/quizzes');
    await expect(page.locator('text=Quizzes & Examinations')).toBeVisible();
  });

  test('Admin settings route renders', async ({ page }) => {
    await page.goto('/admin/settings');
    await expect(page.locator('text=System Settings')).toBeVisible();
  });
});
