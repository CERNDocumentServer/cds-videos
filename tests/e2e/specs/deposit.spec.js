const path = require("path");

const { test, expect, login, getJSON, strapSelect } = require("../support");

const CLIP = path.join(__dirname, "..", "data", "clip.mp4");

function projectTitle(hit) {
  return (hit.metadata.title && hit.metadata.title.title) || "No project title";
}

test.describe("uploads of a user", () => {
  test.beforeEach(async ({ page, users }) => {
    await login(page, users.user);
  });

  test("lists the projects of the user", async ({ page }) => {
    await page.goto("/deposit");
    await expect(
      page.getByRole("textbox", { name: "Search uploads..." })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "New Upload" })
    ).toHaveAttribute("href", "/deposit/new?type=project");
    for (const name of ["category", "project status"]) {
      await expect(
        page.getByRole("heading", { name, exact: true })
      ).toBeVisible();
    }
    // Newest first, as the API returns them
    const api = await getJSON(page.request, "/api/deposits/project/?size=5");
    const projects = page.locator("a[href^='/deposit/project/']");
    await expect(projects.first()).toHaveAttribute(
      "href",
      `/deposit/project/${api.hits.hits[0].id}`
    );
    await expect(projects.first()).toHaveText(projectTitle(api.hits.hits[0]));
  });

  test("searches the projects", async ({ page }) => {
    const api = await getJSON(page.request, "/api/deposits/project/?size=50");
    const titled = api.hits.hits.find((hit) => hit.metadata.title);
    test.skip(!titled, "no project with a title");
    const title = titled.metadata.title.title;
    await page.goto("/deposit");
    const box = page.getByRole("textbox", { name: "Search uploads..." });
    await box.fill(`"${title}"`);
    await box.press("Enter");
    await expect(page).toHaveURL(/[?&]q=/);
    await expect(
      page.locator(`a[href='/deposit/project/${titled.id}']`)
    ).toBeVisible();
  });

  test("shows the upload page", async ({ page }) => {
    await page.goto("/deposit/new");
    await expect(
      page.getByRole("heading", {
        name: "Click here to select videos to upload",
      })
    ).toBeVisible();
    await expect(page.getByText("Supported video formats are")).toBeVisible();
    await expect(page.locator("input[type=file]").first()).toBeAttached();
  });

  test("opens the form of a project", async ({ page }) => {
    const api = await getJSON(page.request, "/api/deposits/project/?size=50");
    const titled = api.hits.hits.find((hit) => hit.metadata.title);
    test.skip(!titled, "no project with a title");
    await page.goto(`/deposit/project/${titled.id}`);
    await expect(page.locator("input[name=title]").first()).toHaveValue(
      titled.metadata.title.title
    );
    await expect(
      page.getByRole("button", { name: "Save Project and Videos" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Publish Project and Videos" })
    ).toBeVisible();
    // The description editors load (in collapsed panels too)
    await expect(
      page
        .getByRole("application", {
          name: /Rich Text Editor/,
          includeHidden: true,
        })
        .first()
    ).toBeAttached();
    // One panel per video
    const videos = (titled.metadata.videos || []).length;
    if (videos > 0) {
      await expect(page.getByText(/Video #1 \(of \d+\)/)).toBeVisible();
    }
  });
});

test.describe("new upload", () => {
  // Creates a project, saves it and deletes it
  test("uploads a video, edits, saves and deletes the project", async ({
    page,
    users,
    ui,
  }) => {
    test.setTimeout(3 * 60 * 1000);
    await login(page, users.admin);
    let id;
    await test.step("upload a video", async () => {
      await page.goto("/deposit/new");
      // The upload ends with the start of the video workflow
      const started = page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          /\/api\/flows\/$/.test(response.url())
      );
      await page.locator("input[type=file]").first().setInputFiles(CLIP);
      await expect(page).toHaveURL(/\/deposit\/project\/[0-9a-f]{32}/, {
        timeout: 30 * 1000,
      });
      id = page.url().split("/").pop();
      await expect(page.getByText(/Video #1/)).toBeVisible();
      await started;
    });

    await test.step("choose the category and the type", async () => {
      const saved = async () => {
        const project = await getJSON(
          page.request,
          `/api/deposits/project/${id}`
        );
        return [project.metadata.category, project.metadata.type];
      };
      // Each choice saves the project: wait for the first save, as two
      // overlapping saves can lose the type (in both interfaces)
      await strapSelect(page, ui, 0, "CERN");
      await expect
        .poll(saved, { timeout: 20 * 1000 })
        .toEqual(["CERN", undefined]);
      await strapSelect(page, ui, 1, "FOOTAGE");
      await expect
        .poll(saved, { timeout: 20 * 1000 })
        .toEqual(["CERN", "FOOTAGE"]);
    });

    await test.step("save the project title", async () => {
      // The details of the project are collapsed after an upload
      await page.getByRole("button", { name: "Show details" }).first().click();
      const title = `E2E ${ui} project ${Date.now()}`;
      const save = page.getByRole("button", {
        name: "Save Project and Videos",
      });
      // The form reloads the project after the upload, which can reset the
      // edits made meanwhile (in both interfaces)
      await expect(async () => {
        await page.locator("input[name=title]:visible").first().fill(title);
        await expect(save).toBeEnabled({ timeout: 2000 });
      }).toPass({ timeout: 30 * 1000 });
      await save.click();
      await expect
        .poll(
          async () => {
            const project = await getJSON(
              page.request,
              `/api/deposits/project/${id}`
            );
            return project.metadata.title && project.metadata.title.title;
          },
          { timeout: 20 * 1000 }
        )
        .toBe(title);
    });

    await test.step("delete the project", async () => {
      await page.getByRole("tab", { name: "Admin" }).first().click();
      await page.getByRole("button", { name: "Delete Project" }).click();
      await expect(page.getByText("Successfully deleted.")).toBeVisible({
        timeout: 30 * 1000,
      });
      const response = await page.request.get(`/api/deposits/project/${id}`, {
        headers: { Accept: "application/json" },
      });
      expect([404, 410]).toContain(response.status());
    });
  });
});
