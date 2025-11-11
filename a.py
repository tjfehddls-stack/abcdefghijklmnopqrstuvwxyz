import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * Hubble Galaxy Classifier – Single‑file React app (Vite-ready)
 * -------------------------------------------------------------
 * Features
 * - Drag & drop or file picker to add one or many galaxy images (local only)
 * - Quick feature sliders + toggles (bulge size, arm tightness, bar, ring, irregular, ellipticity)
 * - Live auto‑suggested class in Hubble scheme: E0–E7, S0, Sa/Sb/Sc, SBa/SBb/SBc, Irr
 * - Keyboard shortcuts for fast labeling
 * - Per‑image notes, confidence slider
 * - Session autosave to localStorage
 * - Export labeled dataset to JSON/CSV
 * - Minimal, clean Tailwind UI (works best with Tailwind; still functional without)
 *
 * How to run (minimal):
 * 1) npm create vite@latest hubble-classifier -- --template react
 * 2) cd hubble-classifier && npm i && npm i -D tailwindcss postcss autoprefixer
 * 3) npx tailwindcss init -p
 * 4) Configure Tailwind: add index.css with @tailwind base; @tailwind components; @tailwind utilities;
 *    and set content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"] in tailwind.config.js
 * 5) Replace src/App.jsx with this file’s content (or adjust imports) and add some basic Tailwind styles
 * 6) npm run dev
 */

const STORAGE_KEY = "hubble_classifier_images_v1";

// Types -------------------------------------------------------
function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/** @typedef {"None"|"Weak"|"Strong"} BarStrength */
/** @typedef {"None"|"Tight"|"Moderate"|"Loose"} ArmTightness */

/**
 * @typedef ImageItem
 * @prop {string} id
 * @prop {string} name
 * @prop {string} dataUrl
 * @prop {{
 *   bulge: number,           // 0..100 (0=small bulge, 100=very large)
 *   arms: ArmTightness,
 *   bar: BarStrength,
 *   ring: boolean,
 *   irregular: boolean,
 *   ellipticity: number,     // 0..7  (Hubble E-index approx.)
 *   s0Likelihood: number,    // 0..100 (use when disk present but arms faint)
 * }} features
 * @prop {string} suggestion   // auto‑suggested class
 * @prop {string} finalLabel   // user-confirmed label (editable)
 * @prop {number} confidence   // 0..100
 * @prop {string} notes
 */

// Utilities ---------------------------------------------------
function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }

/** Map features → Hubble class suggestion */
function suggestClass(f) {
  if (f.irregular) return "Irr";

  // Ellipticals E0–E7 if no arms and no bar, bulge large and s0Likelihood low
  const noSpiralStructure = f.arms === "None";
  if (noSpiralStructure && f.bar === "None" && f.bulge >= 60 && f.s0Likelihood < 40) {
    const e = clamp(Math.round(f.ellipticity), 0, 7);
    return `E${e}`;
  }

  // S0 (lenticular): disk visible / faint arms, ring sometimes; intermediate bulge
  if (f.s0Likelihood >= 60 && (f.arms === "None" || f.arms === "Tight")) {
    return f.ring ? "(R)S0" : "S0";
  }

  // Spirals: decide a/b/c by bulge (a=large, c=small) & arms tightness (a=tight, c=loose)
  const abcScore = (100 - f.bulge) + (f.arms === "Tight" ? 0 : f.arms === "Moderate" ? 30 : 60);
  let stage = "b";
  if (abcScore < 60) stage = "a"; else if (abcScore > 110) stage = "c";

  // Bar flag → SB*
  if (f.bar !== "None") {
    return `SB${stage.toUpperCase()}`;
  } else {
    return `S${stage.toUpperCase()}`;
  }
}

