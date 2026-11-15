const { test, expect, login, userMenu } = require("../support");

test.describe("authentication", () => {
  test("logs in and out", async ({ page, users }) => {
    await login(page, users.user);
    const logout = page.getByRole("link", { name: "Log out" });
    // The menu opens once the page scripts are ready
    await expect(async () => {
      await userMenu(page, users.user).click();
      await expect(logout).toBeVisible({ timeout: 1000 });
    }).toPass();
    await logout.click();
    await expect(
      page.getByRole("banner").getByRole("link", { name: "Log in" })
    ).toBeVisible();
  });

  test("refuses a wrong password", async ({ page, users }) => {
    await page.goto("/login/");
    await page.locator("input[name=email]").fill(users.user.email);
    await page.locator("input[name=password]").fill("not-the-password");
    await page.locator("button[type=submit]").click();
    await expect(page.getByText(/invalid password/i)).toBeVisible();
    await expect(userMenu(page, users.user)).toHaveCount(0);
  });

  test("asks to log in before uploading", async ({ page }) => {
    await page.goto("/deposit");
    await expect(page).toHaveURL(/\/login\/\?next=/);
  });
});
