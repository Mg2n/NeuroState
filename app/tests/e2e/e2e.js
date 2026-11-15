// Browser end-to-end checks (Playwright, Chromium). Run through app/tests/test_e2e.py, which starts the servers.
// env: BASE (server, no epilepsy results file), BASE_RESULTS (server with a fixture results file), SAMPLE, SHOTS
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const BASE = process.env.BASE, BASE_RESULTS = process.env.BASE_RESULTS, SAMPLE = process.env.SAMPLE, SHOTS = process.env.SHOTS;
const results = [];
async function step(name, fn) {
  try { await fn(); results.push(["PASS", name]); console.log("PASS", name); }
  catch (e) { results.push(["FAIL", name, e.message]); console.log("FAIL", name, "\n   ", e.stack.split("\n").slice(0, 4).join("\n    ")); }
}
const shot = (page, name, full = false) => page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: full });

async function waitReady(page, url) {
  await page.goto(url);
  await page.waitForFunction(() => window.__ns && window.__ns.ready);
}

async function plotBox(page, sel) { return page.locator(sel).locator(".nsewdrag").first().boundingBox(); }

async function clickCheck(page, x, y) {
  const before = await page.evaluate(() => (window.__ns.cursor ? window.__ns.cursor.i : -1));
  await page.mouse.click(x, y);
  await page.waitForFunction((b) => window.__ns.cursor && window.__ns.cursor.i !== b && window.__ns.inspector && window.__ns.inspector.i === window.__ns.cursor.i, before);
  await page.waitForTimeout(150);
  return page.evaluate(async () => {
    const ns = window.__ns, run = ns.demo || ns.run;
    const back = await (await fetch(`/api/runs/${run.run_id}/instant?i=${ns.cursor.i}`)).json();
    const shapes = ns.cursorShapes();
    const bars = [...document.querySelectorAll("#insp-bars .bar .val")].map((e) => e.textContent);
    return { i: ns.cursor.i, t0: run.t0, fs: run.fs, shapes, back, shown: ns.inspector, bars, label: document.querySelector("#insp-label").textContent };
  });
}

