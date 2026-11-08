const API_BASE = (window.API_BASE_URL || "").replace(/\/$/, "");
const $ = (id) => document.getElementById(id);
let selectedFile = null;
let lastResult = null;
let chartInstances = [];

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
function showMessage(message, type = "info") {
  const el = $("message");
  el.textContent = message;
  el.className = `message ${type}`;
}
function clearMessage() { $("message").className = "message hidden"; }
function setFile(file) {
  if (!file) return;
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["csv", "json"].includes(ext)) {
    showMessage("Please choose a CSV or JSON file.", "error");
    return;
  }
  selectedFile = file;
  $("dropzone").classList.add("hidden");
  $("file-row").classList.remove("hidden");
  $("file-type").textContent = ext.toUpperCase();
  $("file-name").textContent = file.name;
  $("file-size").textContent = formatBytes(file.size);
  $("process-btn").disabled = false;
  clearMessage();
}
function resetFile() {
  selectedFile = null;
  $("file-input").value = "";
  $("file-row").classList.add("hidden");
  $("dropzone").classList.remove("hidden");
  $("process-btn").disabled = true;
}
$("dropzone").addEventListener("click", () => $("file-input").click());
$("dropzone").addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") $("file-input").click(); });
$("file-input").addEventListener("change", e => setFile(e.target.files[0]));
$("remove-file").addEventListener("click", resetFile);
["dragenter", "dragover"].forEach(name => $("dropzone").addEventListener(name, e => {e.preventDefault(); $("dropzone").classList.add("dragover");}));
["dragleave", "drop"].forEach(name => $("dropzone").addEventListener(name, e => {e.preventDefault(); $("dropzone").classList.remove("dragover");}));
$("dropzone").addEventListener("drop", e => setFile(e.dataTransfer.files[0]));

function renderResult(data) {
  lastResult = data;
  const p = data.profile;
  const c = data.cleaning;
  $("stat-rows").textContent = p.rows.toLocaleString();
  $("stat-columns").textContent = p.columns.toLocaleString();
  $("stat-complete").textContent = `${p.completeness_percent}%`;
  $("stat-issues").textContent = c.exception_count.toLocaleString();
  $("quality-empty").classList.add("hidden");
  $("quality-results").classList.remove("hidden");
  $("meter-value").textContent = `${p.completeness_percent}%`;
  $("meter-ring").style.background = `conic-gradient(#6bdbc0 ${p.completeness_percent * 3.6}deg,#273650 0deg)`;
  const totalCells = p.rows * p.columns;
  $("complete-cells").textContent = Math.max(0, totalCells - p.missing_cells).toLocaleString();
  $("missing-cells").textContent = p.missing_cells.toLocaleString();
  $("duplicate-rows").textContent = p.duplicate_rows.toLocaleString();
  $("profile-count").textContent = `${p.columns} FIELDS`;
  $("column-list").innerHTML = "";
  p.column_profile.forEach(col => {
    const item = document.createElement("div");
    item.className = "column-item";
    const name = document.createElement("b");
    name.textContent = col.name;
    const meta = document.createElement("span");
    meta.textContent = `${col.dtype} · ${col.missing} missing`;
    item.append(name, meta);
    $("column-list").append(item);
  });
  $("result-summary").innerHTML = "";
  [
    [c.input_rows.toLocaleString(), "Input rows"],
    [c.output_rows.toLocaleString(), "Clean rows"],
    [c.removed_duplicates.toLocaleString(), "Duplicates removed"],
    [c.exception_count.toLocaleString(), "Exceptions reported"]
  ].forEach(([value, label]) => {
    const chip = document.createElement("div");
    chip.className = "summary-chip";
    const b = document.createElement("b"); b.textContent = value;
    const span = document.createElement("span"); span.textContent = label;
    chip.append(b, span); $("result-summary").append(chip);
  });
  $("download-clean").href = `${API_BASE}${data.downloads.cleaned_csv}`;
  $("download-exceptions").href = `${API_BASE}${data.downloads.exceptions_csv}`;
  $("results-panel").classList.remove("hidden");
  $("charts-panel").classList.remove("hidden");
  renderCharts(data);
  $("results-panel").scrollIntoView({behavior:"smooth", block:"start"});
}

