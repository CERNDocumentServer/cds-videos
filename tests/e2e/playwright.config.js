// End to end tests of CDS Videos.
//
// The same specs run against both interfaces of a local instance (see
// README.md): the AngularJS one ("angularjs" project) and the React one
// ("react" project). Both read the same database, so a test that passes on
// the first and fails on the second is a regression of the React interface.

const { defineConfig, devices } = require("@playwright/test");

const env = process.env;

module.exports = defineConfig({
  testDir: "./specs",
  timeout: 60 * 1000,
  expect: { timeout: 10 * 1000 },
  // The deposit specs create projects: keep the runs predictable
  fullyParallel: false,
  workers: Number(env.E2E_WORKERS || 2),
  retries: env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 },
    // Local instances use a self signed certificate
    ignoreHTTPSErrors: true,
    // "chrome" uses the installed Google Chrome instead of the Playwright one
    channel: env.E2E_CHANNEL || undefined,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "angularjs",
      use: { baseURL: env.E2E_ANGULARJS_URL || "https://127.0.0.1:5000" },
    },
    {
      name: "react",
      use: { baseURL: env.E2E_REACT_URL || "https://127.0.0.1:5001" },
    },
  ],
});
