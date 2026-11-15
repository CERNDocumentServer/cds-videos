# End to end tests

Playwright tests of the user facing pages of CDS Videos: home page, search,
video and project pages, exports, login, the uploads list and the upload form.

The same specs run against two interfaces of one local instance:

| Project     | Interface                     | Default URL              |
| ----------- | ----------------------------- | ------------------------ |
| `angularjs` | AngularJS (the `main` branch) | `https://127.0.0.1:5000` |
| `react`     | React and Semantic UI         | `https://127.0.0.1:5001` |

Both read the same database, so a test that passes on `angularjs` and fails on
`react` points to a regression of the React interface. `compare-ui.sh` starts
both servers on these ports. With a single server, run one project only.

## Running

```bash
cd tests/e2e
npm install
npx playwright install chromium   # or E2E_CHANNEL=chrome to use Google Chrome
npm test                          # both interfaces
npm run test:react                # one interface
npx playwright test specs/search.spec.js --project=react --headed
npm run report                    # HTML report of the last run
```

The instance needs the users of `scripts/setup` and at least one published
project with a video (ideally with a description, keywords and subtitles). The
specs read the records to check from the REST API, so they work with any
data, and skip the checks the data does not allow.

## Settings

| Variable                                | Default                   |
| --------------------------------------- | ------------------------- |
| `E2E_ANGULARJS_URL`                     | `https://127.0.0.1:5000`  |
| `E2E_REACT_URL`                         | `https://127.0.0.1:5001`  |
| `E2E_USER_EMAIL`, `E2E_USER_PASSWORD`   | `test@test.ch`, `123456`  |
| `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD` | `admin@test.ch`, `123456` |
| `E2E_CHANNEL`                           | Playwright's Chromium     |
| `E2E_WORKERS`                           | `2`                       |

## Writing tests

- Locate elements as a user finds them (`getByRole`, `getByText`, labels),
  which both interfaces share. The few controls that differ, like the sort
  menu and the category and type selects, have helpers in `support.js`.
- Compare what the page shows with the REST API (`getJSON`) instead of
  hard coding records.
- Uncaught page errors fail the test.
- `specs/deposit.spec.js` uploads `data/clip.mp4` (a 2 second test clip) as
  the admin user, then deletes the project it created.
