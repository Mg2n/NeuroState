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

  await step("demo opens from the bundle alone and walks through all steps", async () => {
    requests.length = 0;
    await page.click("#open-demo");
    await page.waitForFunction(() => window.__ns.stageReady === "recording");
    await page.waitForTimeout(400);
    await shot(page, "02_demo_recording");
    const names = { 2: "prepare", 3: "peaks", 4: "fit", 5: "name", 6: "timeline", 7: "measures", 8: "cnn" };
    for (const [k, id] of Object.entries(names)) {
      await page.keyboard.press(k);
      await page.waitForFunction((id) => window.__ns.stageReady === id, id);
      await page.waitForTimeout(500);
      await shot(page, `03_demo_${k}_${id}`, true);
    }
    assert.ok(!requests.some((u) => u.includes("/api/research")), "demo must not call the research pipeline");
    assert.ok(requests.some((u) => u.endsWith("/api/demo")));
    await page.keyboard.press("2");
    await page.waitForFunction(() => window.__ns.stageReady === "prepare");
    await page.locator(".how-btn").click();
    assert.ok(await page.locator(".howto-wrap.open .katex").count() > 0, "formula rendered with KaTeX");
  });

  await step("click inspector: waveform clicks sync both cursors and match the backend", async () => {
    await page.keyboard.press("6");
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

  await step("no page errors", async () => { assert.deepEqual(errors, []); });
  await browser.close();
  const failed = results.filter((r) => r[0] === "FAIL");
  console.log(`\n${results.length - failed.length}/${results.length} browser checks passed`);
  process.exit(failed.length ? 1 : 0);
})();