function buildSummaryText(data) {
  const p = data.profile;
  const c = data.cleaning;
  const totalCells = p.rows * p.columns;
  const completeCells = Math.max(0, totalCells - p.missing_cells);
  const lines = [
    "BUSINESS DATA AUTOMATION TOOLKIT — ANALYSIS SUMMARY",
    "====================================================",
    `File: ${data.filename}`,
    `File size: ${formatBytes(data.file_size_bytes)}`,
    `Generated: ${new Date().toLocaleString()}`,
    "",
    "DATASET PROFILE",
    `Rows analyzed: ${p.rows}`,
    `Columns detected: ${p.columns}`,
    `Total cells: ${totalCells}`,
    `Complete cells: ${completeCells}`,
    `Missing cells: ${p.missing_cells}`,
    `Completeness: ${p.completeness_percent}%`,
    `Duplicate rows detected: ${p.duplicate_rows}`,
    "",
    "CLEANING RESULTS",
    `Input rows: ${c.input_rows}`,
    `Output rows: ${c.output_rows}`,
    `Duplicates removed: ${c.removed_duplicates}`,
    `Exceptions reported: ${c.exception_count}`,
    `Text columns trimmed: ${c.trimmed_text_columns}`,
    "",
    "COLUMN PROFILE",
    ...p.column_profile.map(col => `${col.name} | type: ${col.dtype} | missing: ${col.missing} | unique: ${col.unique}`),
    "",
    "NOTE: This report describes automated checks performed by this application. Review exception rows and business-specific rules before using the data in production."
  ];
  return lines.join("\n");
}

