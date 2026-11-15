const { test, expect, recordTitle } = require("../support");

test.describe("home page", () => {
  test("shows the recent videos, the trends and the channels", async ({
    page,
  }) => {
    await page.goto("/");
    for (const name of ["RECENT", "TRENDS", "CHANNELS"]) {
      await expect(
        page.getByRole("heading", { name, exact: true })
      ).toBeVisible();
    }
    // Trends and channels link to searches
    await expect(
      page.getByRole("link", { name: "Higgs", exact: true })
    ).toHaveAttribute("href", /^\/search\?/);
    await expect(
      page.getByRole("link", { name: "Physics", exact: true })
    ).toHaveAttribute("href", /^\/search\?/);
  });

  test("opens a recent video", async ({ page }) => {
    await page.goto("/");
    const recent = page.locator("a[href^='/record/']").first();
    await expect(recent).toBeVisible();
    const title = (await recent.innerText()).trim();
    await recent.click();
    await expect(page).toHaveURL(/\/record\/\d+$/);
    await expect(recordTitle(page, title)).toBeVisible();
  });

  test("searches from the header", async ({ page, data }) => {
    const word = data.video.metadata.title.title.split(/\s+/).pop();
    await page.goto("/");
    const box = page.getByRole("banner").getByRole("textbox", {
      name: "Search CDS",
    });
    await box.fill(word);
    await box.press("Enter");
    await expect(page).toHaveURL(/\/search\?/);
    expect(new URL(page.url()).searchParams.get("q")).toBe(word);
    await expect(page.getByText(/Found \d+ results?/)).toBeVisible();
    await expect(
      page.getByRole("link", { name: data.video.metadata.title.title })
    ).toBeVisible();
  });

  test("shows the footer links", async ({ page }) => {
    await page.goto("/");
    const footer = page.getByRole("contentinfo");
    for (const name of ["About", "Help & Contact", "FAQ", "Terms of Use"]) {
      await expect(footer.getByRole("link", { name })).toBeVisible();
    }
  });
});
