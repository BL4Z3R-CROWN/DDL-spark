"""
Flask App: SQL DDL to PySpark Schema Converter
Enhanced with editable per-field data types
"""
from flask import Flask, request, jsonify, render_template_string
import traceback
from converter import ddl_to_pyspark, describe_to_pyspark, parse_ddl, generate_pyspark_code
from db_utils import build_connection_string, fetch_schema_via_inspector, SQLALCHEMY_AVAILABLE

app = Flask(__name__)

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>DDL → PySpark Schema Converter</title>
<style>
  :root{
    --bg:#0f1117;
    --card:#1a1d27;
    --card2:#242836;
    --border:#2a2e42;
    --accent:#7c5cff;
    --accent2:#4f46e5;
    --accent-hover:#6d4aff;
    --text:#e6e8f0;
    --muted:#9aa0b8;
    --success:#10b981;
    --warning:#f59e0b;
    --radius:14px;
  }
  *{box-sizing:border-box}
  body{
    margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    background: radial-gradient(1200px 600px at 20% -10%, #1e1b4b 0%, transparent 60%),
                radial-gradient(900px 500px at 90% 0%, #0e3a5a 0%, transparent 60%),
                var(--bg);
    color:var(--text);
    min-height:100vh;
  }
  a{color:var(--accent)}
  header{
    max-width:1280px; margin:0 auto; padding:28px 20px 10px; display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  }
  .brand{display:flex; gap:14px; align-items:center}
  .logo{width:44px; height:44px; border-radius:12px; background: linear-gradient(135deg, var(--accent) 0%, #38bdf8 100%); display:grid; place-items:center; font-weight:800; font-size:20px; color:white; box-shadow:0 8px 24px rgba(124,92,255,.35)}
  .brand h1{margin:0; font-size:22px; letter-spacing:-.02em}
  .brand p{margin:2px 0 0; color:var(--muted); font-size:13px}
  .badge{font-size:12px; padding:6px 10px; border-radius:999px; background:rgba(124,92,255,.12); border:1px solid rgba(124,92,255,.25); color:#c4b5fd}
  .container{max-width:1280px; margin:0 auto; padding:18px 20px 40px}
  .grid{display:grid; grid-template-columns: 1.05fr 1.15fr; gap:20px}
  @media(max-width:1100px){ .grid{grid-template-columns:1fr} }
  .card{background:var(--card); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,.25)}
  .card-header{padding:16px 18px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; gap:12px}
  .card-header h2{margin:0; font-size:14px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted)}
  .tabs{display:flex; gap:8px; flex-wrap:wrap; background:var(--card2); padding:6px; border-radius:999px; border:1px solid var(--border)}
  .tab{padding:8px 14px; border-radius:999px; font-size:13px; font-weight:600; cursor:pointer; border:none; background:transparent; color:var(--muted); transition:.18s}
  .tab.active{background:var(--accent); color:white; box-shadow:0 4px 14px rgba(124,92,255,.35)}
  .tab:hover{color:var(--text)}
  .card-body{padding:18px}
  label{font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); font-weight:700; display:block; margin:14px 0 8px}
  label:first-child{margin-top:0}
  textarea, input, select{
    width:100%; background:var(--card2); border:1px solid var(--border); color:var(--text);
    border-radius:10px; padding:12px 14px; font-size:13px; outline:none; transition:.18s; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  textarea:focus, input:focus, select:focus{border-color:var(--accent); box-shadow:0 0 0 3px rgba(124,92,255,.2)}
  textarea{resize:vertical; min-height:160px; line-height:1.5}
  .hint{font-size:12px; color:var(--muted); margin-top:6px; line-height:1.4}
  .row{display:flex; gap:10px; flex-wrap:wrap}
  .row > *{flex:1}
  .btn{
    appearance:none; border:none; padding:11px 16px; border-radius:10px; font-weight:700; font-size:13px; cursor:pointer; transition:.18s;
    display:inline-flex; align-items:center; justify-content:center; gap:8px; white-space:nowrap;
  }
  .btn-primary{background:linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%); color:white; box-shadow:0 6px 18px rgba(124,92,255,.35)}
  .btn-primary:hover{transform:translateY(-1px); filter:brightness(1.05)}
  .btn-ghost{background:var(--card2); border:1px solid var(--border); color:var(--text)}
  .btn-ghost:hover{border-color:#3a3f5c}
  .btn-sm{padding:7px 10px; font-size:12px; border-radius:8px}
  .btn-xs{padding:5px 8px; font-size:11px; border-radius:7px}
  .btn-danger{background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.3); color:#fca5a5}
  .btn-danger:hover{background:rgba(239,68,68,.2)}
  .actions{display:flex; gap:10px; margin-top:14px; flex-wrap:wrap}
  .example-chips{display:flex; gap:8px; flex-wrap:wrap; margin-top:8px}
  .chip{font-size:11px; padding:6px 10px; border-radius:999px; background:var(--card2); border:1px solid var(--border); color:var(--muted); cursor:pointer}
  .chip:hover{color:var(--text); border-color:var(--accent)}
  .output-card .card-header{background:linear-gradient(180deg, rgba(124,92,255,.08), transparent)}
  .code-block{
    background:#0b0d14; border:1px solid var(--border); border-radius:12px; overflow:hidden; margin-top:12px;
  }
  .code-head{display:flex; align-items:center; justify-content:space-between; padding:10px 12px; background:#11131d; border-bottom:1px solid var(--border); flex-wrap:wrap; gap:8px}
  .code-head span{font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--muted)}
  .code-actions{display:flex; gap:8px}
  pre{margin:0; padding:14px; overflow:auto; font-size:12.5px; line-height:1.6; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; white-space:pre; max-height:380px}
  code{font-family:inherit}
  .table-wrap{overflow:auto; border:1px solid var(--border); border-radius:12px; margin-top:12px}
  table{width:100%; border-collapse:collapse; font-size:13px}
  th{ text-align:left; padding:10px 12px; background:#11131d; color:var(--muted); font-size:11px; letter-spacing:.06em; text-transform:uppercase; border-bottom:1px solid var(--border); white-space:nowrap}
  td{padding:8px 10px; border-bottom:1px solid rgba(42,46,66,.6); vertical-align:middle}
  tr:last-child td{border-bottom:none}
  tr.edited{ background: rgba(124,92,255,.05); }
  .spark-pill{font-family:ui-monospace, monospace; font-size:12px; padding:4px 8px; border-radius:999px; background:rgba(124,92,255,.15); border:1px solid rgba(124,92,255,.25); color:#c4b5fd}
  .nullable-yes{color:var(--success); font-weight:700}
  .nullable-no{color:var(--warning); font-weight:700}
  .empty{padding:30px; text-align:center; color:var(--muted)}
  .status{padding:10px 12px; border-radius:10px; font-size:13px; display:none; margin-top:12px}
  .status.error{display:block; background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.3); color:#fca5a5}
  .status.success{display:block; background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.3); color:#6ee7b7}
  .status.info{display:block; background:rgba(124,92,255,.12); border:1px solid rgba(124,92,255,.3); color:#c4b5fd}
  .footer{max-width:1280px; margin:20px auto 0; padding:0 20px 30px; color:var(--muted); font-size:12px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; border-top:1px solid var(--border); padding-top:16px}
  .kbd{font-family:ui-monospace, monospace; background:var(--card2); border:1px solid var(--border); border-bottom-width:2px; padding:2px 6px; border-radius:6px; font-size:11px}
  .hidden{display:none !important}
  .spinner{width:14px; height:14px; border:2px solid rgba(255,255,255,.3); border-top-color:white; border-radius:50%; animation:spin .7s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  ::-webkit-scrollbar{width:8px; height:8px}
  ::-webkit-scrollbar-thumb{background:#2a2e42; border-radius:999px}
  ::-webkit-scrollbar-track{background:transparent}
  /* Editable specific */
  .type-select{
    min-width:160px; padding:7px 8px; font-size:12px; border-radius:8px; background:#0b0d14; border:1px solid var(--border); color:var(--text);
    font-family: ui-monospace, monospace;
  }
  .type-select:focus{ border-color:var(--accent); }
  .mini-input{
    width:60px !important; padding:6px 8px !important; font-size:12px; border-radius:8px; display:inline-block;
  }
  .decimal-wrap{ display:flex; align-items:center; gap:6px; margin-top:6px; font-size:12px; color:var(--muted); }
  .decimal-wrap span{ color:var(--muted); font-family:ui-monospace, monospace; }
  .toggle{
    position:relative; width:44px; height:24px; background:var(--card2); border:1px solid var(--border); border-radius:999px; cursor:pointer; transition:.2s;
    display:inline-block; vertical-align:middle;
  }
  .toggle.active{ background: var(--success); border-color: var(--success); }
  .toggle::after{
    content:""; position:absolute; top:2px; left:2px; width:18px; height:18px; background:white; border-radius:50%; transition:.2s; box-shadow:0 1px 3px rgba(0,0,0,.3);
  }
  .toggle.active::after{ transform: translateX(20px); }
  .col-name-input{
    background:transparent !important; border:1px dashed transparent !important; padding:6px 8px !important; font-weight:700; border-radius:8px; min-width:120px;
  }
  .col-name-input:hover{ border-color: var(--border) !important; background: var(--card2) !important; }
  .col-name-input:focus{ border-color: var(--accent) !important; background: var(--card2) !important; border-style:solid !important; }
  .edit-badge{ font-size:10px; padding:2px 6px; border-radius:999px; background:rgba(245,158,11,.15); border:1px solid rgba(245,158,11,.3); color:#fde68a; margin-left:6px; display:none; }
  .edit-badge.show{ display:inline-block; }
  .toolbar{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:12px; padding:12px; background:var(--card2); border:1px solid var(--border); border-radius:12px; }
  .toolbar label{ margin:0; font-size:11px; }
  .toolbar select, .toolbar input{ padding:8px 10px; font-size:12px; border-radius:8px; }
  .edited-dot{ width:8px; height:8px; border-radius:50%; background:var(--warning); display:inline-block; margin-left:4px; vertical-align:middle; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <div class="logo">⚡</div>
    <div>
      <h1>DDL → PySpark Schema</h1>
      <p>Convert SQL DDL & DESCRIBE output to <code>pyspark.sql.types.StructType</code></p>
    </div>
  </div>
  <div class="badge">✦ Supports MySQL • Postgres • Oracle • SQL Server • Hive • SQLite • Editable Types</div>
</header>

<div class="container">
  <div class="grid">
    <!-- INPUT -->
    <div class="card">
      <div class="card-header">
        <h2>Input</h2>
        <div class="tabs" role="tablist">
          <button class="tab active" data-tab="ddl" onclick="switchTab('ddl')">SQL DDL</button>
          <button class="tab" data-tab="describe" onclick="switchTab('describe')">DESCRIBE</button>
          <button class="tab" data-tab="live" onclick="switchTab('live')">Live DB</button>
        </div>
      </div>
      <div class="card-body">
        <!-- DDL TAB -->
        <div id="panel-ddl">
          <label for="ddlInput">Create Table DDL</label>
          <textarea id="ddlInput" placeholder="Paste your CREATE TABLE statement here...">CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    age TINYINT,
    salary DECIMAL(10,2) DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    hired_at DATETIME,
    profile_json JSON,
    avatar BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);</textarea>
          <div class="example-chips">
            <span class="chip" onclick="loadExample('mysql')">MySQL example</span>
            <span class="chip" onclick="loadExample('postgres')">Postgres example</span>
            <span class="chip" onclick="loadExample('oracle')">Oracle example</span>
            <span class="chip" onclick="loadExample('hive')">Hive example</span>
          </div>
          <label for="tableOverride">Table name override (optional)</label>
          <input id="tableOverride" placeholder="e.g., employees_schema (leave blank to use DDL table name)" />
          <div class="hint">We parse <span class="kbd">CREATE TABLE</span> including column types, lengths, <span class="kbd">NOT NULL</span>, and nested types like <span class="kbd">DECIMAL(10,2)</span>, <span class="kbd">ARRAY&lt;STRING&gt;</span>.</div>
          <div class="actions">
            <button class="btn btn-primary" onclick="convertDDL()"><span id="ddlBtnIcon">⚡</span> Convert to PySpark</button>
            <button class="btn btn-ghost" onclick="clearDDL()">Clear</button>
          </div>
          <div id="ddlStatus" class="status"></div>
        </div>

        <!-- DESCRIBE TAB -->
        <div id="panel-describe" class="hidden">
          <label for="describeInput">Paste DESCRIBE / information_schema output</label>
          <textarea id="describeInput" style="min-height:180px" placeholder="Paste output from DESCRIBE, e.g.:

Field | Type | Null | Key | Default | Extra
id | int(11) | NO | PRI | NULL | auto_increment
full_name | varchar(255) | NO |  | NULL | 
email | varchar(255) | YES | UNI | NULL | 
salary | decimal(10,2) | YES |  | 0.00 | 
is_active | tinyint(1) | NO |  | 1 | 
hired_at | datetime | YES |  | NULL | 
">Field | Type | Null | Key | Default | Extra
id | int(11) | NO | PRI | NULL | auto_increment
full_name | varchar(255) | NO |  | NULL | 
email | varchar(255) | YES | UNI | NULL | 
salary | decimal(10,2) | YES |  | 0.00 | 
is_active | tinyint(1) | NO |  | 1 | 
hired_at | datetime | YES |  | NULL | </textarea>
          <div class="hint">Supports MySQL <span class="kbd">DESCRIBE table</span>, Postgres <span class="kbd">\d table</span>, CSV, TSV, pipe-separated, or markdown tables. Header must contain something like <span class="kbd">Field | Type | Null</span> or <span class="kbd">column_name | data_type | is_nullable</span>.</div>
          <label for="describeTableName">Target table name</label>
          <input id="describeTableName" value="my_table" placeholder="my_table" />
          <div class="actions">
            <button class="btn btn-primary" onclick="convertDescribe()"><span>⚡</span> Convert DESCRIBE → PySpark</button>
            <button class="btn btn-ghost" onclick="document.getElementById('describeInput').value=''">Clear</button>
          </div>
          <div id="describeStatus" class="status"></div>
        </div>

        <!-- LIVE DB TAB -->
        <div id="panel-live" class="hidden">
          <div style="background:rgba(124,92,255,.08); border:1px solid rgba(124,92,255,.22); border-radius:10px; padding:10px 12px; font-size:12px; color:#c4b5fd; margin-bottom:12px">
            🔒 Connects via SQLAlchemy. We run <span class="kbd">inspector.get_columns(table)</span> (no data is fetched). Credentials are never stored. For demo without a real DB, try the SQLite path below.
          </div>
          <label>Database type</label>
          <select id="dbType" onchange="onDbTypeChange()">
            <option value="mysql">MySQL / MariaDB</option>
            <option value="postgresql">PostgreSQL</option>
            <option value="sqlite">SQLite (file or :memory:)</option>
            <option value="mssql">SQL Server (MSSQL)</option>
            <option value="oracle">Oracle</option>
            <option value="duckdb">DuckDB</option>
          </select>
          <div class="row" id="hostPortRow">
            <div><label for="dbHost">Host</label><input id="dbHost" value="localhost" placeholder="localhost" /></div>
            <div><label for="dbPort">Port</label><input id="dbPort" placeholder="3306" /></div>
          </div>
          <div class="row" id="userPassRow">
            <div><label for="dbUser">User</label><input id="dbUser" placeholder="root" /></div>
            <div><label for="dbPassword">Password</label><input id="dbPassword" type="password" placeholder="••••••••" /></div>
          </div>
          <label for="dbDatabase">Database / File</label>
          <input id="dbDatabase" placeholder="my_database or /path/to.db or :memory:" />
          <div class="row">
            <div><label for="dbTable">Table</label><input id="dbTable" placeholder="employees" /></div>
            <div><label for="dbSchema">Schema (optional)</label><input id="dbSchema" placeholder="public" /></div>
          </div>
          <div class="hint" id="sqliteHint" style="display:none">For SQLite, only <span class="kbd">Database / File</span> + <span class="kbd">Table</span> are needed. Use <span class="kbd">:memory:</span> to spin a throwaway in-memory DB (we'll create a demo table for you).</div>
          <div class="actions">
            <button class="btn btn-primary" onclick="fetchLive()"><span id="liveIcon">🔌</span> DESCRIBE from DB</button>
            <button class="btn btn-ghost" onclick="fillDemoSQLite()">Try SQLite demo</button>
          </div>
          <div id="liveStatus" class="status"></div>
        </div>

      </div>
    </div>

    <!-- OUTPUT -->
    <div class="card output-card">
      <div class="card-header">
        <h2>PySpark Output</h2>
        <div class="row" style="gap:8px; align-items:center; flex:0 0 auto">
          <select id="outputFormat" onchange="rerender()" style="width:auto; min-width:140px; padding:8px 10px; font-size:12px">
            <option value="code">Python code</option>
            <option value="json">JSON</option>
          </select>
          <button class="btn btn-ghost btn-sm" onclick="downloadOutput()">⬇ Download .py</button>
        </div>
      </div>
      <div class="card-body" id="outputBody">
        <div class="empty" id="emptyState">
          <div style="font-size:32px">◈</div>
          <div style="font-weight:700; margin-top:6px">No conversion yet</div>
          <div class="hint" style="max-width:360px; margin:8px auto 0">Paste DDL on the left and hit <span class="kbd">Convert to PySpark</span>. Your <span class="kbd">StructType</span> will appear here — <b>edit any field's type inline</b>.</div>
        </div>

        <div id="resultArea" class="hidden">
          <!-- code blocks -->
          <div class="code-block" id="codeBlock">
            <div class="code-head">
              <span>schema.py — auto-updates on edit</span>
              <div class="code-actions">
                <button class="btn btn-ghost btn-sm" onclick="copyCode()">⎘ Copy</button>
                <button class="btn btn-ghost btn-sm" onclick="copyImports()">Copy imports</button>
              </div>
            </div>
            <pre><code id="codeOutput"></code></pre>
          </div>

          <div class="code-block hidden" id="jsonBlock">
            <div class="code-head">
              <span>schema.json</span>
              <div class="code-actions"><button class="btn btn-ghost btn-sm" onclick="copyJson()">⎘ Copy JSON</button></div>
            </div>
            <pre><code id="jsonOutput"></code></pre>
          </div>

          <div style="display:flex; align-items:center; justify-content:space-between; margin-top:14px; gap:10px; flex-wrap:wrap">
            <label style="margin:0">Column preview <span style="font-weight:400; text-transform:none; letter-spacing:0; color:var(--muted); font-size:11px;">— click type to change • toggle nullable • inline rename</span></label>
            <span id="tableBadge" class="badge"></span>
          </div>

          <!-- Bulk toolbar -->
          <div class="toolbar" id="bulkToolbar">
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; flex:1">
              <label style="white-space:nowrap">Bulk:</label>
              <select id="bulkType" style="min-width:160px">
                <option value="">— Change type —</option>
                <option value="StringType()">StringType</option>
                <option value="IntegerType()">IntegerType</option>
                <option value="LongType()">LongType</option>
                <option value="ShortType()">ShortType</option>
                <option value="ByteType()">ByteType</option>
                <option value="FloatType()">FloatType</option>
                <option value="DoubleType()">DoubleType</option>
                <option value="DecimalType(10,2)">DecimalType(10,2)</option>
                <option value="BooleanType()">BooleanType</option>
                <option value="BinaryType()">BinaryType</option>
                <option value="DateType()">DateType</option>
                <option value="TimestampType()">TimestampType</option>
                <option value="ArrayType(StringType())">ArrayType(String)</option>
                <option value="MapType(StringType(),StringType())">MapType(String,String)</option>
              </select>
              <button class="btn btn-ghost btn-xs" onclick="bulkApplyType()">Apply to all</button>
              <button class="btn btn-ghost btn-xs" onclick="bulkApplyFilter('string')">Apply to String only</button>
            </div>
            <div style="display:flex; gap:8px">
              <button class="btn btn-ghost btn-xs" onclick="resetAllTypes()">↺ Reset all</button>
              <button class="btn btn-ghost btn-xs" onclick="addColumn()">+ Add column</button>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead><tr><th>#</th><th>Column <span style="font-weight:400; text-transform:none; color:var(--muted)">(editable)</span></th><th>SQL Type</th><th>PySpark Type <span style="color:#fde68a">✎ editable</span></th><th>Nullable</th><th></th></tr></thead>
              <tbody id="previewBody"></tbody>
            </table>
          </div>
          <div id="editHint" class="status info" style="display:block; margin-top:10px; font-size:11px">💡 <b>New:</b> Change any field's type via the dropdown. Decimal precision/scale are editable inline. Code on the left updates instantly. Edits are marked with <span class="edited-dot"></span></div>

          <div class="code-block" style="margin-top:12px">
            <div class="code-head"><span>Quick usage (updates with edits)</span></div>
            <pre><code id="usageBlock"></code></pre>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    <div>Built with Flask + PySpark types. No external CSS/JS required. <span class="kbd">POST /api/convert-ddl</span> for API.</div>
    <div style="display:flex; gap:12px; flex-wrap:wrap">
      <span> Lagos • 2026-09-17</span>
      <span>Python 3 • PySpark 3.5 • Editable v2</span>
    </div>
  </div>
</div>

<script>
let lastResult = null;
let lastTables = [];
let originalColumns = []; // deep copy for reset

const SPARK_OPTIONS = [
  "StringType()",
  "IntegerType()",
  "LongType()",
  "ShortType()",
  "ByteType()",
  "FloatType()",
  "DoubleType()",
  "DecimalType(10,0)",
  "DecimalType(10,2)",
  "DecimalType(18,4)",
  "DecimalType(38,18)",
  "BooleanType()",
  "BinaryType()",
  "DateType()",
  "TimestampType()",
  "ArrayType(StringType())",
  "ArrayType(IntegerType())",
  "ArrayType(LongType())",
  "ArrayType(DoubleType())",
  "MapType(StringType(),StringType())",
  "MapType(StringType(),IntegerType())",
  "MapType(StringType(),DoubleType())"
];

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=> t.classList.toggle('active', t.dataset.tab===name));
  document.getElementById('panel-ddl').classList.toggle('hidden', name!=='ddl');
  document.getElementById('panel-describe').classList.toggle('hidden', name!=='describe');
  document.getElementById('panel-live').classList.toggle('hidden', name!=='live');
}

function onDbTypeChange(){
  const t = document.getElementById('dbType').value;
  const isSqlite = t==='sqlite';
  document.getElementById('hostPortRow').style.display = isSqlite ? 'none' : 'flex';
  document.getElementById('userPassRow').style.display = isSqlite ? 'none' : 'flex';
  document.getElementById('sqliteHint').style.display = isSqlite ? 'block' : 'none';
  if(t==='mysql') document.getElementById('dbPort').placeholder='3306';
  if(t==='postgresql') document.getElementById('dbPort').placeholder='5432';
  if(t==='mssql') document.getElementById('dbPort').placeholder='1433';
  if(t==='oracle') document.getElementById('dbPort').placeholder='1521';
}

function showStatus(id, msg, isError){
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className = 'status ' + (isError ? 'error' : 'success');
  el.style.display = 'block';
  setTimeout(()=>{ el.style.display='none'; }, 6000);
}

function parseDecimal(sparkType){
  const m = sparkType.match(/DecimalType\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)/);
  if(m) return {p: m[1], s: m[2]};
  return null;
}

function inferImports(columns){
  const needed = new Set(["StructType","StructField"]);
  columns.forEach(c=>{
    const t = c.spark_type;
    if(t.includes("StringType")) needed.add("StringType");
    if(t.includes("IntegerType")) needed.add("IntegerType");
    if(t.includes("LongType")) needed.add("LongType");
    if(t.includes("ShortType")) needed.add("ShortType");
    if(t.includes("ByteType")) needed.add("ByteType");
    if(t.includes("FloatType")) needed.add("FloatType");
    if(t.includes("DoubleType")) needed.add("DoubleType");
    if(t.includes("DecimalType")) needed.add("DecimalType");
    if(t.includes("BooleanType")) needed.add("BooleanType");
    if(t.includes("BinaryType")) needed.add("BinaryType");
    if(t.includes("DateType")) needed.add("DateType");
    if(t.includes("TimestampType")) needed.add("TimestampType");
    if(t.includes("ArrayType")) needed.add("ArrayType");
    if(t.includes("MapType")) needed.add("MapType");
  });
  const order = ["StructType","StructField","StringType","IntegerType","LongType","ShortType","ByteType","FloatType","DoubleType","DecimalType","BooleanType","BinaryType","DateType","TimestampType","ArrayType","MapType"];
  const ordered = order.filter(x=>needed.has(x));
  // add any leftover
  needed.forEach(x=>{ if(!ordered.includes(x)) ordered.push(x); });
  return ordered;
}

function generateCode(columns, tableName){
  const imports = inferImports(columns);
  const importsStr = `from pyspark.sql.types import ${imports.join(", ")}`;
  const fields = columns.map(c=>{
    const nameEsc = c.name.replace(/"/g,'\\"');
    const nullable = c.nullable ? "True" : "False";
    return `    StructField("${nameEsc}", ${c.spark_type}, ${nullable})`;
  }).join(",\n");
  const code = `${importsStr}\n\n${tableName}_schema = StructType([\n${fields}\n])\n`;
  return {code, importsStr, imports};
}

function regenerateFromEdits(){
  if(!lastResult) return;
  const {code, importsStr} = generateCode(lastResult.columns, lastResult.table);
  lastResult.code = code;
  lastResult.imports = importsStr;
  // update displays
  document.getElementById('codeOutput').textContent = code;
  document.getElementById('jsonOutput').textContent = JSON.stringify(lastResult.columns, null, 2);
  document.getElementById('usageBlock').textContent =
`from pyspark.sql import SparkSession
${importsStr}

# ${lastResult.table} schema (edited)
${code.trim()}

spark = SparkSession.builder.getOrCreate()
df = spark.createDataFrame([], schema=${lastResult.table}_schema)
df.printSchema()`;
  // update edit badges
  lastResult.columns.forEach((c,i)=>{
    const badge = document.getElementById(`edit-badge-${i}`);
    if(!badge) return;
    const orig = originalColumns[i];
    const edited = !orig || orig.spark_type !== c.spark_type || orig.nullable !== c.nullable || orig.name !== c.name;
    badge.classList.toggle('show', edited);
    const row = document.getElementById(`row-${i}`);
    if(row) row.classList.toggle('edited', edited);
  });
}

function onTypeChange(idx, newVal){
  if(!lastResult) return;
  // Handle DecimalType custom: if user picks DecimalType we keep params? newVal already has params like DecimalType(10,2)
  // If they pick plain DecimalType without params, default to 10,0
  if(newVal === "DecimalType()") newVal = "DecimalType(10,0)";
  lastResult.columns[idx].spark_type = newVal;
  // infer spark_type_name
  const base = newVal.split("(")[0];
  lastResult.columns[idx].spark_type_name = base;
  // show/hide decimal editors
  const decWrap = document.getElementById(`decimal-wrap-${idx}`);
  if(decWrap){
    if(newVal.startsWith("DecimalType")){
      decWrap.style.display = "flex";
      const dec = parseDecimal(newVal);
      if(dec){
        document.getElementById(`dec-p-${idx}`).value = dec.p;
        document.getElementById(`dec-s-${idx}`).value = dec.s;
      }
    } else {
      decWrap.style.display = "none";
    }
  }
  regenerateFromEdits();
}

function onDecimalChange(idx){
  const p = document.getElementById(`dec-p-${idx}`).value || "10";
  const s = document.getElementById(`dec-s-${idx}`).value || "0";
  const newVal = `DecimalType(${p},${s})`;
  lastResult.columns[idx].spark_type = newVal;
  lastResult.columns[idx].spark_type_name = "DecimalType";
  regenerateFromEdits();
}

function onNullableToggle(idx){
  lastResult.columns[idx].nullable = !lastResult.columns[idx].nullable;
  const toggle = document.getElementById(`toggle-${idx}`);
  toggle.classList.toggle('active', lastResult.columns[idx].nullable);
  toggle.title = lastResult.columns[idx].nullable ? "Nullable: YES (click to make NOT NULL)" : "Nullable: NO (click to make nullable)";
  // update text label?
  document.getElementById(`nullable-label-${idx}`).textContent = lastResult.columns[idx].nullable ? "YES" : "NO";
  document.getElementById(`nullable-label-${idx}`).className = lastResult.columns[idx].nullable ? "nullable-yes" : "nullable-no";
  regenerateFromEdits();
}

function onNameChange(idx, val){
  lastResult.columns[idx].name = val.trim() || `col_${idx}`;
  regenerateFromEdits();
}

function resetRow(idx){
  if(!originalColumns[idx]) return;
  lastResult.columns[idx].spark_type = originalColumns[idx].spark_type;
  lastResult.columns[idx].spark_type_name = originalColumns[idx].spark_type_name;
  lastResult.columns[idx].nullable = originalColumns[idx].nullable;
  lastResult.columns[idx].name = originalColumns[idx].name;
  renderPreviewOnly();
  regenerateFromEdits();
}

function resetAllTypes(){
  if(!lastResult) return;
  lastResult.columns.forEach((c,i)=>{
    if(originalColumns[i]){
      c.spark_type = originalColumns[i].spark_type;
      c.spark_type_name = originalColumns[i].spark_type_name;
      c.nullable = originalColumns[i].nullable;
      c.name = originalColumns[i].name;
    }
  });
  renderPreviewOnly();
  regenerateFromEdits();
  showStatus('ddlStatus','Reset all fields to auto-detected types ✓', false);
}

function bulkApplyType(){
  const val = document.getElementById('bulkType').value;
  if(!val){ showStatus('ddlStatus','Select a type for bulk apply', true); return; }
  lastResult.columns.forEach((c,i)=>{ onTypeChange(i,val); });
  // need to update selects visually - re-render
  renderPreviewOnly();
  regenerateFromEdits();
}

function bulkApplyFilter(kind){
  const val = document.getElementById('bulkType').value;
  if(!val){ showStatus('ddlStatus','Select a type first', true); return; }
  if(kind==='string'){
    lastResult.columns.forEach((c,i)=>{
      if(c.spark_type.includes("StringType")){
        lastResult.columns[i].spark_type = val;
        lastResult.columns[i].spark_type_name = val.split("(")[0];
      }
    });
    renderPreviewOnly();
    regenerateFromEdits();
  }
}

function addColumn(){
  if(!lastResult) return;
  const newCol = {name: `new_column_${lastResult.columns.length+1}`, sql_type: "VARCHAR(255)", nullable: true, spark_type: "StringType()", spark_type_name: "StringType"};
  lastResult.columns.push(newCol);
  // push to originalColumns as undefined so it shows as edited
  renderPreviewOnly();
  regenerateFromEdits();
}

function removeColumn(idx){
  if(!lastResult) return;
  lastResult.columns.splice(idx,1);
  originalColumns.splice(idx,1);
  renderPreviewOnly();
  regenerateFromEdits();
}

function renderPreviewOnly(){
  if(!lastResult) return;
  const tb = document.getElementById('previewBody');
  tb.innerHTML = '';
  lastResult.columns.forEach((c,i)=>{
    const tr = document.createElement('tr');
    tr.id = `row-${i}`;
    const isEdited = originalColumns[i] && (originalColumns[i].spark_type !== c.spark_type || originalColumns[i].nullable !== c.nullable || originalColumns[i].name !== c.name);
    if(isEdited) tr.classList.add('edited');
    // Build type select options
    const selectOptions = SPARK_OPTIONS.map(opt=> `<option value="${opt}" ${opt===c.spark_type?'selected':''}>${opt}</option>`).join('');
    // If current type not in list, add it
    let extraOpt = "";
    if(!SPARK_OPTIONS.includes(c.spark_type)){
      extraOpt = `<option value="${c.spark_type}" selected>${c.spark_type} (custom)</option>`;
    }
    const dec = parseDecimal(c.spark_type);
    const showDecimal = c.spark_type.startsWith("DecimalType");
    tr.innerHTML = `
      <td style="color:var(--muted); text-align:center">${i+1} ${isEdited ? '<span class="edited-dot" title="edited"></span>' : ''}</td>
      <td>
        <input class="col-name-input" value="${c.name}" onchange="onNameChange(${i}, this.value)" oninput="onNameChange(${i}, this.value)" title="Editable column name" />
        <span id="edit-badge-${i}" class="edit-badge ${isEdited?'show':''}">edited</span>
      </td>
      <td><code style="font-size:12px; background:var(--card2); padding:3px 6px; border-radius:6px; border:1px solid var(--border)">${c.sql_type}</code></td>
      <td style="min-width:220px">
        <select class="type-select" onchange="onTypeChange(${i}, this.value)" title="Change PySpark type for ${c.name}">
          ${extraOpt}
          ${selectOptions}
        </select>
        <div id="decimal-wrap-${i}" class="decimal-wrap" style="display:${showDecimal?'flex':'none'}">
          <span>precision</span><input id="dec-p-${i}" class="mini-input" type="number" min="1" max="38" value="${dec?dec.p:'10'}" onchange="onDecimalChange(${i})" oninput="onDecimalChange(${i})" />
          <span>scale</span><input id="dec-s-${i}" class="mini-input" type="number" min="0" max="38" value="${dec?dec.s:'0'}" onchange="onDecimalChange(${i})" oninput="onDecimalChange(${i})" />
        </div>
      </td>
      <td style="text-align:center">
        <div id="toggle-${i}" class="toggle ${c.nullable?'active':''}" onclick="onNullableToggle(${i})" title="${c.nullable?'Nullable: YES (click to make NOT NULL)':'Nullable: NO (click to make nullable)'}"></div>
        <div id="nullable-label-${i}" class="${c.nullable?'nullable-yes':'nullable-no'}" style="font-size:11px; margin-top:4px; font-weight:700">${c.nullable?'YES':'NO'}</div>
      </td>
      <td style="text-align:center; white-space:nowrap">
        <button class="btn btn-ghost btn-xs" onclick="resetRow(${i})" title="Reset this field to auto-detected">↺</button>
        <button class="btn btn-ghost btn-xs btn-danger" onclick="removeColumn(${i})" title="Remove column">✕</button>
      </td>
    `;
    tb.appendChild(tr);
  });
}

function renderResult(data){
  // data can be single table {table, code, columns, imports} or {tables: [...]}
  if(data.tables){
    lastTables = data.tables;
    lastResult = data.tables[0];
  } else if(data.table){
    lastTables = [data];
    lastResult = data;
  } else {
    return;
  }
  // deep copy original for reset
  originalColumns = JSON.parse(JSON.stringify(lastResult.columns));
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('resultArea').classList.remove('hidden');
  document.getElementById('tableBadge').textContent = lastTables.length>1 ? `${lastTables.length} tables • showing: ${lastResult.table} • editable` : `Table: ${lastResult.table} • ${lastResult.columns.length} fields • editable`;
  
  // If multiple tables, show selector
  if(lastTables.length>1){
    // create simple selector if not exists
    let sel = document.getElementById('tableSelector');
    if(!sel){
      const div = document.createElement('div');
      div.style.marginTop = '10px';
      div.innerHTML = `<label>Multiple tables detected</label><select id="tableSelector" onchange="switchTable(this.value)">${lastTables.map((t,idx)=>`<option value="${idx}" ${idx===0?'selected':''}>${t.table} (${t.columns.length} cols)</option>`).join('')}</select>`;
      document.getElementById('resultArea').prepend(div);
    }
  }
  
  rerender();
  renderPreviewOnly();
  regenerateFromEdits();
}

function switchTable(idx){
  lastResult = lastTables[parseInt(idx)];
  originalColumns = JSON.parse(JSON.stringify(lastResult.columns));
  document.getElementById('tableBadge').textContent = `Table: ${lastResult.table} • ${lastResult.columns.length} fields • editable`;
  rerender();
  renderPreviewOnly();
  regenerateFromEdits();
}

function rerender(){
  if(!lastResult) return;
  const fmt = document.getElementById('outputFormat').value;
  document.getElementById('codeBlock').classList.toggle('hidden', fmt!=='code');
  document.getElementById('jsonBlock').classList.toggle('hidden', fmt!=='json');
  // code and json are updated via regenerateFromEdits, but ensure initial
  if(!lastResult.code || document.getElementById('codeOutput').textContent===""){
    const {code} = generateCode(lastResult.columns, lastResult.table);
    lastResult.code = code;
    document.getElementById('codeOutput').textContent = code;
    document.getElementById('jsonOutput').textContent = JSON.stringify(lastResult.columns, null, 2);
  } else {
    document.getElementById('codeOutput').textContent = lastResult.code;
    document.getElementById('jsonOutput').textContent = JSON.stringify(lastResult.columns, null, 2);
  }
}

async function convertDDL(){
  const ddl = document.getElementById('ddlInput').value.trim();
  const override = document.getElementById('tableOverride').value.trim();
  if(!ddl){ showStatus('ddlStatus','Please paste DDL first.', true); return; }
  const btn = document.querySelector('#panel-ddl .btn-primary');
  const orig = btn.innerHTML;
  btn.innerHTML = '<span class="spinner"></span> Converting...';
  btn.disabled = true;
  try{
    const res = await fetch('/api/convert-ddl', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ddl, table_name: override || null})});
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || 'Conversion failed');
    renderResult(data);
    showStatus('ddlStatus', `✓ Converted ${data.count} table(s): ${data.tables.map(t=>t.table).join(', ')} • Now edit types inline`, false);
  }catch(e){
    showStatus('ddlStatus', '✗ ' + e.message, true);
  }finally{
    btn.innerHTML = orig; btn.disabled=false;
  }
}

async function convertDescribe(){
  const text = document.getElementById('describeInput').value.trim();
  const table = document.getElementById('describeTableName').value.trim() || 'my_table';
  if(!text){ showStatus('describeStatus','Paste DESCRIBE output first.', true); return; }
  const btn = document.querySelector('#panel-describe .btn-primary');
  const orig = btn.innerHTML;
  btn.innerHTML = '<span class="spinner"></span> Converting...'; btn.disabled=true;
  try{
    const res = await fetch('/api/convert-describe', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({describe_text: text, table_name: table})});
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || 'Failed');
    renderResult(data);
    showStatus('describeStatus', `✓ Parsed ${data.columns.length} columns for ${data.table} • Edit types inline`, false);
  }catch(e){ showStatus('describeStatus','✗ '+e.message,true); }
  finally{ btn.innerHTML=orig; btn.disabled=false; }
}

async function fetchLive(){
  const payload = {
    db_type: document.getElementById('dbType').value,
    host: document.getElementById('dbHost').value,
    port: document.getElementById('dbPort').value,
    user: document.getElementById('dbUser').value,
    password: document.getElementById('dbPassword').value,
    database: document.getElementById('dbDatabase').value,
    table: document.getElementById('dbTable').value,
    schema: document.getElementById('dbSchema').value
  };
  if(!payload.database || !payload.table){ showStatus('liveStatus','Database and Table are required.', true); return; }
  const btn = document.querySelector('#panel-live .btn-primary');
  const orig = btn.innerHTML;
  btn.innerHTML = '<span class="spinner"></span> Connecting...'; btn.disabled=true;
  try{
    const res = await fetch('/api/connect', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || 'Connection failed');
    renderResult(data);
    showStatus('liveStatus', `✓ Fetched ${data.columns.length} columns from ${data.table} • Edit types inline`, false);
  }catch(e){ showStatus('liveStatus','✗ '+e.message,true); }
  finally{ btn.innerHTML=orig; btn.disabled=false; }
}

function loadExample(kind){
  const examples = {
    mysql: `CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    age TINYINT,
    salary DECIMAL(10,2) DEFAULT 0.00,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    hired_at DATETIME,
    profile_json JSON,
    avatar BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`,
    postgres: `CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    bio TEXT,
    balance NUMERIC(12,2) DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    birth_date DATE,
    last_login TIMESTAMPTZ,
    metadata JSONB,
    avatar BYTEA
);`,
    oracle: `CREATE TABLE EMPLOYEES (
    EMPLOYEE_ID NUMBER(6) PRIMARY KEY,
    FIRST_NAME VARCHAR2(20),
    LAST_NAME VARCHAR2(25) NOT NULL,
    EMAIL VARCHAR2(25) NOT NULL UNIQUE,
    SALARY NUMBER(8,2),
    HIRE_DATE DATE DEFAULT SYSDATE,
    IS_MANAGER CHAR(1) DEFAULT 'N',
    PROFILE CLOB,
    PHOTO BLOB
);`,
    hive: `CREATE TABLE sales (
    order_id BIGINT,
    customer_name STRING,
    amount DOUBLE,
    discount DECIMAL(5,2),
    is_returned BOOLEAN,
    order_date DATE,
    created_at TIMESTAMP,
    items ARRAY<STRING>,
    props MAP<STRING,STRING>
) STORED AS PARQUET;`
  };
  document.getElementById('ddlInput').value = examples[kind];
  switchTab('ddl');
}

function clearDDL(){ document.getElementById('ddlInput').value=''; document.getElementById('tableOverride').value=''; }

function copyCode(){ navigator.clipboard.writeText(lastResult.code).then(()=> showStatus('ddlStatus','Copied Python code ✓ (with your edits)',false)); }
function copyImports(){ navigator.clipboard.writeText(lastResult.imports).then(()=> showStatus('ddlStatus','Copied imports ✓',false)); }
function copyJson(){ navigator.clipboard.writeText(JSON.stringify(lastResult.columns,null,2)).then(()=> showStatus('ddlStatus','Copied JSON ✓ (with edits)',false)); }

function downloadOutput(){
  if(!lastResult) return;
  const blob = new Blob([lastResult.code + "\n# JSON view (edited):\n# " + JSON.stringify(lastResult.columns, null, 2).replace(/\n/g,"\n# ")], {type:'text/x-python'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download = `${lastResult.table}_schema.py`; a.click(); URL.revokeObjectURL(url);
}

function fillDemoSQLite(){
  document.getElementById('dbType').value='sqlite';
  onDbTypeChange();
  document.getElementById('dbDatabase').value=':memory:';
  document.getElementById('dbTable').value='employees';
  document.getElementById('dbSchema').value='';
  showStatus('liveStatus','Demo: will create in-memory SQLite with sample employees table and DESCRIBE it. Click DESCRIBE from DB.', false);
}

// init
onDbTypeChange();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/convert-ddl", methods=["POST"])
def api_convert_ddl():
    try:
        data = request.get_json(force=True)
        ddl = data.get("ddl", "")
        table_override = data.get("table_name")
        if not ddl or not ddl.strip():
            return jsonify({"error": "DDL is empty"}), 400
        result = ddl_to_pyspark(ddl, table_name_override=table_override)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

@app.route("/api/convert-describe", methods=["POST"])
def api_convert_describe():
    try:
        data = request.get_json(force=True)
        describe_text = data.get("describe_text", "")
        table_name = data.get("table_name", "my_table") or "my_table"
        if not describe_text.strip():
            return jsonify({"error": "DESCRIBE text is empty"}), 400
        result = describe_to_pyspark(describe_text, table_name=table_name)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

@app.route("/api/connect", methods=["POST"])
def api_connect():
    try:
        data = request.get_json(force=True)
        db_type = (data.get("db_type") or "").strip().lower()
        host = (data.get("host") or "").strip()
        port = (data.get("port") or "").strip()
        user = (data.get("user") or "").strip()
        password = (data.get("password") or "").strip()
        database = (data.get("database") or "").strip()
        table = (data.get("table") or "").strip()
        schema = (data.get("schema") or "").strip() or None

        if not db_type or not database or not table:
            return jsonify({"error": "db_type, database and table are required"}), 400

        if not SQLALCHEMY_AVAILABLE:
            return jsonify({"error": "SQLAlchemy not installed on server"}), 500

        # Special handling for :memory: sqlite demo - create a demo table first
        if db_type == "sqlite" and database == ":memory:":
            import os, sqlite3
            demo_path = "/tmp/demo_ddl2spark.db"
            if os.path.exists(demo_path):
                try:
                    os.remove(demo_path)
                except:
                    pass
            conn = sqlite3.connect(demo_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    age INTEGER,
                    salary REAL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    hired_at TIMESTAMP,
                    profile_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            conn.close()
            conn_str = f"sqlite:///{demo_path}"
        else:
            conn_str = build_connection_string(db_type, host, port, user, password, database)

        try:
            result = fetch_schema_via_inspector(conn_str, table, schema=schema)
        except Exception as e1:
            try:
                from db_utils import fetch_schema_via_describe
                result = fetch_schema_via_describe(conn_str, table)
            except Exception as e2:
                return jsonify({"error": f"Inspector failed: {e1}; DESCRIBE fallback failed: {e2}"}), 500

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "sqlalchemy": SQLALCHEMY_AVAILABLE})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
