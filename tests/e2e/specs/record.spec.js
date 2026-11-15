const { test, expect, recordTitle } = require("../support");

function plainText(html) {
  return html
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

test.describe("video page", () => {
  test("shows the metadata of the video", async ({ page, data }) => {
    const { metadata } = data.video;
    await page.goto(`/record/${data.video.id}`);
    await expect(recordTitle(page, metadata.title.title)).toBeVisible();
    // The first words of the description
    if (metadata.description) {
      const words = plainText(metadata.description).split(" ").slice(0, 4);
      await expect(page.getByText(words.join(" ")).first()).toBeVisible();
    }
    await expect(
      page.getByRole("listitem").filter({ hasText: metadata.duration }).first()
    ).toBeVisible();
    await expect(page.getByText(/\d+ Views?/)).toBeVisible();
  });

  test("plays the video in the previewer", async ({ page, data }) => {
    await page.goto(`/record/${data.video.id}`);
    const player = page.locator("iframe").first();
    await expect(player).toHaveAttribute(
      "src",
      new RegExp(`/record/${data.video.id}/preview/`)
    );
    // The previewer page renders a player
    await expect(
      page.frameLocator("iframe").first().locator("video").first()
    ).toBeAttached();
  });

  test("links the keywords to searches", async ({ page, data }) => {
    const keywords = data.video.metadata.keywords || [];
    test.skip(keywords.length === 0, "the video has no keywords");
    const keyword = keywords[0].name;
    await page.goto(`/record/${data.video.id}`);
    const link = page.getByRole("link", { name: keyword, exact: true });
    await expect(link).toHaveAttribute(
      "href",
      `/search?q=keywords.name:"${keyword}"`
    );
    await link.click();
    await expect(page).toHaveURL(/\/search\?/);
    await expect(page.getByText(/Found \d+ results?/)).toBeVisible();
  });

  test("shares and embeds the video", async ({ page, data }) => {
    await page.goto(`/record/${data.video.id}`);
    await expect(
      page.getByRole("heading", { name: "Share", exact: false })
    ).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Shareable link" })
    ).toHaveValue(page.url());
    // The embed code points to the video by its report number
    const report = data.video.metadata.report_number[0];
    await expect
      .poll(() =>
        page
          .locator("textarea, input")
          .evaluateAll((fields) => fields.map((field) => field.value))
      )
      .toContainEqual(expect.stringContaining(`/video/${report}`));
    // Starting at a given time adds it to the link
    await page.getByRole("checkbox", { name: "Start at:" }).check();
    const start = page.getByRole("textbox", { name: "0:00" });
    await start.fill("0:10");
    await start.press("Tab");
    await expect(
      page.getByRole("textbox", { name: "Shareable link" })
    ).toHaveValue(`${page.url()}?t=10`);
  });

  test("lists the files to download", async ({ page, data }) => {
    await page.goto(`/record/${data.video.id}`);
    await expect(
      page.getByRole("heading", { name: "Download", exact: false })
    ).toBeVisible();
    const download = page.getByRole("link", { name: "Download", exact: true });
    await expect(download.first()).toHaveAttribute("href", /\/api\/files\//);
    // Other formats open on click
    await page.getByText("Other video formats").click();
    await expect(
      page.getByRole("link", { name: "Download", exact: true })
    ).not.toHaveCount(1);
  });

  test("shows the transcript of the subtitles", async ({ page, data }) => {
    const subtitled = data.videos.find((hit) =>
      (hit.metadata._files || []).some(
        (file) => file.context_type === "subtitle"
      )
    );
    test.skip(!subtitled, "no video with subtitles");
    await page.goto(`/record/${subtitled.id}`);
    await page.getByRole("button", { name: "Show Transcriptions" }).click();
    await expect(
      page.getByRole("heading", { name: "In this video" })
    ).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Search transcript..." })
    ).toBeVisible();
    // The cues are read from the subtitle file, which the browser can only
    // fetch from the origin of the page
    const subtitle = subtitled.metadata._files.find(
      (file) => file.context_type === "subtitle"
    );
    const origin = new URL(page.url()).origin;
    if (new URL(subtitle.links.self).origin === origin) {
      await expect(page.getByText(/\d+:\d\d - \d+:\d\d/).first()).toBeVisible();
    }
  });
});

test.describe("project page", () => {
  test("lists the videos of the project", async ({ page, data }) => {
    const { metadata } = data.project;
    await page.goto(`/record/${data.project.id}`);
    await expect(recordTitle(page, metadata.title.title)).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Videos", exact: true })
    ).toBeVisible();
    for (const video of metadata.videos) {
      await expect(
        page
          .getByRole("link", { name: video.title.title })
          .and(page.locator(`[href="/record/${video.recid}"]`))
          .first()
      ).toBeVisible();
    }
  });
});

test.describe("record exports", () => {
  test("exports the video as JSON", async ({ page, data }) => {
    await page.goto(`/record/${data.video.id}/export/json`);
    await expect(page.locator("pre").first()).toContainText(
      new RegExp(`"recid":\\s*${data.video.id}\\b`)
    );
  });
});

test.describe("errors", () => {
  test("shows a not found page", async ({ page }) => {
    const response = await page.goto("/record/999999999");
    expect(response.status()).toBe(404);
    await expect(page.getByText("Page not found.")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Back to safety" })
    ).toBeVisible();
  });
});
