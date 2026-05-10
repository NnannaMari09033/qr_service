# Contributing to QR Service

Thanks for wanting to help. This guide explains how to set up the project on your computer, how to make a change, and how to submit it. If you have never contributed to an open source project before, this guide is written for you.

## What this project is

QR Service is a Django web app. People use it to make QR codes, paste those codes on flyers or banners, and then track how many times each one is scanned. The goal is to help event planners and marketers see which placements work and which do not.

## What you need installed

Before you start, make sure these are installed on your computer:

* Python 3.12 or newer
* PostgreSQL (the database)
* Git
* A text editor or IDE (VS Code, PyCharm, anything you like)

## Step 1: Get the code on your computer

First, fork the repository on GitHub. A fork is your own personal copy. To fork, click the "Fork" button on the GitHub page.

Then clone your fork to your computer. Replace `YOUR_USERNAME` with your GitHub username:

```bash
git clone https://github.com/YOUR_USERNAME/qr_service.git
cd qr_service
```

## Step 2: Set up a Python environment

A virtual environment keeps this project's Python packages separate from other projects on your computer.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If you ever close your terminal and come back later, run `source venv/bin/activate` again before working.

## Step 3: Set up the database and config

Copy the example config file and fill it with your own values:

```bash
cp .env.example .env
```

Open `.env` in your editor. Replace the placeholder values with real ones. To generate a secret key, run:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Create the database and apply the schema:

```bash
createdb qr_service
python manage.py migrate
python manage.py createsuperuser
```

The `createsuperuser` command will ask for a username, email, and password. Pick anything you can remember. This is only on your computer.

## Step 4: Start the app

```bash
python manage.py runserver
```

Open `http://localhost:8000` in your browser. You should see the landing page. If you do, the setup worked.

## Running the tests

Before you change anything, run the existing tests to make sure your setup is correct:

```bash
python manage.py test
```

The first run takes about a minute because Django creates a test database. Every test should pass. If they do not, your setup has a problem. Open an issue and someone will help.

For faster test runs while you are coding, use:

```bash
python manage.py test --keepdb --parallel auto
```

`--keepdb` reuses the test database. `--parallel auto` runs tests across all your CPU cores.

## Making your first change

These are the steps to make a change and submit it.

### 1. Find or file an issue

Go to the Issues tab on GitHub. Look for an issue you want to work on. Issues with the label `good first issue` are picked specifically to be easy starting points.

If you have a new idea or found a bug that has no issue, open one first. Describe what is wrong or what you want to add. Wait for a maintainer to confirm it is a good fit. This avoids you spending hours on a change that gets rejected.

### 2. Claim the issue

Leave a comment on the issue saying you want to work on it. For example: "I would like to take this." This stops two people from working on the same thing at the same time.

### 3. Create a branch

Branches let you work on a change without touching the main code. Branch names should describe what you are doing.

```bash
git checkout -b fix/dashboard-mobile-layout
```

Common branch name prefixes:

* `fix/` for bug fixes
* `feat/` for new features
* `docs/` for documentation changes
* `test/` for adding tests

### 4. Write your code

Make your change. Keep it focused. If your fix is about the dashboard, do not also change the login page in the same branch. Two unrelated changes belong in two separate branches and two separate pull requests.

### 5. Add a test

If you added new behavior, add a test for it. The test files are:

* `qr/tests.py`
* `users/tests.py`
* `analytics/tests.py`

Open the file closest to what you changed and copy the pattern of an existing test. New behavior with no test is much harder to keep working over time.

### 6. Run the tests

```bash
python manage.py test
```

All tests must pass. If a test fails, fix it before moving on. Do not skip a failing test by deleting it.

### 7. Commit your change

```bash
git add .
git commit -m "fix: dashboard cards no longer overlap on mobile"
```

The commit message should be one short sentence describing what changed.

### 8. Push to your fork

```bash
git push origin fix/dashboard-mobile-layout
```

### 9. Open a pull request

Go to your fork on GitHub. You will see a banner asking if you want to open a pull request. Click it.

In the pull request description, write:

* What you changed
* Why you changed it
* Which issue it fixes (use the format "Fixes #123" so GitHub links them)

A maintainer will review your code. They might ask for changes. That is normal. Make the requested changes, push them to the same branch, and the pull request updates automatically.

## What kinds of changes are welcome

* Bug fixes with a test that proves the bug is fixed
* New analytics features (charts, exports, filters)
* Better mobile layout
* Better error messages
* Documentation improvements
* Test coverage for code that does not have tests yet
* Performance improvements that come with a measurement

## What kinds of changes will be turned down

These are common changes that get rejected, and the reason for each:

* **Storing login tokens in browser localStorage.** The whole login system is built on cookies. Changing it to localStorage opens the app to attacks where a malicious script can steal the token.
* **Letting QR codes point to non-web URLs** (like `javascript:` or `file:`). The current code rejects anything that is not `http` or `https`. This is on purpose. It blocks attacks where someone makes a QR code that runs scripts on the scanner's phone.
* **Making the redirect endpoint go straight to the destination for anonymous users.** The current code shows a confirmation page first. This stops the app from being used in phishing schemes.
* **Refactors that change a lot of code without changing what it does.** Big rewrites are risky. They are hard to review and they often hide bugs. Small focused changes are easier to merge.
* **Adding a dependency you only need once.** New dependencies have to be maintained forever. If you can do it without a new package, do it without.
* **Changes with no tests.**

## Reporting security problems

If you find a security vulnerability, do not open a public issue. Sending it through a public issue tells attackers about the problem before it can be fixed. Instead, email the maintainer through their GitHub profile. You should hear back within 72 hours.

## Code style

* Python: follow PEP 8. There is no automatic formatter. Match the style of the file you are editing.
* Comments: explain why the code does something, not what it does. If the code is self explanatory, do not add a comment.
* Do not leave `TODO` or `FIXME` notes in code that gets merged. File an issue instead.
* HTML and JavaScript: plain HTML and plain JavaScript only. Do not add React, Vue, Tailwind, or a build step.
* Variable and function names: use full words. `count` is better than `cnt`. `user_email` is better than `ue`.

## Getting help

If you are stuck:

1. Re-read this guide and the README.
2. Search closed issues to see if someone hit the same problem.
3. Open a new issue describing what you tried and what is not working. Include error messages and the commands you ran.

There are no stupid questions. A confusing setup step is something the docs need to fix, not something you should figure out alone.

## License

By submitting a contribution you agree it can be used under the terms of the project's LICENSE file.
