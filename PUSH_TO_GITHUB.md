# Push to GitHub — DDL to PySpark Converter

Your repo is **already initialized and committed locally** at `/home/user`.

```
Branch: main
Commit: eddd6b5 - feat: initial commit - SQL DDL to PySpark schema converter
Files:  app.py, converter.py, db_utils.py, cli.py, requirements.txt, README.md, LICENSE, .gitignore, examples/
```

Bundle & ZIP are ready:
- `/home/user/ddl-to-pyspark.bundle` (27K - full git history)
- `/home/user/ddl-to-pyspark.zip` (27K - source files)

---

## Option A: Create a NEW repo on GitHub (recommended)

### 1. Create the repo on GitHub
Go to https://github.com/new

- **Repository name:** `ddl-to-pyspark` (or any name you want)
- **Description:** `Convert SQL DDL / DESCRIBE to PySpark StructType schemas`
- **Visibility:** Public / Private
- **IMPORTANT:** Leave **unchecked**:
  - ❌ Add a README file
  - ❌ Add .gitignore
  - ❌ Choose a license
  (because your local repo already has these)
- Click **Create repository**

### 2. Push from this workspace

GitHub will show you a URL like:
`https://github.com/YOUR_USERNAME/ddl-to-pyspark.git`

Run **one** of these in this workspace terminal (or on your local machine after downloading the ZIP):

#### If you use HTTPS + Personal Access Token (PAT)
> Create a token at https://github.com/settings/tokens/new — classic token with `repo` scope

```bash
cd /home/user

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ddl-to-pyspark.git

# Optional: ensure branch is main
git branch -M main

# Push with token (replace TOKEN and USERNAME)
git push -u origin main
# When prompted:
# Username: YOUR_USERNAME
# Password: <your PAT token>   (not your GitHub password)

# Or push in one line with token embedded (be careful - don't share logs):
git remote set-url origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/YOUR_USERNAME/ddl-to-pyspark.git
git push -u origin main
```

#### If you use SSH
```bash
cd /home/user
git remote add origin git@github.com:YOUR_USERNAME/ddl-to-pyspark.git
git branch -M main
git push -u origin main
```

### 3. Verify
Visit `https://github.com/YOUR_USERNAME/ddl-to-pyspark` — you should see all files.

---

## Option B: Push to an EXISTING repo

If you already have an empty repo `https://github.com/YOUR_USERNAME/existing-repo.git`:

```bash
cd /home/user
git remote add origin https://github.com/YOUR_USERNAME/existing-repo.git
git branch -M main
git push -u origin main

# If repo is not empty and you want to force overwrite (danger!):
# git push -u origin main --force
```

To push with a token in this workspace **right now**, just tell me:
- The repo URL
- I will run the push for you (you can paste a token - it will not be saved in the snapshot after you remove .git-credentials)

---

## Option C: Upload via GitHub Web UI (no git needed)

1. Download `ddl-to-pyspark.zip` from this workspace (see Files panel)
2. Go to https://github.com/new → create repo **with** README unchecked
3. On the new repo page, click **Add file → Upload files**
4. Drag the unzipped contents (or the ZIP itself - GitHub will unzip) and **Commit**

Or upload the bundle:
- The `.bundle` file is a full git clone: someone can `git clone ddl-to-pyspark.bundle`

---

## Option D: Quick download + local push

On your **local laptop**:

```bash
# Download ZIP from workspace, then:
unzip ddl-to-pyspark.zip -d ddl-to-pyspark
cd ddl-to-pyspark
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ddl-to-pyspark.git
git push -u origin main
```

---

## What's inside?

| File | Purpose |
|------|---------|
| `app.py` | Flask web app + REST API (port 5000) |
| `converter.py` | Core DDL/DESCRIBE → PySpark parser |
| `db_utils.py` | Live DB connector via SQLAlchemy |
| `cli.py` | CLI (`--ddl-file`, `--describe-file`, `--connect`) |
| `requirements.txt` | Flask, SQLAlchemy, pyspark, pymysql, psycopg2 |
| `examples/` | sample_mysql.sql + describe_mysql.txt |
| `README.md` | Full docs |
| `LICENSE` | MIT |

---

## Need me to push for you?

Just reply with:
```
https://github.com/YOUR_USERNAME/ddl-to-pyspark.git
```
and (if private / HTTPS) a **Personal Access Token** with `repo` scope. I'll run the push immediately and confirm.

Or paste your token as `TOKEN@URL` and I'll do it in one step.
