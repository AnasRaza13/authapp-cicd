# Runbook: build and demonstrate the CI/CD pipeline

Follow the parts in order. Total time: about 45 minutes, mostly waiting for AWS.

**Names used below** (you can choose your own, just stay consistent):

| Thing | Name / value |
|---|---|
| AWS Region | **Asia Pacific (Singapore) `ap-southeast-1`** (use it for everything) |
| S3 bucket | `authapp-builds-<yourname>-<4 digits>` (must be globally unique, lowercase) |
| EC2 server | `authapp-server`, Ubuntu 24.04, `t3.micro` |
| Server IAM role | `authapp-ec2-role` |
| GitHub IAM user | `github-deployer` |
| GitHub repository | `authapp-cicd` |

You need: a GitHub account, an AWS account, and [Git for Windows](https://git-scm.com/download/win).

---

## Part 1: AWS setup

Sign in to the AWS Console and set the Region (top-right) to **Asia Pacific (Singapore)**.

### 1.1 Create the S3 bucket
1. Open **S3** > **Create bucket**.
2. **Bucket name:** `authapp-builds-<yourname>-<4 digits>`. Region: `ap-southeast-1`.
3. Leave **Block all public access** ticked. Leave everything else as default. Click **Create bucket**.
4. Write the bucket name down.

### 1.2 Create the server's IAM role
1. Open **IAM** > **Roles** > **Create role**.
2. Trusted entity: **AWS service**. Use case: **EC2**. Click **Next**.
3. Tick the policy **AmazonSSMManagedInstanceCore** (this lets the pipeline send commands to the server). **Next**.
4. Role name: `authapp-ec2-role`. **Create role**.
5. Open the new role > **Add permissions** > **Create inline policy** > **JSON** tab. Paste the contents of `docs/iam/ec2-s3-read-policy.json` and replace `YOUR-BUCKET-NAME` with your bucket name. **Next**, name it `read-builds`, **Create policy**.

### 1.3 Launch the EC2 server
Open **EC2** > **Launch instance** and set:

| Setting | Value |
|---|---|
| Name | `authapp-server` |
| Application image (AMI) | **Ubuntu** > **Ubuntu Server 24.04 LTS** (64-bit x86) |
| Instance type | `t3.micro` (or the type marked **Free tier eligible**) |
| Key pair | **Proceed without a key pair** (no SSH is needed) |
| Network settings > Edit | **Auto-assign public IP: Enable**. Create a new security group. **Delete the SSH rule.** Add one rule: **HTTP**, port 80, source **Anywhere** |
| Storage | default (8 GiB) |
| Advanced details > **IAM instance profile** | `authapp-ec2-role` |
| Advanced details > **User data** | paste the **whole contents of `deploy/server_setup.sh`** |

Click **Launch instance**. Then:
- Wait until **Status check** shows `2/2 checks passed` (about 3 minutes), then 3 more minutes for the setup script to finish.
- Open **Systems Manager** > **Fleet Manager** (or **Node Tools**). Your instance should appear with **Ping status: Online**. Do not continue until it does.
- Write down the **Instance ID** (`i-...`) and the **Public IPv4 address**.

*Optional but recommended:* **EC2** > **Elastic IPs** > **Allocate Elastic IP address** > **Associate** it with the instance. Then the address does not change if you stop and start the server. Use that IP below.

### 1.4 Create the limited IAM user for GitHub
1. **IAM** > **Policies** > **Create policy** > **JSON** tab. Paste `docs/iam/github-deployer-policy.json` and replace:
   - `YOUR-BUCKET-NAME` with your bucket name
   - `REGION` with `ap-southeast-1` (appears twice)
   - `ACCOUNT_ID` with your 12-digit AWS account number (top-right menu)
   - `INSTANCE_ID` with the `i-...` ID from step 1.3
2. Name it `github-deployer-policy`. **Create policy**.
3. **IAM** > **Users** > **Create user**. Name: `github-deployer`. Do **not** tick console access. **Next** > **Attach policies directly** > tick `github-deployer-policy` > **Create user**.
4. Open the user > **Security credentials** > **Create access key** > use case **Application running outside AWS** > **Create access key**.
5. Copy the **Access key ID** and the **Secret access key** now. The secret is shown only once.

---

## Part 2: GitHub setup

### 2.1 Create the repository
On github.com: **New repository**, name `authapp-cicd`, **do not** add a README or .gitignore. Create it.

### 2.2 Add the six secrets
Repository > **Settings** > **Secrets and variables** > **Actions** > **New repository secret**. Create exactly these names:

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | the access key ID from step 1.4 |
| `AWS_SECRET_ACCESS_KEY` | the secret access key from step 1.4 |
| `AWS_REGION` | `ap-southeast-1` |
| `S3_BUCKET` | your bucket name |
| `EC2_INSTANCE_ID` | the `i-...` ID |
| `APP_URL` | `http://<public IP>` (for example `http://203.0.113.10`, with `http://` and no trailing slash) |

### 2.3 Push the project (this starts the first pipeline run)
In PowerShell, inside the project folder:

```powershell
git init -b main
git add .
git commit -m "Initial commit: AuthApp with CI/CD pipeline"
git remote add origin https://github.com/<your-github-username>/authapp-cicd.git
git push -u origin main
```

If Git asks you to sign in, use the browser window it opens.

---

## Part 3: Watch the first run and open the live app

1. GitHub > **Actions** > click the running **CI/CD Pipeline**. You should see four jobs turn green in order: **1 - Unit tests**, **2 - Build package**, **3 - Upload build to S3**, **4 - Deploy latest build to EC2**.
2. In job 4, open **Wait for the deployment and show the server log**. You will see the server's own lines such as `Latest build: builds/build-1.0.0-run1-...zip` and `SUCCESS: version 1.0.0 ... is live`.
3. AWS **S3** > your bucket: the `builds/` folder holds the zip, and `latest.txt` points to it.
4. Open `http://<public IP>` in your browser. The footer reads **Version 1.0.0 · build run1-xxxxxxx**.
5. Register a company (for example `Acme Corp` / `alice`) and log in. This is your "before" state.

---

## Part 4: The demo: a code change reaches production

This is the flow your assignment asks you to show.

1. **Make a visible change.** In the project folder:
   ```powershell
   Set-Content -Path VERSION -Value "1.1.0"
   ```
   (Optional: also change some text in `app/presentation/templates/index.html`.)
2. **Commit and push:**
   ```powershell
   git add .
   git commit -m "Release 1.1.0"
   git push
   ```
3. **Watch GitHub Actions** start by itself and go through all four jobs.
4. **Check S3:** a second zip `build-1.1.0-run2-...zip` is in `builds/`, and `latest.txt` now points to it.
5. **Refresh `http://<public IP>`:** the footer now reads **Version 1.1.0**. Your earlier user is still there, because deployments never touch the database.
6. Open `http://<public IP>/health` to show `{"status":"ok","version":"1.1.0","build":"run2-..."}`.

**Screenshots to take for your submission:** the commit on GitHub; the Actions run with four green jobs; the S3 bucket listing; the live site before and after; the `/health` page.

---

## Part 5: Bonus demo: failing tests block the deployment

1. Open `app/business/services.py` and change `MIN_PASSWORD_LEN = 8` to `MIN_PASSWORD_LEN = 3`.
2. `git add .`, `git commit -m "Break password rule"`, `git push`.
3. In Actions, **1 - Unit tests** turns **red** and jobs 2, 3 and 4 are skipped. Production is untouched.
4. Undo it: `git revert HEAD --no-edit` then `git push`. The pipeline goes green again.

---

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Job 3 fails with `AccessDenied` or `Unable to locate credentials` | A secret is misspelled or empty, or the bucket name in `github-deployer-policy` is wrong |
| Job 4 fails with `InvalidInstanceId` | The server is not "Online" in Systems Manager. Check the role `authapp-ec2-role` is attached (EC2 > Actions > Security > Modify IAM role), wait 5 minutes, or reboot the instance |
| Job 4 fails with `AccessDeniedException` on `SendCommand` | The instance ID, Region or account number in `github-deployer-policy` is wrong |
| Job 4 shows `command not found` or `venv` errors in the server log | The setup script did not finish. In EC2 > **Connect** > **Session Manager**, run `sudo tail -50 /var/log/cloud-init-output.log` and `cat /var/log/authapp-setup-done` |
| Deployment says `did not become healthy` and rolls back | The new build has a problem. The server log in job 4 shows why. Production keeps serving the previous build |
| The final "Verify production" step times out | Port 80 is not open in the security group, `APP_URL` is wrong or uses `https://`, or the public IP changed after a stop/start (use an Elastic IP and update `APP_URL`) |
| Browser says "can't connect" | Use `http://` not `https://` (there is no HTTPS in this setup) |

Handy commands on the server (EC2 > **Connect** > **Session Manager** > **Connect**):

```bash
sudo systemctl status authapp
sudo journalctl -u authapp -n 50 --no-pager
curl http://localhost/health
ls /opt/authapp/releases
```

---

## Cleanup (to avoid charges)

When you have finished and submitted:
1. **EC2** > select `authapp-server` > **Instance state** > **Terminate**.
2. **EC2** > **Elastic IPs** > **Release** (if you created one).
3. **S3** > empty the bucket, then delete it.
4. **IAM** > delete the user `github-deployer` (and its access key), the policy `github-deployer-policy`, and the role `authapp-ec2-role`.

A `t3.micro` server and a tiny S3 bucket cost very little, but a forgotten server keeps billing, and public IPv4 addresses are charged hourly once any free allowance ends.
