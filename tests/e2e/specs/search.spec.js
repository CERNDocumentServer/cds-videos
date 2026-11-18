const {
  test,
  expect,
  getJSON,
  hitsTotal,
  selectSort,
  sortControl,
  recordTitle,
  facetValue,
  searchParams,
} = require("../support");

test.describe("search page", () => {
  test("lists the published videos", async ({ page, ui, data }) => {
    await page.goto("/search");
    await expect(
      page.getByText(new RegExp(`Found ${data.total} results?`))
    ).toBeVisible();
    // The first page of results, newest first without a query
    const expected = Math.min(data.total, 21);
    await expect(page.locator("a[href^='/record/']")).toHaveCount(expected);
    await expect(sortControl(page, ui)).toContainText("Newest");
  });

  test("shows the facets of the results", async ({ page, data }) => {
    await page.goto("/search");
    for (const name of ["category", "type", "language"]) {
      await expect(
        page.getByRole("heading", { name, exact: true })
      ).toBeVisible();
    }
    const bucket = data.aggregations.category.buckets[0];
    await expect(facetValue(page, bucket.key)).toContainText(
      String(bucket.doc_count)
    );
  });

  test("filters the results with a facet", async ({ page, data, request }) => {
    const bucket = data.aggregations.category.buckets[0];
    await page.goto("/search");
    await facetValue(page, bucket.key).click();
    await expect(page).toHaveURL(/category=/);
    expect(searchParams(page).get("category")).toBe(bucket.key);
    await expect(
      page.getByText(new RegExp(`Found ${bucket.doc_count} results?`))
    ).toBeVisible();
    // Same results as the API
    const api = await getJSON(
      request,
      `/api/records/?category=${encodeURIComponent(bucket.key)}&size=21`
    );
    const titles = api.hits.hits.map((hit) => hit.metadata.title.title);
    for (const title of titles) {
      await expect(page.getByRole("link", { name: title })).toBeVisible();
    }
  });

  test("searches with a query", async ({ page, data, request }) => {
    const query = data.video.metadata.title.title.split(/\s+/).pop();
    await page.goto(`/search?q=${encodeURIComponent(query)}`);
    const api = await getJSON(
      request,
      `/api/records/?q=${encodeURIComponent(query)}`
    );
    await expect(
      page.getByText(new RegExp(`Found ${hitsTotal(api.hits)} results?`))
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: data.video.metadata.title.title })
    ).toBeVisible();
  });

  test("shows that nothing matches a query", async ({ page, request }) => {
    // One word: the words of a query are ORed, so "no-such-video" would
    // find the videos
    const query = "zzzznosuchvideozzzz";
    const api = await getJSON(request, `/api/records/?q=${query}`);
    expect(hitsTotal(api.hits)).toBe(0);
    await page.goto(`/search?q=${query}`);
    await expect(page.getByText(/no results/i).first()).toBeVisible();
    await expect(page.locator("a[href^='/record/']")).toHaveCount(0);
  });

  test("sorts the results by title", async ({ page, ui, request }) => {
    await page.goto("/search");
    await selectSort(page, ui, "Title [Asc]");
    await expect(page).toHaveURL(/sort=title_asc/);
    const api = await getJSON(request, "/api/records/?sort=title_asc&size=21");
    const expected = api.hits.hits.map((hit) => hit.metadata.title.title);
    await expect(page.locator("a[href^='/record/'] p")).toHaveText(expected);
  });

  test("opens a result", async ({ page, data }) => {
    await page.goto("/search");
    const title = data.video.metadata.title.title;
    await page.getByRole("link", { name: title }).click();
    await expect(page).toHaveURL(new RegExp(`/record/${data.video.id}$`));
    await expect(recordTitle(page, title)).toBeVisible();
  });

  test("keeps the search in the URL", async ({ page, ui, data }) => {
    const bucket = data.aggregations.category.buckets[0];
    await page.goto(
      `/search?q=&category=${encodeURIComponent(bucket.key)}&sort=oldest`
    );
    await expect(
      page.getByText(new RegExp(`Found ${bucket.doc_count} results?`))
    ).toBeVisible();
    await expect(sortControl(page, ui)).toContainText("Oldest");
  });
});
