# Deploy Guide — DDL → PySpark (https://github.com/BL4Z3R-CROWN/DDL-spark)

Your repo `BL4Z3R-CROWN/DDL-spark` is **public** (current `77eb20` on `main`). Your local workspace is **4 commits ahead** (`d8e8a6b` includes `DOCUMENTATION.html` + GitHub Pages workflow). To finish the push + deploy, pick one path below.

---

## 🔑 Why you need a token (even for public repos)

- **Read** (clone, `ls-remote`) is anonymous for public repos — that's why `git ls-remote` worked.
- **Write** (`git push`) **always** requires authentication — GitHub returns `could not read Username` if no token.
- Making the repo public does **not** allow anonymous pushes (that would let anyone overwrite your code).

You need a **Personal Access Token (PAT)** with `repo` scope. It's a password like `ghp_xxxx` you generate once and paste when pushing. It is **not saved** in snapshots (`.git/config` is excluded).

---

## Option A — Push from THIS workspace (fastest — I do it for you)

### Step 1: Create a Classic PAT

1. Go to **https://github.com/settings/tokens/new**
   - Note: `ddl-spark-push`
   - Expiration: 7 days (or custom)
   - Scopes: check **`repo`** (Full control of private repositories)
   - Click **Generate token** → **Copy** the token (starts `ghp_` or `github_pat_`). You see it **once**.

> Alternative (Fine-grained token): https://github.com/settings/tokens?type=beta → Generate new token → Repository access → *Only select* `BL4Z3R-CROWN/DDL-spark` → Permissions → **Contents: Read and write**, **Pages: Write**, **Metadata: Read** → Generate.

### Step 2: Paste it here

Reply in this chat with:
```
ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
(or `YOUR_TOKEN https://github.com/BL4Z3R-CROWN/DDL-spark.git`)

I will run immediately:
```bash
cd /home/user
git remote set-url origin https://BL4Z3R-CROWN:TOKEN@github.com/BL4Z3R-CROWN/DDL-spark.git
git push -u origin main
git remote set-url origin https://github.com/BL4Z3R-CROWN/DDL-spark.git  # remove token from URL after
```

I’ll confirm with `git log` and the new commit hash on GitHub, then trigger the Pages deployment.

---

## Option B — Push manually from YOUR laptop (no token pasted here)

### 1. Download ZIP from this workspace
- In the IDE Files panel, download **`ddl-to-pyspark.zip`** (77KB) or **`DOCUMENTATION.html`**

### 2. On your laptop:

```bash
# 1. Create token as in Option A, Step 1 (copy ghp_xxx)

# 2. Get current repo (has your old commit 77eb20)
git clone https://github.com/BL4Z3R-CROWN/DDL-spark.git
cd DDL-spark
# OR if you downloaded the ZIP:
unzip ~/Downloads/ddl-to-pyspark.zip -d DDL-spark
cd DDL-spark
git init
git add .
git commit -m "initial"

# 3. Push with token (paste token when prompted, or embed)
git remote add origin https://github.com/BL4Z3R-CROWN/DDL-spark.git 2>/dev/null || git remote set-url origin https://github.com/BL4Z3R-CROWN/DDL-spark.git
git branch -M main
git push -u origin main
# When prompted:
# Username: BL4Z3R-CROWN
# Password: <your ghp_ token, NOT your GitHub password>
```

One-liner with token (don’t share logs):
```bash
git remote set-url origin https://BL4Z3R-CROWN:ghp_xxx@github.com/BL4Z3R-CROWN/DDL-spark.git
git push -u origin main
git remote set-url origin https://github.com/BL4Z3R-CROWN/DDL-spark.git
```

---

## Option C — GitHub Web UI (no CLI, no token)

1. Go to https://github.com/BL4Z3R-CROWN/DDL-spark → **Add file → Upload files**
2. Drag **all files** from `ddl-to-pyspark.zip` (unzipped) → **Commit directly to main**
3. For `DOCUMENTATION.html`, ensure it’s at repo root — GitHub Pages will serve it as `index.html` via the workflow below.

---

## 📄 Deploy — GitHub Pages for Documentation (HTML)

I’ve already added **`.github/workflows/deploy.yml`** to your local repo. When you push `main`, it:

- Copies `DOCUMENTATION.html` → `_site/index.html`
- Uploads as Pages artifact
- Deploys to `https://BL4Z3R-CROWN.github.io/DDL-spark/`

### Enable Pages (one-time, on GitHub)

After you push:

1. Go to **https://github.com/BL4Z3R-CROWN/DDL-spark/settings/pages**
2. Under **Build and deployment** → **Source:** select **GitHub Actions** (not “Deploy from branch”)
3. Wait ~1 min → Visit **https://BL4Z3R-CROWN.github.io/DDL-spark/** → Your docs appear!
4. Future pushes to `main` auto-redeploy (see **Actions** tab).

> No workflow? You can also do **Pages → Source: Deploy from branch** → Branch: `main`, `/ (root)`, and rename `DOCUMENTATION.html` to `index.html`.

---

## 🚀 Deploy — Flask Web App (Live Converter)

The Flask app (`app.py` on port 5000) needs a Python host. After GitHub push, **one-click deploy**:

### Render (free)

1. Go to https://dashboard.render.com → **New → Web Service** → Connect `BL4Z3R-CROWN/DDL-spark`
2. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`  (or `python app.py` if no gunicorn)
   - **Environment:** `Python 3.11`
   - **Port:** `10000` (Render sets `$PORT`; add to `app.py` if needed: `port=int(os.environ.get("PORT",5000))`)
3. **Create Web Service** → URL like `https://ddl-spark.onrender.com` — live in ~2 min.

`render.yaml` is already prepared? If not, use:

```yaml
# render.yaml
services:
  - type: web
    name: ddl-spark
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

### Railway / Fly.io / Vercel

- **Railway:** https://railway.app/new → Deploy from GitHub → same build/start.
- **Fly.io:** `fly launch` → `fly deploy`
- **Vercel (Python):** add `vercel.json` with `{ "builds": [{"src":"app.py","use":"@vercel/python"}]}`

---

## ✅ Verify After Push

```bash
git ls-remote https://github.com/BL4Z3R-CROWN/DDL-spark.git
# should show your local commits: d8e8a6b, ee5de21, etc., plus remote 77eb20

# Check Pages
curl -I https://BL4Z3R-CROWN.github.io/DDL-spark/
```

---

## 🆘 Troubleshooting

- **403 / Authentication failed:** Token missing `repo` scope or expired. Regenerate at https://github.com/settings/tokens/new → check `repo`.
- **remote: Repository not found:** Typo in URL or repo is private and token has no access.
- **Pages 404:** Ensure Settings → Pages → Source = **GitHub Actions** and workflow ran (check **Actions** tab, green check).
- **Render build failed:** Ensure `requirements.txt` includes `gunicorn` (add `gunicorn==21.2.0` if needed).

---

**Ready?** Paste your `ghp_...` token here and I’ll push + verify + tell you your Pages URL. Or tell me “download” and I’ll give you the ZIP.

*Lagos • 2026-09-17 • branch main @ d8e8a6b*