function toCSVRows(items) {
  const header = [
    "id","name","label","suggestion","confidence","bulge","arms","bar","ring","irregular","ellipticity","s0Likelihood","notes"
  ];
  const rows = items.map(it => [
    it.id,
    it.name,
    (it.finalLabel || "").replaceAll(",",";"),
    it.suggestion,
    it.confidence,
    it.features.bulge,
    it.features.arms,
    it.features.bar,
    it.features.ring,
    it.features.irregular,
    it.features.ellipticity,
    it.features.s0Likelihood,
    (it.notes || "").replaceAll(",",";")
  ]);
  return [header, ...rows].map(r => r.join(",")).join("\n");
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// Main App ----------------------------------------------------
export default function App() {
  const [items, setItems] = useState(/** @type {ImageItem[]} */([]));
  const [selectedId, setSelectedId] = useState(/** @type {string|null} */(null));

  // Load / Save session
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const data = JSON.parse(raw);
        if (Array.isArray(data)) setItems(data);
      }
    } catch {}
  }, []);
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); } catch {}
  }, [items]);

  const selected = useMemo(() => items.find(x => x.id === selectedId) || items[0] || null, [items, selectedId]);

  function addFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const readers = files.map(f => new Promise(resolve => {
      const r = new FileReader();
      r.onload = () => resolve({ name: f.name, dataUrl: String(r.result) });
      r.readAsDataURL(f);
    }));
    Promise.all(readers).then(loaded => {
      setItems(prev => {
        const next = [...prev, ...loaded.map(l => {
          /** @type {ImageItem} */
          const base = {
            id: uid(),
            name: l.name,
            dataUrl: l.dataUrl,
            features: {
              bulge: 50,
              arms: "Moderate",
              bar: "None",
              ring: false,
              irregular: false,
              ellipticity: 2,
              s0Likelihood: 30,
            },
            suggestion: "",
            finalLabel: "",
            confidence: 70,
            notes: "",
          };
          base.suggestion = suggestClass(base.features);
          return base;
        })];
        if (!selectedId && next.length) setSelectedId(next[0].id);
        return next;
      });
    });
  }

  function updateItem(id, patch) {
    setItems(prev => prev.map(it => it.id === id ? ({ ...it, ...patch }) : it));
  }

  function updateFeatures(id, fpatch) {
    setItems(prev => prev.map(it => {
      if (it.id !== id) return it;
      const f = { ...it.features, ...fpatch };
      return { ...it, features: f, suggestion: suggestClass(f) };
    }));
  }

  function removeItem(id) {
    setItems(prev => prev.filter(it => it.id !== id));
    if (selected && selected.id === id) setSelectedId(null);
  }

  function exportJSON() {
    const blob = new Blob([JSON.stringify(items, null, 2)], { type: "application/json" });
    downloadBlob("hubble_labels.json", blob);
  }

  function exportCSV() {
    const csv = toCSVRows(items);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    downloadBlob("hubble_labels.csv", blob);
  }

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e) {
      if (!selected) return;
      if (e.target && (/** @type any */(e.target)).tagName === "INPUT" || (/** @type any */(e.target)).tagName === "TEXTAREA") return;
      const k = e.key.toLowerCase();
      if (k === "i") updateFeatures(selected.id, { irregular: !selected.features.irregular });
      if (k === "b") updateFeatures(selected.id, { bar: selected.features.bar === "None" ? "Strong" : selected.features.bar === "Strong" ? "Weak" : "None" });
      if (k === "r") updateFeatures(selected.id, { ring: !selected.features.ring });
      if (k === "0"||k==="1"||k==="2"||k==="3"||k==="4"||k==="5"||k==="6"||k==="7") {
        updateFeatures(selected.id, { ellipticity: Number(k), arms: "None", bar: "None", s0Likelihood: 10, bulge: 80 });
      }
      if (k === "s") {
        // Cycle S0 → Sa → Sb → Sc
        const f = selected.features;
        const order = ["S0","Sa","Sb","Sc"];
        const currentIndex = order.indexOf(selected.finalLabel || selected.suggestion);
        const next = order[(currentIndex + 1) % order.length];
        const mapping = {
          S0: { s0Likelihood: 80, arms: "None", bulge: 60, bar: "None" },
          Sa: { s0Likelihood: 20, arms: "Tight", bulge: 70, bar: "None" },
          Sb: { s0Likelihood: 10, arms: "Moderate", bulge: 50, bar: "None" },
          Sc: { s0Likelihood: 10, arms: "Loose", bulge: 25, bar: "None" },
        };
        updateFeatures(selected.id, mapping[next]);
        updateItem(selected.id, { finalLabel: next });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <ForkIcon className="w-6 h-6"/>
          <h1 className="text-xl font-semibold">Hubble Galaxy Classifier</h1>
          <span className="ml-auto" />
          <button className="px-3 py-1.5 rounded-xl bg-slate-900 text-white hover:opacity-90" onClick={exportCSV}>Export CSV</button>
          <button className="px-3 py-1.5 rounded-xl bg-slate-200 hover:bg-slate-300" onClick={exportJSON}>Export JSON</button>
          <label className="px-3 py-1.5 rounded-xl bg-indigo-600 text-white cursor-pointer hover:opacity-90">
            Add Images
            <input type="file" className="hidden" multiple accept="image/*" onChange={e => addFiles(e.target.files)} />
          </label>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 grid md:grid-cols-12 gap-4">
        {/* Sidebar: List */}
        <aside className="md:col-span-3">
          <DropBox onFiles={addFiles} />
          <div className="mt-3 bg-white border border-slate-200 rounded-2xl overflow-hidden">
            <div className="px-3 py-2 text-sm font-medium border-b">Images ({items.length})</div>
            <ul className="max-h-[60vh] overflow-auto">
              {items.map(it => (
                <li key={it.id} className={`flex items-center gap-2 px-3 py-2 border-b last:border-b-0 cursor-pointer hover:bg-slate-50 ${selected && selected.id===it.id?"bg-indigo-50/70":''''}`} onClick={()=>setSelectedId(it.id)}>
                  <img src={it.dataUrl} alt="thumb" className="w-10 h-10 object-cover rounded-lg border"/>
                  <div className="truncate">
                    <div className="text-sm font-medium truncate">{it.name}</div>
                    <div className="text-xs text-slate-500">{it.finalLabel || it.suggestion}</div>
                  </div>
                  <button className="ml-auto text-xs text-rose-600 hover:underline" onClick={(e)=>{e.stopPropagation(); removeItem(it.id)}}>Delete</button>
                </li>
              ))}
              {!items.length && (
                <li className="px-3 py-8 text-center text-slate-500 text-sm">Drop images here or click <span className="font-medium">Add Images</span>.</li>
              )}
            </ul>
          </div>

          <HelpCard />
        </aside>

        {/* Main: Inspector */}
        <section className="md:col-span-9">
          {!selected ? (
            <div className="h-[60vh] grid place-items-center text-slate-500">No image selected</div>
          ) : (
            <div className="grid lg:grid-cols-2 gap-4">
              <div className="bg-white border border-slate-200 rounded-2xl p-3">
                <img src={selected.dataUrl} alt={selected.name} className="w-full h-[440px] object-contain rounded-xl bg-slate-100 border"/>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-slate-600">
                  <Stat label="Suggestion" value={selected.suggestion} />
                  <Stat label="Final Label" value={selected.finalLabel || "—"} />
                  <Stat label="Confidence" value={`${selected.confidence}%`} />
                  <Stat label="Ring" value={selected.features.ring?"Yes":"No"} />
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-2xl p-3 space-y-3">
                <h2 className="text-base font-semibold">Annotate</h2>

                <RangeRow label="Bulge prominence" value={selected.features.bulge} onChange={(v)=>updateFeatures(selected.id,{bulge:v})} hint="Large bulge → a, small → c" />
                <SelectRow label="Arm tightness" value={selected.features.arms} onChange={(v)=>updateFeatures(selected.id,{arms:v})} options={["None","Tight","Moderate","Loose"]} />
                <SelectRow label="Bar" value={selected.features.bar} onChange={(v)=>updateFeatures(selected.id,{bar:v})} options={["None","Weak","Strong"]} />
                <ToggleRow label="Ring (R)" checked={selected.features.ring} onChange={(v)=>updateFeatures(selected.id,{ring:v})} />
                <ToggleRow label="Irregular (Irr)" checked={selected.features.irregular} onChange={(v)=>updateFeatures(selected.id,{irregular:v})} />

                <div className="grid grid-cols-2 gap-3">
                  <RangeRow label="Elliptical index E0–E7" value={selected.features.ellipticity} min={0} max={7} step={1} onChange={(v)=>updateFeatures(selected.id,{ellipticity:v})} hint="Use only for ellipticals" />
                  <RangeRow label="S0 likelihood" value={selected.features.s0Likelihood} onChange={(v)=>updateFeatures(selected.id,{s0Likelihood:v})} hint="Higher → S0" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <TextRow label="Final label" value={selected.finalLabel} placeholder={selected.suggestion} onChange={(v)=>updateItem(selected.id,{finalLabel:v})} />
                  <RangeRow label="Confidence" value={selected.confidence} onChange={(v)=>updateItem(selected.id,{confidence:v})} />
                </div>

                <div>
                  <label className="text-sm font-medium">Notes</label>
                  <textarea className="w-full mt-1 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" rows={3} placeholder="e.g., foreground star contamination, low S/N …" value={selected.notes} onChange={e=>updateItem(selected.id,{notes:e.target.value})} />
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"None", bar:"None", s0Likelihood:10, bulge:80}); updateItem(selected.id,{finalLabel:`E${Math.round(selected.features.ellipticity)}`}); }}>Set as Elliptical</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{s0Likelihood:85, arms:"None", bar:"None", bulge:60}); updateItem(selected.id,{finalLabel:"S0"}); }}>Set as S0</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"Tight", bar:"None", bulge:70}); updateItem(selected.id,{finalLabel:"Sa"}); }}>Sa</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"Moderate", bar:"None", bulge:50}); updateItem(selected.id,{finalLabel:"Sb"}); }}>Sb</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"Loose", bar:"None", bulge:25}); updateItem(selected.id,{finalLabel:"Sc"}); }}>Sc</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"Tight", bar:"Strong", bulge:70}); updateItem(selected.id,{finalLabel:"SBa"}); }}>SBa</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"Moderate", bar:"Strong", bulge:50}); updateItem(selected.id,{finalLabel:"SBb"}); }}>SBb</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{arms:"Loose", bar:"Strong", bulge:25}); updateItem(selected.id,{finalLabel:"SBc"}); }}>SBc</QuickSet>
                  <QuickSet onClick={() => { updateFeatures(selected.id,{irregular:true}); updateItem(selected.id,{finalLabel:"Irr"}); }}>Irr</QuickSet>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      <footer className="max-w-7xl mx-auto px-4 pb-10 pt-4 text-xs text-slate-500">
        <p className="leading-relaxed">
          Shortcuts: <kbd className="kbd">0..7</kbd> set E0–E7, <kbd className="kbd">B</kbd> toggle bar, <kbd className="kbd">R</kbd> toggle ring, <kbd className="kbd">I</kbd> toggle irregular, <kbd className="kbd">S</kbd> cycle S0→Sa→Sb→Sc.
        </p>
      </footer>
    </div>
  );
}