function downloadSummary() {
  if (!lastResult) return;
  const blob = new Blob([buildSummaryText(lastResult)], {type:"text/plain;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `analysis_summary_${new Date().toISOString().slice(0,10)}.txt`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function openSummary() {
  if (!lastResult) return;
  const data = lastResult;
  const p = data.profile;
  const c = data.cleaning;
  const totalCells = p.rows * p.columns;
  const completeCells = Math.max(0, totalCells - p.missing_cells);
  const container = $("summary-content");
  container.replaceChildren();
  const meta = document.createElement("p");
  meta.className = "summary-meta";
  meta.textContent = `${data.filename} · ${formatBytes(data.file_size_bytes)} · Generated ${new Date().toLocaleString()}`;
  container.append(meta);
  const kpis = document.createElement("div");
  kpis.className = "summary-kpis";
  [[p.rows,"Rows"],[p.columns,"Columns"],[`${p.completeness_percent}%`,"Completeness"],[c.exception_count,"Exceptions"]].forEach(([value,label]) => {
    const card=document.createElement("div"); card.className="summary-kpi";
    const b=document.createElement("b"); b.textContent=value;
    const span=document.createElement("span"); span.textContent=label;
    card.append(b,span); kpis.append(card);
  });
  container.append(kpis);
  const section=document.createElement("section"); section.className="summary-section";
  const heading=document.createElement("h3"); heading.textContent="Cleaning results"; section.append(heading);
  const table=document.createElement("table"); table.className="summary-table";
  const tbody=document.createElement("tbody");
  [["Complete cells",completeCells],["Missing cells",p.missing_cells],["Duplicate rows detected",p.duplicate_rows],["Input rows",c.input_rows],["Cleaned rows",c.output_rows],["Duplicates removed",c.removed_duplicates],["Text columns trimmed",c.trimmed_text_columns]].forEach(([label,value])=>{
    const tr=document.createElement("tr"); const th=document.createElement("th"); const td=document.createElement("td");
    th.textContent=label; td.textContent=Number(value).toLocaleString(); tr.append(th,td); tbody.append(tr);
  });
  table.append(tbody); section.append(table); container.append(section);
  const colSection=document.createElement("section"); colSection.className="summary-section";
  const colHeading=document.createElement("h3"); colHeading.textContent="Column profile"; colSection.append(colHeading);
  const colTable=document.createElement("table"); colTable.className="summary-table";
  const thead=document.createElement("thead"); const header=document.createElement("tr");
  ["Column","Type","Missing","Unique"].forEach(label=>{const th=document.createElement("th");th.textContent=label;header.append(th)});
  thead.append(header); colTable.append(thead);
  const colBody=document.createElement("tbody");
  p.column_profile.forEach(col=>{const tr=document.createElement("tr");[col.name,col.dtype,col.missing,col.unique].forEach(value=>{const td=document.createElement("td");td.textContent=value;tr.append(td)});colBody.append(tr)});
  colTable.append(colBody); colSection.append(colTable); container.append(colSection);
  $("summary-modal").classList.remove("hidden");
}

function closeSummary() { $("summary-modal").classList.add("hidden"); }

function escapeSvg(value) {
  return String(value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"}[ch]));
}
function renderCharts(data) {
  const p = data.profile;
  const c = data.cleaning;
  const complete = Math.max(0, p.rows * p.columns - p.missing_cells);
  const total = complete + p.missing_cells;
  const pct = total ? Math.round(complete / total * 100) : 0;
  const circumference = 2 * Math.PI * 66;
  const dash = circumference * pct / 100;
  $("completeness-chart").innerHTML = `
    <div class="donut-layout">
      <svg viewBox="0 0 180 180" class="donut-svg" aria-hidden="true">
        <circle cx="90" cy="90" r="66" fill="none" stroke="#293750" stroke-width="19"/>
        <circle cx="90" cy="90" r="66" fill="none" stroke="#42d6ad" stroke-width="19" stroke-linecap="round" stroke-dasharray="${dash} ${circumference-dash}" transform="rotate(-90 90 90)"/>
        <text x="90" y="86" text-anchor="middle" class="donut-number">${pct}%</text><text x="90" y="106" text-anchor="middle" class="donut-label">COMPLETE</text>
      </svg>
      <div class="chart-legend"><div><i class="legend-dot complete-dot"></i><span>Complete cells</span><b>${complete.toLocaleString()}</b></div><div><i class="legend-dot missing-dot"></i><span>Missing cells</span><b>${p.missing_cells.toLocaleString()}</b></div><small>${total.toLocaleString()} total cells checked</small></div>
    </div>`;

  const cols = [...p.column_profile].sort((a,b)=>b.missing-a.missing).slice(0,8);
  const maxMissing = Math.max(1, ...cols.map(x=>x.missing));
  const barRows = cols.length ? cols.map(col => `<div class="hbar-row"><span class="hbar-name" title="${escapeSvg(col.name)}">${escapeSvg(col.name)}</span><div class="hbar-track"><i style="width:${col.missing/maxMissing*100}%"></i></div><b>${col.missing.toLocaleString()}</b></div>`).join('') : '<div class="chart-empty">No columns available to display.</div>';
  $("missing-chart").innerHTML = `<div class="hbar-chart">${barRows}<div class="chart-footnote">Showing up to 8 columns with the most missing values</div></div>`;

  const values = [c.input_rows, c.output_rows, c.removed_duplicates];
  const labels = ["Input rows", "Cleaned rows", "Duplicates removed"];
  const colors = ["#8292ff", "#42d6ad", "#ffb86b"];
  const maxRows = Math.max(1, ...values);
  const bars = values.map((value,i)=>`<div class="vbar-item"><b>${value.toLocaleString()}</b><div class="vbar-track"><i style="height:${Math.max(value===0?2:7,value/maxRows*100)}%;background:${colors[i]}"></i></div><span>${labels[i]}</span></div>`).join('');
  $("cleaning-chart").innerHTML = `<div class="vbar-chart">${bars}</div>`;
}

$("view-summary-btn").addEventListener("click", openSummary);
$("download-summary-btn").addEventListener("click", downloadSummary);
$("modal-download-summary").addEventListener("click", downloadSummary);
$("close-summary-btn").addEventListener("click", closeSummary);
$("close-summary-bottom").addEventListener("click", closeSummary);
$("summary-modal").addEventListener("click", event => { if (event.target === $("summary-modal")) closeSummary(); });
document.addEventListener("keydown", event => { if (event.key === "Escape") closeSummary(); });

$("process-btn").addEventListener("click", async () => {
  if (!selectedFile) return;
  clearMessage();
  $("process-btn").disabled = true;
  $("progress-wrap").classList.remove("hidden");
  $("progress-label").textContent = "Uploading and analyzing…";
  $("progress-bar").style.width = "8%";
  $("progress-percent").textContent = "8%";
  const form = new FormData();
  form.append("file", selectedFile);
  try {
    // XHR provides upload progress and sends the file directly to the Python API.
    const result = await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/api/process`);
      xhr.upload.onprogress = event => {
        if (event.lengthComputable) {
          const percent = Math.min(90, Math.round(event.loaded / event.total * 90));
          $("progress-bar").style.width = `${percent}%`;
          $("progress-percent").textContent = `${percent}%`;
        }
      };
      xhr.onload = () => {
        let body = {};
        try { body = JSON.parse(xhr.responseText); } catch {}
        if (xhr.status >= 200 && xhr.status < 300) resolve(body);
        else reject(new Error(body.detail || `Server error (${xhr.status})`));
      };
      xhr.onerror = () => reject(new Error("Could not connect to the processing server. Check the API URL and backend status."));
      xhr.send(form);
    });
    $("progress-bar").style.width = "100%";
    $("progress-percent").textContent = "100%";
    $("progress-label").textContent = "Analysis complete";
    renderResult(result);
    showMessage(`Successfully processed ${selectedFile.name}. Your reports are ready below.`, "info");
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    $("process-btn").disabled = false;
    setTimeout(() => $("progress-wrap").classList.add("hidden"), 1200);
  }
});

$("sample-btn").addEventListener("click", () => {
  const csv = [
    "customer_id,customer_name,email,city,order_value",
    "1001, Ali Khan ,ali@example.com,Hyderabad,2500",
    "1002,Sara Ahmed,sara@example.com,Karachi,1800",
    "1003,Usman,wrong-email,Lahore,3200",
    "1004,Ayesha,,Hyderabad,2100",
    "1002,Sara Ahmed,sara@example.com,Karachi,1800",
    "1005, Bilal ,bilal@example.com ,Sukkur,1500"
  ].join("\n");
  const file = new File([csv], "sample_business_data.csv", {type:"text/csv"});
  setFile(file);
  showMessage("Sample dataset loaded. Select Analyze dataset to run the complete workflow.", "info");
});

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error();
    const data = await response.json();
    document.querySelector(".system-status").innerHTML = `<i></i> API online · ${data.max_upload_mb} MB max`;
  } catch {
    document.querySelector(".system-status").innerHTML = `<i style="background:#ffb86b"></i> API not connected`;
  }
}
checkHealth();