function assertSync(r) {
  const x = r.t0 + r.i / r.fs;
  assert.equal(r.shapes.length, 2, "cursor in both waveform and timeline");
  for (const s of r.shapes) assert.ok(Math.abs(s.x - x) < 1e-9, `${s.name} at ${s.x}, expected ${x}`);
  assert.deepEqual(r.shown.abs_r, r.back.abs_r);
  assert.equal(r.shown.label, r.back.label);
  assert.deepEqual(r.bars, r.back.abs_r.map((v) => v.toFixed(2)));
  assert.equal(r.label, "ABCD"[r.back.label]);
}

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const requests = [];
  page.on("request", (r) => requests.push(r.url()));

  await step("home renders", async () => {
    await waitReady(page, BASE);
    await page.waitForSelector("#open-demo");
    await shot(page, "01_home");
  });

  await step("demo opens from the bundle alone and walks through all 10 steps", async () => {
    requests.length = 0;
    await page.click("#open-demo");
    await page.waitForFunction(() => window.__ns.stageReady === "recording");
    await page.waitForTimeout(400);
    await shot(page, "02_demo_01_recording");
    const names = ["recording", "prepare", "snapshots", "peaks", "fit", "name", "timeline", "measures", "transitions", "cnn"];
    for (let k = 1; k < names.length; k++) {
      await page.keyboard.press(String((k + 1) % 10));
      await page.waitForFunction((id) => window.__ns.stageReady === id, names[k]);
      await page.waitForTimeout(700);
      await shot(page, `03_demo_${String(k + 1).padStart(2, "0")}_${names[k]}`);
    }
    assert.ok(!requests.some((u) => u.includes("/api/research")), "demo must not call the research pipeline");
    assert.ok(requests.some((u) => u.endsWith("/api/demo")));
    await page.keyboard.press("2");
    await page.waitForFunction(() => window.__ns.stageReady === "prepare");
    await page.locator("#how-btn").click();
    await page.waitForFunction(() => window.__ns.drawerOpen === true);
    assert.ok(await page.locator(".drawer.open .katex").count() > 0, "formula rendered with KaTeX in the drawer");
    await page.waitForTimeout(400);
    await shot(page, "03_demo_how_it_works_drawer");
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => window.__ns.drawerOpen === false);
  });

  await step("snapshots: the dots and the map are the backend's values at the chosen instant", async () => {
    await page.keyboard.press("3");
    await page.waitForFunction(() => window.__ns.stageReady === "snapshots" && window.__ns.snapshot);
    const box = await plotBox(page, "#wave");
    const before = await page.evaluate(() => window.__ns.snapshot.i);
    await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.4);
    await page.waitForFunction((b) => window.__ns.snapshot.i !== b, before);
    await page.waitForTimeout(600);
    const r = await page.evaluate(async () => {
      const ns = window.__ns, gd = document.querySelector("#wave");
      const dots = gd.data.find((t) => t.name === "dots");
      const back = await (await fetch(`/api/runs/demo/instant?i=${ns.snapshot.i}`)).json();
      const view = ns.demo.default_view, sp = ns.view ? null : null;
      return { i: ns.snapshot.i, frames: ns.snapshot.frames, dotsX: dots.x, dotsY: dots.y, back, view, src: document.querySelector("#snap-map").getAttribute("src"),
        film: [...document.querySelectorAll("#film img")].map((im) => im.getAttribute("src")), t0: ns.demo.t0, fs: ns.demo.fs,
        spacing: gd.layout.yaxis.tickvals };
    });
    const x = r.t0 + r.i / r.fs;
    assert.ok(r.dotsX.every((v) => Math.abs(v - x) < 1e-9), "dots sit on the cursor instant");
    r.view.forEach((c, k) => assert.ok(Math.abs(r.dotsY[k] - (r.back.values_uv[r.back.channels.indexOf(c)] + r.spacing[k])) < 1e-6, `dot ${c} = backend value`));
    assert.deepEqual(r.frames, Array.from({ length: 8 }, (_, k) => r.i - 3 + k));
    assert.ok(r.src.includes(`i=${r.i}&vmax=`));
    r.film.forEach((src, k) => assert.ok(src.includes(`i=${r.frames[k]}&vmax=`)));
  });

  await step("GFP peaks: a click selects the nearest peak; the low point is lower and on the same scale", async () => {
    await page.keyboard.press("4");
    await page.waitForFunction(() => window.__ns.stageReady === "peaks" && window.__ns.peakPick);
    const box = await plotBox(page, "#gfp-plot");
    await page.mouse.click(box.x + box.width * 0.62, box.y + box.height * 0.5);
    await page.waitForTimeout(800);
    const r = await page.evaluate(() => ({ p: window.__ns.peakPick, gfp: window.__ns.demo.gfp, peaks: window.__ns.demo.peak_idx, fs: window.__ns.demo.fs,
      a: document.querySelector("#peak-map").getAttribute("src"), b: document.querySelector("#low-map").getAttribute("src") }));
    assert.ok(r.peaks.includes(r.p.peak));
    assert.ok(r.gfp[r.p.low] <= r.gfp[r.p.peak] && Math.abs(r.p.low - r.p.peak) <= Math.round(r.fs / 10));
    assert.ok(r.a.endsWith(`vmax=${r.p.vmax}`) && r.b.endsWith(`vmax=${r.p.vmax}`), "same colour scale");
  });

  await step("patterns: real peak snapshots grouped under each fitted map, counts equal the backend", async () => {
    await page.keyboard.press("5");
    await page.waitForFunction(() => window.__ns.stageReady === "fit" && window.__ns.peakExamples);
    const r = await page.evaluate(async () => ({ shown: [...document.querySelectorAll("#clusters .cnt b")].map((b) => b.textContent),
      back: (await (await fetch("/api/runs/demo/peak_examples?n=4")).json()).maps, n: window.__ns.demo.steps.peaks.n_used }));
    const byCluster = [...r.back].sort((a, b) => a.cluster - b.cluster).map((m) => m.n_peaks.toLocaleString("en-US"));
    assert.deepEqual(r.shown, byCluster);
    assert.equal(r.back.reduce((a, m) => a + m.n_peaks, 0), r.n);
  });

  await step("measures: every number on the cards equals the backend measures, for each map", async () => {
    await page.keyboard.press("8");
    await page.waitForFunction(() => window.__ns.stageReady === "measures");
    for (const k of [0, 1, 2, 3]) {
      await page.locator("#map-pick button").nth(k).click();
      await page.waitForFunction((k) => window.__ns.measurePick.k === k, k);
      const r = await page.evaluate(() => ({ cards: [...document.querySelectorAll("#mcards .mcard .n")].map((e) => e.textContent),
        m: window.__ns.measurePick.m, hist: window.__ns.measurePick.hist, waffle: window.__ns.measurePick.waffle, check: document.querySelector("#measure-check").textContent }));
      assert.deepEqual(r.cards, [`${r.m.mean_duration_ms.toFixed(1)} ms`, `${r.m.occurrence_per_s.toFixed(1)} /s`, `${r.m.coverage_pct.toFixed(1)}%`]);
      assert.equal(r.hist.reduce((a, b) => a + b, 0), r.m.n_visits, "histogram counts every visit");
      assert.equal(r.waffle.reduce((a, b) => a + b, 0), 100);
      assert.ok(r.check.endsWith(`= ${r.m.coverage_pct.toFixed(1)}%`), r.check);
    }
  });

  await step("transitions: the arrows' percentages equal the backend's conditional probabilities", async () => {
    await page.keyboard.press("9");
    await page.waitForFunction(() => window.__ns.stageReady === "transitions");
    for (const k of [0, 2]) {
      await page.locator("#map-pick button").nth(k).click();
      await page.waitForFunction((k) => window.__ns.transPick.k === k, k);
      const r = await page.evaluate(() => ({ p: window.__ns.transPick, back: window.__ns.demo.transitions, labels: [...document.querySelectorAll(".trans-svg text")].map((t) => t.textContent) }));
      assert.deepEqual(r.p.probs, r.back.conditional[k]);
      [0, 1, 2, 3].filter((j) => j !== k).forEach((j) => assert.ok(r.labels.includes(`${(r.back.conditional[k][j] * 100).toFixed(0)}%`)));
    }
  });

  await step("CNN input: clicking a window shows that window's 4 x 512 one-hot rows", async () => {
    await page.keyboard.press("0");
    await page.waitForFunction(() => window.__ns.stageReady === "cnn");
    const box = await plotBox(page, "#cnn-windows");
    await page.mouse.click(box.x + box.width * (4.5 * 4 / 61), box.y + box.height / 2);
    await page.waitForFunction(() => window.__ns.cnnWindow.k === 4);
    const w = await page.evaluate(() => window.__ns.cnnWindow);
    assert.deepEqual(w.shape, [4, 512]);
  });

  await step("click inspector: waveform clicks sync both cursors and match the backend", async () => {
    await page.keyboard.press("7");
    await page.waitForFunction(() => window.__ns.stageReady === "timeline");
    await page.waitForTimeout(400);
    const box = await plotBox(page, "#wave");
    for (const fx of [0.2, 0.47, 0.81]) {
      const r = await clickCheck(page, box.x + box.width * fx, box.y + box.height * 0.3);
      assertSync(r);
    }
    await shot(page, "04_inspector");
  });

  await step("click inspector: timeline click gives the same result as the backend", async () => {
    const box = await plotBox(page, "#wave");
    const r = await clickCheck(page, box.x + box.width * 0.63, box.y + box.height * 0.95);
    assertSync(r);
  });

  await step("arrow keys step one sample", async () => {
    const i0 = await page.evaluate(() => window.__ns.cursor.i);
    await page.keyboard.press("ArrowRight");
    await page.waitForFunction((i0) => window.__ns.cursor.i === i0 + 1 && window.__ns.inspector.i === i0 + 1, i0);
    await page.keyboard.press("ArrowLeft");
    await page.waitForFunction((i0) => window.__ns.cursor.i === i0 && window.__ns.inspector.i === i0, i0);
    assert.equal(await page.evaluate(() => window.__ns.stageReady), "timeline", "arrows step samples, not stages, on step 6");
  });

  await step("Raw / Processed toggle keeps the cursor time", async () => {
    const before = await page.evaluate(() => window.__ns.cursorShapes());
    await page.click("#view-raw");
    await page.waitForFunction(() => window.__ns.viewMode === "raw");
    const raw = await page.evaluate(() => window.__ns.cursorShapes());
    await page.click("#view-proc");
    await page.waitForFunction(() => window.__ns.viewMode === "proc");
    const proc = await page.evaluate(() => window.__ns.cursorShapes());
    assert.deepEqual(raw, before);
    assert.deepEqual(proc, before);
  });

  await step("Show an example jumps to the preselected moment and explains it", async () => {
    await page.keyboard.press("1");
    await page.waitForFunction(() => window.__ns.stageReady === "recording");
    await page.click("#show-example");
    await page.waitForFunction(() => window.__ns.exampleShown !== undefined && window.__ns.inspector && window.__ns.inspector.i === window.__ns.demo.example_i);
    await page.waitForTimeout(700);
    const r = await page.evaluate(async () => {
      const ns = window.__ns;
      const back = await (await fetch(`/api/runs/demo/instant?i=${ns.demo.example_i}`)).json();
      return { back, sentence: document.querySelector("#insp-sentence").textContent, shapes: ns.cursorShapes(), t: ns.demo.t0 + ns.demo.example_i / ns.demo.fs,
        img: document.querySelector("#insp-map").getAttribute("src") };
    });
    assert.equal(r.sentence, r.back.sentence);
    assert.ok(r.shapes.every((s) => Math.abs(s.x - r.t) < 1e-9));
    assert.ok(r.img.includes(`i=${r.back.i}`));
    await shot(page, "05_show_example");
  });

  await step("epilepsy research page with no results file: pending, no metrics, charts or progress bars", async () => {
    await page.goto(`${BASE}#/research`);
    await page.waitForSelector("#cnn-results");
    await page.waitForTimeout(600);
    const st = await page.evaluate(() => {
      const epi = document.querySelector("#epilepsy-study");
      return { badge: [...epi.querySelectorAll("#epi-status")].map((e) => e.textContent), text: epi.innerText,
        plots: epi.querySelectorAll(".js-plotly-plot, canvas, svg.main-svg").length,
        bars: epi.querySelectorAll("progress, [role=progressbar], meter").length,
        jobs: epi.querySelectorAll("#jobs tr").length };
    });
    assert.ok(st.badge.length >= 1 && st.badge.every((b) => b === "Epilepsy training pending"));
    assert.equal(st.plots, 0);
    assert.equal(st.bars, 0);
    assert.equal(st.jobs, 0);
    const cnn = await page.locator("#cnn-results").innerText();
    assert.ok(!/\d/.test(cnn), `no numbers in the CNN results section: ${cnn}`);
    assert.ok(!/\b0\.\d|%/.test(st.text), "no metric-like numbers in the epilepsy section");
    await shot(page, "06_epilepsy_pending", true);
  });

  await step("no 'trained on epilepsy' wording anywhere", async () => {
    for (const r of ["", "#/demo", "#/research"]) {
      await page.goto(BASE + r);
      await page.waitForTimeout(800);
      const t = await page.evaluate(() => document.body.innerText.toLowerCase());
      assert.ok(!t.includes("trained on epilepsy"), r);
    }
  });

  await step("research: a compatible EDF runs through the real pipeline and returns maps and measures", async () => {
    await page.goto(`${BASE}#/research`);
    await page.waitForSelector("#edf-input", { state: "attached" });
    await page.setInputFiles("#edf-input", SAMPLE);
    await page.waitForSelector('#jobs tr[data-status="done"]', { timeout: 120000 });
    await page.click('#jobs button[data-job]');
    await page.waitForSelector("#job-output #measures-table");
    await page.waitForTimeout(800);
    const r = await page.evaluate(async () => {
      const run = window.__ns.researchRun;
      const back = await (await fetch(`/api/runs/${run.run_id}`)).json();
      const rows = [...document.querySelectorAll("#job-output #measures-table tbody tr")].map((tr) => [...tr.children].map((td) => td.textContent));
      return { back, rows, imgs: document.querySelectorAll("#job-output .pair img").length };
    });
    assert.equal(r.imgs, 8);
    r.back.measures.forEach((m, k) => {
      assert.equal(r.rows[k][1], `${m.mean_duration_ms.toFixed(1)} ms`);
      assert.equal(r.rows[k][2], `${m.occurrence_per_s.toFixed(1)} /s`);
      assert.equal(r.rows[k][3], `${m.coverage_pct.toFixed(1)}%`);
    });
    await shot(page, "07_research_outputs", true);
  });

  await step("research: an incompatible EDF is refused with a reason", async () => {
    const bad = path.join(SHOTS, "..", "tests", "fixtures", "missing_pz.edf");
    if (!fs.existsSync(bad)) throw new Error(`fixture missing: ${bad}`);
    await page.setInputFiles("#edf-input", bad);
    await page.waitForSelector('#jobs tr[data-status="incompatible"]');
    const t = await page.locator('#jobs tr[data-status="incompatible"]').innerText();
    assert.ok(t.includes("missing: Pz"), t);
  });

  await step("example CNN input on the research page", async () => {
    await page.click("#example-cnn-btn");
    await page.waitForFunction(() => window.__ns.cnnWindow && document.querySelector("#ex-window .main-svg"));
    await page.waitForTimeout(600);
    const cap = await page.locator("#example-caption").innerText();
    assert.ok(cap.includes("input format only"));
    const w = await page.evaluate(() => window.__ns.cnnWindow);
    assert.deepEqual(w.shape, [4, 512]);
    await page.locator("#cnn-input").screenshot({ path: path.join(SHOTS, "08_example_cnn_input.png") });
  });

  await step("results file present: cohort, training runs, held-out evaluation and curve appear", async () => {
    await page.goto(`${BASE_RESULTS}#/research`);
    await page.waitForSelector("#evaluation");
    await page.waitForSelector("#study-curve .main-svg");
    assert.equal(await page.locator("#epi-status").first().textContent(), "Epilepsy model evaluated on held-out patients");
    assert.ok(await page.locator("#cohort").count());
    assert.ok(await page.locator("#train-runs").count());
    await page.fill("#target-size", "200");
    assert.ok((await page.locator("#next-cohort-out").innerText()).includes("more"));
    await page.locator("#cnn-results").screenshot({ path: path.join(SHOTS, "09_results_fixture.png") });
  });

  await step("presentation mode at 1920x1080: demo sequence", async () => {
    const p2 = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    await waitReady(p2, `${BASE}#/demo`);
    await p2.waitForFunction(() => window.__ns.stageReady === "recording");
    await p2.keyboard.press("p");
    await p2.waitForFunction(() => document.body.classList.contains("presenting"));
    await p2.waitForTimeout(400);
    await p2.screenshot({ path: path.join(SHOTS, "10_presentation_demo.png") });
    await p2.click("#show-example");
    await p2.waitForFunction(() => window.__ns.inspector && window.__ns.inspector.i === window.__ns.demo.example_i);
    await p2.waitForTimeout(800);
    await p2.screenshot({ path: path.join(SHOTS, "11_presentation_example.png") });
    const vis = await p2.evaluate(() => { const r = document.querySelector("#insp-sentence").getBoundingClientRect(); return r.bottom <= window.innerHeight + 400; });
    assert.ok(vis);
    await p2.click('a[data-nav="research"]');
    await p2.waitForSelector("#example-cnn-btn");
    await p2.click("#example-cnn-btn");
    await p2.waitForFunction(() => window.__ns.cnnWindow && document.querySelector("#ex-window .main-svg"));
    await p2.waitForTimeout(600);
    await p2.locator("#cnn-input").scrollIntoViewIfNeeded();
    await p2.screenshot({ path: path.join(SHOTS, "12_presentation_cnn_input.png") });
    assert.ok(await p2.evaluate(() => document.body.classList.contains("presenting")));
    await p2.close();
  });

  await step("every demo step fits the screen at 1280x720 and 1920x1080 (no scrolling, visual and navigation visible)", async () => {
    const names = ["recording", "prepare", "snapshots", "peaks", "fit", "name", "timeline", "measures", "transitions", "cnn"];
    for (const [w, hgt] of [[1280, 720], [1920, 1080]]) {
      const p3 = await browser.newPage({ viewport: { width: w, height: hgt }, deviceScaleFactor: 1 });
      p3.on("pageerror", (e) => errors.push(e.message));
      await waitReady(p3, `${BASE}#/demo`);
      for (let k = 0; k < names.length; k++) {
        await p3.keyboard.press(String((k + 1) % 10));
        await p3.waitForFunction((id) => window.__ns.stageReady === id, names[k]);
        await p3.waitForTimeout(300);
        const m = await p3.evaluate(() => {
          const r = (sel) => { const e = document.querySelector(sel); if (!e) return null; const b = e.getBoundingClientRect(); return { top: b.top, bottom: b.bottom, left: b.left, right: b.right }; };
          return { scroll: document.documentElement.scrollHeight - innerHeight, hscroll: document.documentElement.scrollWidth - innerWidth, H: innerHeight, W: innerWidth,
            canvas: r("#canvas"), next: r("#stage-next"), prev: r("#stage-prev"), example: r("#show-example"), pills: [...document.querySelectorAll(".stage-pill")].map((e) => e.getBoundingClientRect().bottom) };
        });
        const tag = `${w}x${hgt} step ${k + 1}`;
        assert.ok(m.scroll <= 2, `${tag}: page scrolls ${m.scroll}px`);
        assert.ok(m.hscroll <= 2, `${tag}: horizontal scroll ${m.hscroll}px`);
        assert.ok(m.canvas.bottom <= m.H && m.canvas.bottom - m.canvas.top >= 380, `${tag}: main visual fits`);
        for (const b of [m.next, m.prev, m.example]) assert.ok(b.right <= m.W && b.bottom <= m.H && b.top >= 0, `${tag}: navigation visible`);
        assert.ok(new Set(m.pills.map(Math.round)).size === 1, `${tag}: step pills on one row`);
        await p3.screenshot({ path: path.join(SHOTS, `demo_${w}x${hgt}_${String(k + 1).padStart(2, "0")}_${names[k]}.png`) });
      }
      await p3.close();
    }
  });

  await step("no page errors", async () => { assert.deepEqual(errors, []); });
  await browser.close();
  const failed = results.filter((r) => r[0] === "FAIL");
  console.log(`\n${results.length - failed.length}/${results.length} browser checks passed`);
  process.exit(failed.length ? 1 : 0);
})();
