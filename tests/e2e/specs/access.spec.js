// Who can see the records and who can edit the deposits.
//
// The restricted project of ``seed.py`` and its video are readable by the
// e-group ``e2e-readers@cern.ch`` (the reader user), editable by the test
// user (their owner) and by the admins. The other user can upload, but has
// no access to them.

const {
  test,
  expect,
  READERS,
  login,
  getJSON,
  recordTitle,
  strapOptions,
  JSON_HEADERS,
} = require("../support");

// The drafts of seed.py: the tests change the restrictions and editors of
// the first one, the second one is in a category the other user cannot read
const ACCESS_DRAFT = "Access settings draft";
const SHARED_DRAFT = "Draft shared with the other user";

// A project of the uploads of the logged in user
async function findDraft(request, title) {
  const api = await getJSON(request, "/api/deposits/project/?size=100");
  return api.hits.hits.find(
    (hit) => hit.metadata.title && hit.metadata.title.title === title
  );
}

// The categories that the logged in user can read, which are records
// restricted to e-groups (all but OPEN in the fixtures)
async function categoryNames(request) {
  const api = await getJSON(request, "/api/categories/?size=100");
  return api.hits.hits.map((hit) => hit.metadata.name).sort();
}

async function status(request, url) {
  const response = await request.get(url, { headers: JSON_HEADERS });
  return response.status();
}

// The ids of the published records found by a query
async function searchIds(request, query) {
  const api = await getJSON(
    request,
    `/api/records/?q=${encodeURIComponent(query)}&size=100`
  );
  return api.hits.hits.map((hit) => String(hit.id));
}

async function expectRefused(page, url) {
  const response = await page.goto(url);
  expect(response.status(), url).toBe(403);
  await expect(page.getByText("Permission required").first()).toBeVisible();
}

async function expectLogin(page, url) {
  await page.goto(url);
  await expect(page).toHaveURL(/\/login\/?\?next=/);
  await expect(page.locator("input[name=email]")).toBeVisible();
}

function uploadLink(page) {
  return page
    .getByRole("banner")
    .getByRole("link", { name: "Upload", exact: true });
}