// UI Bits -----------------------------------------------------
function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 px-3 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}

function RangeRow({ label, value, onChange, min=0, max=100, step=1, hint }) {
  return (
    <div>
      <div className="flex items-end justify-between">
        <label className="text-sm font-medium">{label}</label>
        <span className="text-xs text-slate-500">{value}</span>
      </div>
      <input type="range" className="w-full" min={min} max={max} step={step} value={value} onChange={e=>onChange(Number(e.target.value))} />
      {hint && <div className="text-xs text-slate-500 mt-0.5">{hint}</div>}
    </div>
  );
}

function SelectRow({ label, value, onChange, options }) {
  return (
    <div>
      <label className="text-sm font-medium">{label}</label>
      <select value={value} onChange={e=>onChange(e.target.value)} className="w-full mt-1 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
        {options.map(op => <option key={op} value={op}>{op}</option>)}
      </select>
    </div>
  );
}

function ToggleRow({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-3 select-none">
      <input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)} className="w-4 h-4"/>
      <span className="text-sm font-medium">{label}</span>
    </label>
  );
}

function TextRow({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="text-sm font-medium">{label}</label>
      <input type="text" value={value} placeholder={placeholder} onChange={e=>onChange(e.target.value)} className="w-full mt-1 rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
    </div>
  );
}

