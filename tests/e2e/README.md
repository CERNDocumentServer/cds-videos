# End to end tests

Playwright tests of the user facing pages of CDS Videos: home page, search,
video and project pages, exports, login, the uploads list and the upload form,
and who can see the records and edit the deposits.

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

`setup.sh` prepares such an instance on empty services: the database, the
indices, the users and fixtures of `scripts/setup` (without the keywords
harvested from home.cern), the users of the access tests and the records of
`seed.py`, all with the files of processed videos:

- a published project with two videos and a draft project with one,
- a published project with a video, both restricted to the e-group
  `e2e-readers@cern.ch` (a role of the reader user),
- a draft project with a video, "Access settings draft", in the OPEN
  category, whose restrictions and editors `specs/access.spec.js` changes and
  resets,
- a draft project with a video in the CERN category, shared with the other
  user. The categories are records readable by their e-groups only (all but
  OPEN in the fixtures), so the other user can edit it but not change its
  restrictions.

`specs/access.spec.js` skips its tests when these records are missing.

```bash
./tests/e2e/setup.sh    # from the root of the repository, in the virtualenv
```

## Continuous integration

The `tests-e2e` job of `.github/workflows/tests.yml` builds the assets, starts
PostgreSQL, OpenSearch and Redis with `docker-services-cli`, runs `setup.sh`,
starts the server on `https://127.0.0.1:5001` and runs the `react` project,
once per LTS line of Node.js (24 and 26). There is no Celery worker, so the
tasks of new uploads stay in the queue. On failure the job uploads the HTML
report, the traces and the server log as the `playwright-report-node-<version>`
artifact. The tests need Node.js 24 or later.

## Settings

| Variable                                  | Default                    |
| ----------------------------------------- | -------------------------- |
| `E2E_ANGULARJS_URL`                       | `https://127.0.0.1:5000`   |
| `E2E_REACT_URL`                           | `https://127.0.0.1:5001`   |
| `E2E_USER_EMAIL`, `E2E_USER_PASSWORD`     | `test@test.ch`, `123456`   |
| `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD`   | `admin@test.ch`, `123456`  |
| `E2E_READER_EMAIL`, `E2E_READER_PASSWORD` | `reader@test.ch`, `123456` |
| `E2E_OTHER_EMAIL`, `E2E_OTHER_PASSWORD`   | `other@test.ch`, `123456`  |
| `E2E_READERS_EGROUP`                      | `e2e-readers@cern.ch`      |
| `E2E_CHANNEL`                             | Playwright's Chromium      |
| `E2E_WORKERS`                             | `2`                        |

## Writing tests

- Locate elements as a user finds them (`getByRole`, `getByText`, labels),
  which both interfaces share. The few controls that differ, like the sort
  menu and the category and type selects, have helpers in `support.js`.
- Compare what the page shows with the REST API (`getJSON`) instead of
  hard coding records.
- Uncaught page errors fail the test.
- `specs/deposit.spec.js` uploads `data/clip.mp4` (a 2 second test clip) as
  the admin user, then deletes the project it created, also when the test
  fails midway.
- `specs/access.spec.js` uses four users: the owner of the records (`user`),
  an admin, a member of the e-group of the restricted record without the
  upload permission (`reader`), and a user who can upload but has no access
  to the records of the others (`other`). The form test runs on `react` only.