test.describe("restricted record", () => {
  let video;
  let project;
  let depositId;
  let phrase;

  test.beforeEach(async ({ data }) => {
    test.skip(!data.restricted, "no restricted record (see seed.py)");
    ({ video, project } = data.restricted);
    depositId = video.metadata._project_id;
    phrase = `"${video.metadata.title.title}"`;
  });

  test("is hidden from anonymous users", async ({ page, request }) => {
    expect(await status(request, `/api/record/${video.id}`)).toBe(401);
    expect(await status(request, `/api/record/${project.id}`)).toBe(401);
    expect(await searchIds(request, phrase)).not.toContain(String(video.id));
    await expectLogin(page, `/record/${video.id}`);
    await expectLogin(page, `/record/${project.id}`);
    await page.goto(`/search?q=${encodeURIComponent(phrase)}`);
    await expect(page.getByText(/no results/i).first()).toBeVisible();
  });

  test("is refused to the users without access", async ({ page, users }) => {
    await login(page, users.other);
    const { request } = page;
    expect(await status(request, `/api/record/${video.id}`)).toBe(403);
    expect(await searchIds(request, phrase)).not.toContain(String(video.id));
    await expectRefused(page, `/record/${video.id}`);
    await expectRefused(page, `/record/${project.id}`);
    // Nor can they edit it, although they can upload
    expect(await status(request, `/api/deposits/project/${depositId}`)).toBe(
      403
    );
    await expectRefused(page, `/deposit/project/${depositId}`);
    const uploads = await getJSON(request, "/api/deposits/project/?size=100");
    expect(uploads.hits.hits.map((hit) => hit.id)).not.toContain(depositId);
  });

  test("is shown to the members of its e-group", async ({ page, users }) => {
    await login(page, users.reader);
    const { request } = page;
    expect(await status(request, `/api/record/${video.id}`)).toBe(200);
    expect(await searchIds(request, phrase)).toContain(String(video.id));
    await page.goto(`/record/${video.id}`);
    await expect(recordTitle(page, video.metadata.title.title)).toBeVisible();
    await page.goto(`/record/${project.id}`);
    await expect(recordTitle(page, project.metadata.title.title)).toBeVisible();
    await page.goto(`/search?q=${encodeURIComponent(phrase)}`);
    await expect(
      page.locator(`a[href='/record/${video.id}']`).first()
    ).toBeVisible();
    // Reading is not editing
    await expectRefused(page, `/deposit/project/${depositId}`);
  });

  test("is labelled restricted for the members of its e-group", async ({
    page,
    ui,
    users,
  }) => {
    test.skip(ui === "angularjs", "fixed on the React branch only");
    await login(page, users.reader);
    // They know that the record is restricted, not who can read or edit it
    const api = await getJSON(page.request, `/api/record/${video.id}`);
    expect(api.metadata._access).toEqual({ status: "restricted" });
    await page.goto(`/record/${video.id}`);
    await expect(recordTitle(page, video.metadata.title.title)).toBeVisible();
    await expect(
      page.getByText("Restricted", { exact: true }).first()
    ).toBeVisible();
  });

  for (const role of ["user", "admin"]) {
    test(`is labelled restricted for the ${role === "user" ? "owner" : "admins"}`, async ({
      page,
      users,
      data,
    }) => {
      await login(page, users[role]);
      await page.goto(`/record/${video.id}`);
      await expect(recordTitle(page, video.metadata.title.title)).toBeVisible();
      await expect(
        page.getByText("Restricted", { exact: true }).first()
      ).toBeVisible();
      // and the public video as public
      await page.goto(`/record/${data.video.id}`);
      await expect(
        page.getByText("Public", { exact: true }).first()
      ).toBeVisible();
      // They can edit it
      const response = await page.goto(`/deposit/project/${depositId}`);
      expect(response.status()).toBe(200);
    });
  }
});

test.describe("uploads", () => {
  test("need a login", async ({ page }) => {
    await page.goto("/");
    await expect(uploadLink(page)).toHaveCount(0);
    await expectLogin(page, "/deposit");
    await expectLogin(page, "/deposit/new");
  });

  test("need the upload permission", async ({ page, users }) => {
    await login(page, users.reader);
    await page.goto("/");
    await expect(uploadLink(page)).toHaveCount(0);
    await expectRefused(page, "/deposit");
    await expectRefused(page, "/deposit/new");
  });

  test("are open to the users who can upload", async ({ page, users }) => {
    await login(page, users.other);
    await page.goto("/");
    await expect(uploadLink(page)).toBeVisible();
    const response = await page.goto("/deposit");
    expect(response.status()).toBe(200);
  });
});

