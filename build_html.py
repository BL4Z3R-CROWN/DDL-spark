import pathlib, markdown

md_path = pathlib.Path("DOCUMENTATION.md")
md_text = md_path.read_text(encoding="utf-8")

# Convert
html_body = markdown.markdown(md_text, extensions=["extra", "toc", "tables", "fenced_code", "codehilite", "sane_lists"])

# Minimal toc generation via markdown's toc extension adds an id; we can keep body as is
# Build full HTML with self-contained CSS
html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>DDL → PySpark Converter — Documentation</title>
<meta name="description" content="Complete documentation for DDL to PySpark Schema Converter - editable per-field, API, CLI, library, sharing." />
<style>
  :root {{
    --bg: #ffffff;
    --bg2: #f8fafc;
    --card: #ffffff;
    --border: #e2e8f0;
    --border2: #cbd5e1;
    --text: #0f172a;
    --muted: #64748b;
    --accent: #7c5cff;
    --accent2: #4f46e5;
    --accent-light: #ede9fe;
    --success: #10b981;
    --warning: #f59e0b;
    --code-bg: #0f172a;
    --code-fg: #e2e8f0;
    --radius: 14px;
    --max: 1200px;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f1117;
      --bg2: #1a1d27;
      --card: #1a1d27;
      --border: #2a2e42;
      --border2: #3a3f5c;
      --text: #e6e8f0;
      --muted: #9aa0b8;
      --accent-light: rgba(124,92,255,.12);
      --code-bg: #0b0d14;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    background: var(--bg);
    color: var(--text);
    line-height: 1.65;
    -webkit-font-smoothing: antialiased;
  }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  header {{
    position: sticky; top:0; z-index:20;
    backdrop-filter: blur(10px);
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    border-bottom: 1px solid var(--border);
  }}
  .header-inner {{
    max-width: var(--max); margin: 0 auto; padding: 14px 20px;
    display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  }}
  .brand {{ display:flex; gap:12px; align-items:center; }}
  .logo {{
    width:40px; height:40px; border-radius:12px;
    background: linear-gradient(135deg, var(--accent) 0%, #38bdf8 100%);
    display:grid; place-items:center; font-weight:800; color:white;
    box-shadow: 0 8px 24px rgba(124,92,255,.25);
  }}
  .brand h1 {{ margin:0; font-size:18px; letter-spacing:-.02em; line-height:1.2; }}
  .brand p {{ margin:2px 0 0; color: var(--muted); font-size:12px; }}
  .header-actions {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
  .btn {{
    appearance:none; border:1px solid var(--border); background: var(--card);
    padding:8px 12px; border-radius:999px; font-size:12px; font-weight:700; cursor:pointer;
    display:inline-flex; align-items:center; gap:6px; color: var(--text); text-decoration:none;
  }}
  .btn-primary {{
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    color: white; border-color: transparent; box-shadow: 0 4px 14px rgba(124,92,255,.25);
  }}
  .btn:hover {{ filter: brightness(1.05); transform: translateY(-1px); }}
  .layout {{
    max-width: var(--max); margin: 0 auto; padding: 0 20px 40px;
    display:grid; grid-template-columns: 260px 1fr; gap: 28px;
  }}
  @media (max-width: 960px) {{ .layout {{ grid-template-columns: 1fr; }} .sidebar {{ display:none; }} }}
  .sidebar {{
    position: sticky; top: 64px; height: fit-content; max-height: calc(100vh - 80px); overflow:auto;
    padding: 18px 0;
  }}
  .sidebar h3 {{
    font-size:11px; letter-spacing:.08em; text-transform:uppercase; color: var(--muted);
    margin: 14px 0 8px; font-weight:800;
  }}
  .sidebar a {{
    display:block; padding:6px 10px; border-radius:8px; font-size:13px; color: var(--muted); line-height:1.4;
  }}
  .sidebar a:hover {{ background: var(--bg2); color: var(--text); text-decoration:none; }}
  .sidebar a.active {{ background: var(--accent-light); color: var(--accent); font-weight:700; }}
  .content {{
    min-width:0; padding-top: 10px;
  }}
  .content h1 {{ font-size:32px; letter-spacing:-.02em; margin: 18px 0 8px; line-height:1.15; }}
  .content h2 {{
    font-size:22px; letter-spacing:-.02em; margin: 36px 0 12px; padding-bottom:8px;
    border-bottom: 1px solid var(--border);
  }}
  .content h3 {{ font-size:16px; margin: 24px 0 8px; color: var(--text); }}
  .content h4 {{ font-size:14px; margin: 18px 0 8px; color: var(--muted); text-transform:uppercase; letter-spacing:.06em; }}
  .content p {{ margin: 10px 0; color: var(--text); }}
  .content ul, .content ol {{ margin: 10px 0; padding-left: 22px; }}
  .content li {{ margin: 4px 0; }}
  .content li::marker {{ color: var(--muted); }}
  .content table {{
    width:100%; border-collapse:collapse; margin: 14px 0; font-size:13px;
    border:1px solid var(--border); border-radius:12px; overflow:hidden;
    display:block; max-width:100%; overflow:auto;
  }}
  .content thead {{ background: var(--bg2); }}
  .content th {{ text-align:left; padding:10px 12px; font-size:11px; letter-spacing:.06em; text-transform:uppercase; color: var(--muted); border-bottom:1px solid var(--border); white-space:nowrap; }}
  .content td {{ padding:9px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
  .content tr:last-child td {{ border-bottom:none; }}
  .content code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: .92em; background: var(--bg2); border:1px solid var(--border);
    padding: 2px 6px; border-radius:6px; word-break: break-word;
  }}
  .content pre {{
    margin:14px 0; padding:16px; background: var(--code-bg); color: var(--code-fg);
    border-radius:12px; overflow:auto; border:1px solid var(--border);
    line-height:1.6; font-size:12.5px;
  }}
  .content pre code {{
    background: transparent; border: none; padding:0; color: inherit; font-size: inherit;
  }}
  /* codehilite token colors (light) */
  .codehilite {{ background: transparent; }}
  .content blockquote {{
    margin:14px 0; padding:12px 16px; border-left:4px solid var(--accent);
    background: var(--accent-light); border-radius: 0 10px 10px 0; color: var(--text);
  }}
  .badge {{
    display:inline-flex; align-items:center; gap:6px;
    font-size:11px; padding:4px 8px; border-radius:999px;
    background: var(--accent-light); border:1px solid #c4b5fd; color: var(--accent);
    font-weight:700;
  }}
  .hero {{
    margin:18px 0 20px; padding:20px; background: linear-gradient(135deg, var(--accent-light) 0%, transparent 100%);
    border:1px solid var(--border); border-radius: var(--radius);
  }}
  .hero p {{ margin:6px 0; color: var(--muted); font-size:13px; }}
  .kpi {{
    display:flex; gap:12px; flex-wrap:wrap; margin-top:12px;
  }}
  .kpi div {{
    flex:1; min-width:140px; padding:12px; background: var(--card); border:1px solid var(--border);
    border-radius:12px; text-align:center;
  }}
  .kpi strong {{ display:block; font-size:18px; color: var(--accent); }}
  .kpi span {{ font-size:11px; color: var(--muted); letter-spacing:.06em; text-transform:uppercase; font-weight:700; }}
  .callout {{
    margin:16px 0; padding:14px 16px; border-radius:12px; border:1px solid var(--border);
    display:flex; gap:12px; align-items:flex-start; background: var(--card);
  }}
  .callout-icon {{ font-size:18px; line-height:1; }}
  .footer {{
    max-width: var(--max); margin: 30px auto 0; padding: 18px 20px 30px;
    border-top:1px solid var(--border); color: var(--muted); font-size:12px;
    display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px;
  }}
  .toc-mobile {{
    display:none; margin:14px 0; padding:12px; background: var(--bg2); border:1px solid var(--border); border-radius:12px;
  }}
  @media (max-width:960px) {{ .toc-mobile {{ display:block; }} }}
  .toc-mobile summary {{ font-weight:800; cursor:pointer; }}
  .anchor {{ scroll-margin-top: 80px; }}
  /* Print */
  @media print {{
    header, .sidebar, .header-actions {{ display:none; }}
    .layout {{ grid-template-columns: 1fr; }}
    .content pre {{ white-space: pre-wrap; word-break: break-word; }}
  }}
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <div class="brand">
      <div class="logo">⚡</div>
      <div>
        <h1>DDL → PySpark Converter</h1>
        <p>Documentation v2.1 • Editable Types • API • CLI • Library</p>
      </div>
    </div>
    <div class="header-actions">
      <span class="badge">✦ MySQL • Postgres • Oracle • Hive • SQLite</span>
      <a class="btn btn-primary" href="#" onclick="window.print(); return false;">🖨 Print / Save PDF</a>
      <a class="btn" href="README.md" download>⬇ .md</a>
    </div>
  </div>
</header>

<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="hero" style="margin-top:0; padding:12px;">
      <div style="display:flex; gap:8px; flex-wrap:wrap;">
        <span class="badge">v2.1 editable</span>
        <span class="badge">Flask + SQLAlchemy</span>
      </div>
      <div class="kpi" style="margin-top:10px;">
        <div><strong>45+</strong><span>SQL Types</span></div>
        <div><strong>3</strong><span>Interfaces</span></div>
      </div>
    </div>
    <h3>Navigate</h3>
    <a href="#ddl-pyspark-schema-converter-complete-documentation">Top</a>
    <a href="#1-overview">1. Overview</a>
    <a href="#2-key-features">2. Key Features</a>
    <a href="#3-architecture--how-it-works">3. Architecture</a>
    <a href="#4-type-mapping--sql--pyspark">4. Type Mapping</a>
    <a href="#5-installation">5. Installation</a>
    <a href="#6-usage--web-ui">6. Web UI</a>
    <a href="#7-usage--editable-per-field-feature">7. Editable Feature</a>
    <a href="#8-usage--rest-api">8. REST API</a>
    <a href="#9-usage--cli">9. CLI</a>
    <a href="#10-usage--python-library">10. Python Library</a>
    <a href="#11-live-database-describe">11. Live DB</a>
    <a href="#12-examples-by-database-dialect">12. Examples</a>
    <a href="#13-sharing--distribution">13. Sharing</a>
    <a href="#14-deployment-options">14. Deployment</a>
    <a href="#15-security--performance">15. Security</a>
    <a href="#16-troubleshooting--faq">16. FAQ</a>
    <a href="#17-project-structure">17. Structure</a>
    <a href="#18-contributing--roadmap">18. Roadmap</a>
    <a href="#19-appendix--code-snippets">19. Appendix</a>
    <h3>Quick Links</h3>
    <a href="#" onclick="document.getElementById('content').scrollIntoView({{behavior:'smooth'}}); return false;">↑ Back to top</a>
    <a href="README.md">README.md</a>
    <a href="PUSH_TO_GITHUB.md">Push to GitHub guide</a>
  </aside>

  <main class="content" id="content">
    <div class="hero">
      <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
        <span class="badge">⚡ Live at http://0.0.0.0:5000</span>
        <span class="badge">Editable per-field types • Bulk • Decimal p/s</span>
      </div>
      <p><b>One parser for every dialect.</b> Paste <code>CREATE TABLE</code> or <code>DESCRIBE</code>, or connect live — get <code>pyspark.sql.types.StructType</code> instantly, then edit any field’s type inline.</p>
    </div>

    <details class="toc-mobile">
      <summary>Table of Contents</summary>
      <ol style="margin:8px 0 0; padding-left:18px; font-size:13px;">
        <li><a href="#1-overview">Overview</a></li>
        <li><a href="#2-key-features">Key Features</a></li>
        <li><a href="#3-architecture--how-it-works">Architecture</a></li>
        <li><a href="#4-type-mapping--sql--pyspark">Type Mapping</a></li>
        <li><a href="#5-installation">Installation</a></li>
        <li><a href="#6-usage--web-ui">Web UI</a></li>
        <li><a href="#7-usage--editable-per-field-feature">Editable</a></li>
        <li><a href="#8-usage--rest-api">REST API</a></li>
        <li><a href="#9-usage--cli">CLI</a></li>
        <li><a href="#10-usage--python-library">Library</a></li>
        <li><a href="#11-live-database-describe">Live DB</a></li>
        <li><a href="#12-examples-by-database-dialect">Examples</a></li>
        <li><a href="#13-sharing--distribution">Sharing</a></li>
        <li><a href="#14-deployment-options">Deployment</a></li>
        <li><a href="#15-security--performance">Security</a></li>
        <li><a href="#16-troubleshooting--faq">FAQ</a></li>
      </ol>
    </details>

    {html_body}

    <div class="callout" style="margin-top:30px; background: var(--accent-light); border-color: #c4b5fd;">
      <div class="callout-icon">🎉</div>
      <div>
        <b>Enjoy — and edit those types!</b><br/>
        <span style="color:var(--muted); font-size:13px;">For quick start see <code>README.md</code>. For push help see <code>PUSH_TO_GITHUB.md</code>. For code, read <code>converter.py</code>.</span>
      </div>
    </div>
  </main>
</div>

<div class="footer">
  <div>Lagos • 2026-09-17 • MIT • <code>main@ee5de21</code> → Docs v2.1 HTML</div>
  <div>Built with Flask + Vanilla JS • No CDN needed • <code>pip install -r requirements.txt && python app.py</code></div>
</div>

<script>
// Highlight active sidebar link on scroll
const links = document.querySelectorAll('.sidebar a[href^=\"#\"]');
const headings = [...document.querySelectorAll('.content h1, .content h2, .content h3')].map(h => {{
  h.classList.add('anchor');
  return h;
}});
const obs = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if(e.isIntersecting){{
      const id = e.target.id;
      links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#'+id));
    }}
  }});
}}, {{ rootMargin: "-30% 0px -60% 0px", threshold: 0 }});
headings.forEach(h => obs.observe(h));
</script>
</body>
</html>
"""

out = pathlib.Path("DOCUMENTATION.html")
out.write_text(html_template, encoding="utf-8")
print(f"Wrote {out} {out.stat().st_size} bytes")
