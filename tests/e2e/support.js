// Fixtures and helpers shared by the specs.
//
// The specs describe what a user sees and does, with role and text locators
// that both interfaces share. The few controls that differ (the sort menu,
// the strap selects of the deposit form) go through the helpers below, keyed
// by the project name ("angularjs" or "react").

const base = require("@playwright/test");

const { expect } = base;
const env = process.env;

// The users of ``scripts/setup``
const USERS = {
  user: {
    email: env.E2E_USER_EMAIL || "test@test.ch",
    password: env.E2E_USER_PASSWORD || "123456",
  },
  admin: {
    email: env.E2E_ADMIN_EMAIL || "admin@test.ch",
    password: env.E2E_ADMIN_PASSWORD || "123456",
  },
};

const JSON_HEADERS = { Accept: "application/json" };

async function login(page, user) {
  await page.goto("/login/?next=/");
  await page.locator("input[name=email]").fill(user.email);
  await page.locator("input[name=password]").fill(user.password);
  await page.locator("button[type=submit]").click();
  await expect(userMenu(page, user)).toBeVisible();
}

function userMenu(page, user) {
  return page.getByRole("banner").getByRole("button", { name: user.email });
}

async function getJSON(request, url) {
  const response = await request.get(url, { headers: JSON_HEADERS });
  expect(response.ok(), `GET ${url}`).toBeTruthy();
  return response.json();
}

// Deletes a deposit with its videos through the REST API, if it exists
async function deleteDeposit(page, url) {
  const found = await page.request.get(url, { headers: JSON_HEADERS });
  if (!found.ok()) {
    return;
  }
  const { origin } = new URL(url, base.test.info().project.use.baseURL);
  const cookies = await page.context().cookies(origin);
  const csrf = cookies.find((cookie) => cookie.name === "csrftoken");
  const response = await page.request.delete(url, {
    headers: {
      ...JSON_HEADERS,
      "X-CSRFToken": csrf ? csrf.value : "",
      // The REST API checks the referer of secure requests
      Referer: `${origin}/`,
    },
  });
  expect([204, 404, 410], `DELETE ${url}`).toContain(response.status());
}

function hitsTotal(hits) {
  return typeof hits.total === "object" ? hits.total.value : hits.total;
}

// Published records to test with, read from the REST API as an admin
async function loadData(browser, baseURL) {
  const context = await browser.newContext({
    baseURL,
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  await login(page, USERS.admin);
  const search = await getJSON(context.request, "/api/records/?size=100");
  const videos = search.hits.hits;
  if (videos.length === 0) {
    throw new Error("The tests need at least one published video");
  }
  // A video with the metadata the record page shows
  const video =
    videos.find(
      (hit) =>
        hit.metadata.description &&
        (hit.metadata.keywords || []).length > 0 &&
        hit.metadata._project_id
    ) || videos[0];
  const deposit = await getJSON(
    context.request,
    `/api/deposits/project/${video.metadata._project_id}`
  );
  const project = await getJSON(
    context.request,
    `/api/record/${deposit.metadata._deposit.pid.value}`
  );
  await context.close();
  return {
    total: hitsTotal(search.hits),
    aggregations: search.aggregations,
    videos,
    video,
    project,
  };
}

const test = base.test.extend({
  // "angularjs" or "react"
  ui: async ({}, use, testInfo) => {
    await use(testInfo.project.name);
  },
  users: async ({}, use) => {
    await use(USERS);
  },
  data: [
    async ({ browser }, use, workerInfo) => {
      await use(await loadData(browser, workerInfo.project.use.baseURL));
    },
    { scope: "worker" },
  ],
  // Fails the test on uncaught errors of the page
  page: async ({ page }, use) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error));
    await use(page);
    // The messages, the errors themselves print as ``[Object]``
    expect(errors.map(String), "uncaught errors in the page").toEqual([]);
  },
});

// The sort menu: a Bootstrap dropdown button or a Semantic UI dropdown
function sortControl(page, ui) {
  return ui === "angularjs"
    ? page.getByRole("button", { name: /^Sort:/ })
    : page.getByRole("listbox").filter({ hasText: /^Sort:/ });
}

async function selectSort(page, ui, label) {
  await sortControl(page, ui).click();
  if (ui === "angularjs") {
    await page
      .locator(".dropdown-menu:visible")
      .getByText(label, { exact: true })
      .click();
  } else {
    await page.getByRole("option", { name: label, exact: true }).click();
  }
}

// The category and type selects of the deposit form (index 0 and 1)
async function strapSelect(page, ui, index, label) {
  if (ui === "angularjs") {
    await page
      .locator(".cds-deposit-strap-select button:visible")
      .nth(index)
      .click();
    await page
      .locator("ul.dropdown-menu:visible a")
      .filter({ hasText: label })
      .first()
      .click();
  } else {
    const dropdown = page
      .locator(".cds-deposit-strap-select .ui.dropdown:visible")
      .nth(index);
    await dropdown.click();
    await dropdown.getByRole("option", { name: label }).first().click();
  }
}

// The title of a record page
function recordTitle(page, title) {
  return page.getByRole("heading", { level: 1, name: title, exact: true });
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// A facet value with its count, like "ATLAS 2"
function facetValue(page, label) {
  const text = new RegExp(`^\\s*${escapeRegExp(label)}\\s*\\d+\\s*$`);
  return page.getByRole("listitem").filter({ hasText: text }).first();
}

function searchParams(page) {
  return new URL(page.url()).searchParams;
}

module.exports = {
  test,
  expect,
  login,
  userMenu,
  getJSON,
  deleteDeposit,
  hitsTotal,
  selectSort,
  sortControl,
  strapSelect,
  recordTitle,
  facetValue,
  escapeRegExp,
  searchParams,
  JSON_HEADERS,
};