function QuickSet({ children, onClick }) {
  return (
    <button onClick={onClick} className="px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-100 text-sm">
      {children}
    </button>
  );
}

function DropBox({ onFiles }) {
  const ref = useRef(null);
  const [over, setOver] = useState(false);
  return (
    <div ref={ref}
      onDragOver={(e)=>{e.preventDefault(); setOver(true);}}
      onDragLeave={()=>setOver(false)}
      onDrop={(e)=>{e.preventDefault(); setOver(false); onFiles(e.dataTransfer.files);}}
      className={`rounded-2xl border-2 border-dashed p-4 text-center ${over?"border-indigo-400 bg-indigo-50/40":"border-slate-300"}`}>
      <div className="text-sm">Drag & drop images here</div>
      <div className="text-xs text-slate-500">or use <span className="font-medium">Add Images</span> above</div>
    </div>
  );
}

function HelpCard() {
  return (
    <div className="mt-3 bg-white border border-slate-200 rounded-2xl p-3 text-sm text-slate-700 space-y-2">
      <div className="font-semibold">Hubble overview</div>
      <ul className="list-disc ml-5 space-y-1">
        <li><span className="font-medium">E0–E7</span>: Ellipticals (index ~ 10×(1−b/a)). More elongated → higher E.</li>
        <li><span className="font-medium">S0</span>: Lenticular (disk + large bulge, arms faint/absent; rings common).</li>
        <li><span className="font-medium">Sa→Sc</span>: Unbarred spirals; bulge decreases, arms open up.</li>
        <li><span className="font-medium">SBa→SBc</span>: Barred spirals; same Sa→Sc trend, with bar.</li>
        <li><span className="font-medium">Irr</span>: Irregular (no obvious bulge/arms symmetry).</li>
      </ul>
      <div className="text-xs text-slate-500">Tip: Use the controls to approximate morphology; the app suggests a class you can override.</div>
    </div>
  );
}

function ForkIcon(props){
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M7 3v5a4 4 0 0 0 4 4h2a4 4 0 0 0 4-4V3"/>
      <circle cx="7" cy="3" r="2"/>
      <circle cx="17" cy="3" r="2"/>
      <path d="M12 12v6"/>
      <circle cx="12" cy="21" r="2"/>
    </svg>
  );
}

// End of file