test.describe("restrictions and editors of a project", () => {
  // The project panel of the deposit form
  function restrictions(page) {
    return page
      .getByRole("heading", { name: "Project restrictions when published" })
      .locator("xpath=..");
  }

  function editors(page) {
    return page
      .getByRole("heading", {
        name: "Grant edit access to the project and the videos",
      })
      .locator("xpath=..");
  }

  async function addEmail(box, email) {
    await box.locator(".cds-async-select input.search").fill(email);
    await box.getByRole("option", { name: email, exact: true }).click();
    await expect(
      box.locator(".ui.label").filter({ hasText: email })
    ).toBeVisible();
  }

  async function save(page) {
    const button = page.getByRole("button", {
      name: "Save Project and Videos",
    });
    await expect(button).toBeEnabled();
    await button.click();
  }

  test("are saved from the deposit form", async ({
    page,
    ui,
    users,
    browser,
  }) => {
    test.skip(
      ui === "angularjs",
      "the ui-select controls of AngularJS have no helper"
    );
    test.setTimeout(2 * 60 * 1000);
    await login(page, users.user);
    const draft = await findDraft(page.request, ACCESS_DRAFT);
    test.skip(!draft, `no "${ACCESS_DRAFT}" project (see seed.py)`);
    const { id } = draft;
    const access = async () =>
      (await getJSON(page.request, `/api/deposits/project/${id}`)).metadata
        ._access || {};

    // The other user, in a context of their own
    const { baseURL } = test.info().project.use;
    const context = await browser.newContext({
      baseURL,
      ignoreHTTPSErrors: true,
    });
    const other = await context.newPage();
    await login(other, users.other);
    const otherStatus = async () =>
      (await other.goto(`/deposit/project/${id}`)).status();

    // No LDAP in the tests: the suggestions are the typed e-mail only
    await page.route("**/api/ldap/**", (route) => route.fulfill({ json: [] }));
    await page.goto(`/deposit/project/${id}`);
    await page.getByRole("button", { name: "Show details" }).first().click();

    await test.step("restrict the project to an e-group", async () => {
      const box = restrictions(page);
      const select = box.locator("select");
      // Public first, so that choosing restricted is a change, whatever a
      // previous run left
      await select.selectOption("public");
      await select.selectOption("restricted");
      await expect(
        box.getByText("Choose who can access the published project")
      ).toBeVisible();
      await addEmail(box, READERS);
    });

    await test.step("grant edit access to the other user", async () => {
      await page.getByRole("tab", { name: "Project editors" }).click();
      await addEmail(editors(page), users.other.email);
    });

    await test.step("save", async () => {
      expect(await otherStatus()).toBe(403);
      await save(page);
      await expect.poll(access, { timeout: 20 * 1000 }).toEqual(
        expect.objectContaining({
          read: expect.arrayContaining([READERS]),
          update: expect.arrayContaining([users.user.email, users.other.email]),
        })
      );
      // The other user can now edit the project
      expect(await otherStatus()).toBe(200);
    });

    await test.step("make it public again", async () => {
      await page.getByRole("tab", { name: "Basic Info" }).first().click();
      // The editors are reset to the owner and the category's responsibles
      await restrictions(page).locator("select").selectOption("public");
      await save(page);
      await expect
        .poll(
          async () => {
            const { read, update } = await access();
            return [
              (read || []).length,
              (update || []).includes(users.other.email),
            ];
          },
          { timeout: 20 * 1000 }
        )
        .toEqual([0, false]);
      expect(await otherStatus()).toBe(403);
    });
    await context.close();
  });
});

test.describe("categories of a project", () => {
  for (const role of ["user", "admin"]) {
    test(`are the ones the ${role} can read`, async ({ page, ui, users }) => {
      await login(page, users[role]);
      const names = await categoryNames(page.request);
      expect(names.includes("CERN")).toBe(role === "admin");
      // A draft of the user, which the admins can edit too
      const draft = await findDraft(page.request, ACCESS_DRAFT);
      test.skip(!draft, `no "${ACCESS_DRAFT}" project (see seed.py)`);
      await page.goto(`/deposit/project/${draft.id}`);
      expect((await strapOptions(page, ui, 0)).sort()).toEqual(names);
    });
  }

  test("cannot be read by the editors outside of their e-groups", async ({
    page,
    users,
  }) => {
    await login(page, users.other);
    expect(await categoryNames(page.request)).not.toContain("CERN");
    const draft = await findDraft(page.request, SHARED_DRAFT);
    test.skip(!draft, `no "${SHARED_DRAFT}" project (see seed.py)`);
    expect(draft.metadata.category).toBe("CERN");
    const response = await page.goto(`/deposit/project/${draft.id}`);
    expect(response.status()).toBe(200);
    await page.getByRole("button", { name: "Show details" }).first().click();
    // They edit the project, but without the access rules of its category
    // they cannot change its restrictions
    await expect(
      page.locator("input[name=title]:visible").first()
    ).toBeEnabled();
    await expect(
      page
        .getByRole("heading", { name: "Project restrictions when published" })
        .locator("xpath=..")
        .locator("select")
    ).toBeDisabled();
  });
});
