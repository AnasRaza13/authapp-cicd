# AuthApp: multi-tenant login app with a CI/CD pipeline (GitHub Actions + AWS)

A small multi-tenant Login and Registration web app (FastAPI, Jinja2, SQLAlchemy, SQLite),
deployed automatically to AWS every time you push to `main`.

```
 Code change ─▶ git push ─▶ GitHub Actions
                               │
          1 Unit tests ─▶ 2 Build zip ─▶ 3 Upload to S3 ─▶ 4 Deploy to EC2 ─▶ Verify live site
          (pytest)        (artifact)     (AWS S3 bucket)    (Systems Manager)   (/health)
```

| Assignment step | Where it happens |
|---|---|
| 1. Code change | Edit the `VERSION` file (shown in the page footer) or any text/feature |
| 2. GitHub push | `git push` to the `main` branch |
| 3. Pipeline trigger | `.github/workflows/ci-cd.yml` starts on every push to `main` |
| 4. Unit tests | Job 1: `python -m pytest`. A failing test stops the pipeline |
| 5. Build | Job 2: `scripts/package.py` creates `build-<version>-run<N>-<sha>.zip` |
| 6. Store in S3 | Job 3: uploads the zip to `s3://<bucket>/builds/` and updates `latest.txt` |
| 7. Deploy latest build | Job 4: tells the EC2 server (via AWS Systems Manager) to run `deploy/deploy.sh`, which reads `latest.txt` in S3, downloads that build, switches to it and restarts the app |
| 8. Verify production | The pipeline calls `http://<server>/health` until it reports the new build; you open the site and see the new version |

## Start here

**`docs/RUNBOOK.md`** is the click-by-click guide: AWS setup, GitHub secrets, first run, the live
demo, the "failing test" demo, troubleshooting and cleanup.

## Repository layout

```
.github/workflows/ci-cd.yml   the pipeline (test -> build -> S3 -> deploy -> verify)
app/                          the application (presentation / business / data layers)
tests/                        pytest unit tests (run on a throw-away database)
scripts/package.py            the build step
deploy/deploy.sh              runs ON the server: fetch latest from S3, switch release, health check, rollback
deploy/server_setup.sh        one-time server setup (paste as EC2 "User data")
docs/RUNBOOK.md               step-by-step instructions
docs/iam/                     the two IAM policies to create
VERSION                       the version number shown in the app (edit this for the demo)
```

## Run it on your own computer

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest              # run the unit tests
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Check http://127.0.0.1:8000/health for the version and build.

## How a deployment stays safe

- **Tests gate everything.** Each job needs the previous one, so a red test means nothing is built, uploaded or deployed.
- **The database is never overwritten.** On the server it lives in `/opt/authapp/data`, outside the release folders.
- **Health check with automatic rollback.** `deploy.sh` waits until `/health` reports the new build id. If it never does, it switches back to the previous release and fails the pipeline.
- **Least privilege.** The GitHub user can only upload to one bucket and run one command on one server. The server can only read from that bucket. No SSH port is open.
- **Private builds.** The S3 bucket blocks all public access.

## Known limits (fine for the assignment)

- The site uses plain HTTP on the server's IP address. HTTPS needs a domain name and a certificate.
- SQLite on one server is not for heavy production use. PostgreSQL (RDS) would be the next step.
- Anyone can join an existing company by typing its name. A real product would use invitations.
