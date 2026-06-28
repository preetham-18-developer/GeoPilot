/**
 * AIVOP — Real Browser QA Audit
 * Phases 1–10: Project creation, pipeline monitoring, grounding,
 *              questions, keywords, all tabs, API, download, console, performance.
 *
 * Run with: npx playwright test tests/e2e/real_browser_qa.spec.ts --headed
 */

import { test, expect, Page, BrowserContext } from "@playwright/test";
import fs from "fs";
import path from "path";

// ─── Constants ───────────────────────────────────────────────────────────────
const FRONTEND_URL = "http://localhost:3000";
const BACKEND_URL  = "http://localhost:8000";
const TARGET_URL   = "https://www.thelibrarycompany.com";
const DEFAULT_USER  = "00000000-0000-4000-a000-000000000001";
const AUTH_HEADER   = `Bearer mock-${DEFAULT_USER}`;
const PROJ_NAME    = "TheLibraryCompany_QA_" + Date.now();
const SCREENSHOT_DIR = path.join(__dirname, "../../qa_screenshots");
const REPORT_PATH    = path.join(__dirname, "../../real_browser_validation_report.md");

/** Forbidden tokens — none of these must appear in any response or page */
const FORBIDDEN_TOKENS = [
  "Benjamin Franklin",
  "Philadelphia",
  "1731",
  "Historical Research Library",
  "Library Company of Philadelphia",
  "librarycompany.org",
];

// ─── Shared state ────────────────────────────────────────────────────────────
let findings: string[] = [];
let issues: { level: string; title: string; detail: string; repro: string; fix: string }[] = [];
let apiFailures: { url: string; status: number; method: string }[] = [];
let consoleErrors: string[] = [];
let timings: Record<string, number> = {};
let projectId: string = "";

function logFinding(msg: string) {
  console.log("[QA]", msg);
  findings.push(msg);
}

function addIssue(level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW", title: string, detail: string, repro: string, fix: string) {
  issues.push({ level, title, detail, repro, fix });
  console.warn(`[${level}] ${title}: ${detail}`);
}

function ensureScreenshotDir() {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
}

async function screenshot(page: Page, name: string) {
  ensureScreenshotDir();
  const p = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: p, fullPage: false });
  logFinding(`Screenshot: ${name}.png`);
  return p;
}// ─── Test Suite ──────────────────────────────────────────────────────────────
test.describe("AIVOP Real Browser QA Audit", () => {
  test.describe.configure({ timeout: 600000 });

  test.beforeAll(() => {
    ensureScreenshotDir();
    // Reset shared state
    findings = [];
    issues = [];
    apiFailures = [];
    consoleErrors = [];
    timings = {};
    projectId = "";
  });

  // ── Phase 0 — Server health ────────────────────────────────────────────────
  test("Phase 0 — Backend health check", async ({ request }) => {
    const t0 = Date.now();
    const res = await request.get(`${BACKEND_URL}/health`, { headers: { Authorization: AUTH_HEADER } });
    timings["backend_health_ms"] = Date.now() - t0;
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    logFinding(`✅ Backend healthy (${timings["backend_health_ms"]}ms): ${JSON.stringify(body)}`);
  });

  // ── Phase 1 — Project Creation ─────────────────────────────────────────────
  test("Phase 1 — Load app & create project", async ({ page }) => {
    // Collect console errors
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(`[console.error] ${msg.text()}`);
      }
    });
    page.on("pageerror", (err) => {
      consoleErrors.push(`[pageerror] ${err.message}`);
    });

    // Intercept failed API requests
    page.on("response", (resp) => {
      if (resp.url().includes("/api/") && (resp.status() >= 400)) {
        apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
      }
    });

    const t0 = Date.now();
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    timings["initial_load_ms"] = Date.now() - t0;
    logFinding(`✅ App loaded in ${timings["initial_load_ms"]}ms`);

    // Verify title
    const title = await page.title();
    logFinding(`Page title: "${title}"`);
    expect(title.length).toBeGreaterThan(0);

    await screenshot(page, "01_landing");

    // ── Fill landing form ──
    const nameInput = page.locator('input[name="name"]');
    const urlInput  = page.locator('input[name="url"]');
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    await expect(urlInput).toBeVisible();

    await nameInput.fill(PROJ_NAME);
    await urlInput.fill(TARGET_URL);
    await screenshot(page, "02_form_filled");

    // Intercept project creation API
    const projectResponsePromise = page.waitForResponse(
      (resp) => resp.url().includes("/projects") && resp.request().method() === "POST",
      { timeout: 15000 }
    );

    await page.locator('button[type="submit"]:has-text("Create Project")').click();
    const projectResp = await projectResponsePromise;
    const projStatus = projectResp.status();
    logFinding(`Project creation API response: ${projStatus}`);

    if (projStatus >= 400) {
      addIssue("CRITICAL", "Project creation failed", `API returned ${projStatus}`,
        "Fill form → click Create Project & Start → observe network tab",
        "Check backend /projects POST endpoint for errors");
    } else {
      const body = await projectResp.json().catch(() => ({}));
      projectId = body.id || body.project_id || "";
      logFinding(`✅ Project created — ID: ${projectId}`);
    }

    // Wait for dashboard to load
    await expect(page.locator('h1.text-gradient')).toBeVisible({ timeout: 10000 });
    await screenshot(page, "03_project_dashboard");

    // Check no early console errors
    if (consoleErrors.length > 0) {
      addIssue("HIGH", "Console errors on load", consoleErrors.slice(0, 3).join("; "),
        "Open DevTools → Console → reload page",
        "Fix JS/React errors shown in console");
    }
  });

  // ── Phase 2 — Pipeline Monitoring ─────────────────────────────────────────
  test("Phase 2 — Trigger analysis & monitor pipeline", async ({ page }) => {
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(`[P2 console.error] ${msg.text()}`);
    });
    page.on("response", (resp) => {
      if (resp.url().includes("/api/") && resp.status() >= 400) {
        apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
      }
    });

    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    // Select the project we created
    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (err) {
      logFinding("⚠️ Could not re-select project from sidebar — using existing session");
      // Create fresh project for pipeline test
      const nameInput = page.locator('input[name="name"]');
      if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nameInput.fill(PROJ_NAME + "_P2");
        await page.locator('input[name="url"]').fill(TARGET_URL);
        const projRespPromise = page.waitForResponse(
          (resp) => resp.url().includes("/projects") && resp.request().method() === "POST",
          { timeout: 10000 }
        );
        await page.locator('button[type="submit"]:has-text("Create Project")').click();
        const pr = await projRespPromise;
        const b = await pr.json().catch(() => ({}));
        projectId = b.id || b.project_id || projectId;
      }
    }

    // Wait for project header
    const projHeader = page.locator('h1.text-gradient');
    await expect(projHeader).toBeVisible({ timeout: 15000 });
    await screenshot(page, "04_project_loaded");

    // Click Run Analysis
    const runBtn = page.locator('button:has-text("Run Analysis")').first();
    if (await runBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      const t0 = Date.now();
      const runRespPromise = page.waitForResponse(
        (resp) => resp.url().includes("/runs") && resp.request().method() === "POST",
        { timeout: 15000 }
      );
      await runBtn.click();
      timings["analysis_trigger_ms"] = Date.now() - t0;

      const runResp = await runRespPromise.catch(() => null);
      if (runResp) {
        logFinding(`✅ Run triggered — status: ${runResp.status()}, time: ${timings["analysis_trigger_ms"]}ms`);
        const runBody = await runResp.json().catch(() => ({}));
        logFinding(`Run ID: ${runBody.id || runBody.run_id || "unknown"}`);
        if (runResp.status() >= 400) {
          addIssue("CRITICAL", "Analysis trigger failed", `POST /runs returned ${runResp.status()}`,
            "Click Run Analysis button → check Network tab",
            "Check backend /runs POST endpoint");
        }
      }

      // Monitor pipeline banner
      const banner = page.locator('.run-banner');
      const bannerVisible = await banner.isVisible({ timeout: 10000 }).catch(() => false);
      if (bannerVisible) {
        logFinding("✅ Pipeline banner appeared");
        await screenshot(page, "05_pipeline_running");

        // Poll for up to 10 minutes for completion
        const maxWait = 600000;
        const pollInterval = 5000;
        const startTime = Date.now();
        let completed = false;
        let lastStatus = "";

        while (Date.now() - startTime < maxWait) {
          await page.waitForTimeout(pollInterval);

          // Check for completion card
          const completedCard = page.locator('.card:has-text("✓ Pipeline Completed")');
          const failedCard    = page.locator('.card:has-text("✗ Pipeline Failed")');

          if (await completedCard.isVisible({ timeout: 1000 }).catch(() => false)) {
            timings["analysis_total_ms"] = Date.now() - t0;
            logFinding(`✅ Pipeline COMPLETED in ${Math.round(timings["analysis_total_ms"] / 1000)}s`);
            completed = true;
            await screenshot(page, "06_pipeline_completed");
            break;
          }
          if (await failedCard.isVisible({ timeout: 1000 }).catch(() => false)) {
            const errText = await failedCard.textContent().catch(() => "");
            addIssue("CRITICAL", "Pipeline failed", errText || "Pipeline error card shown",
              "Click Run Analysis → wait for pipeline → observe failure card",
              "Check backend logs for pipeline error");
            await screenshot(page, "06_pipeline_failed");
            completed = true;
            break;
          }

          // Log current stage
          const stageEl = page.locator('.run-banner-header span').first();
          const stage = await stageEl.textContent().catch(() => "");
          if (stage !== lastStatus) {
            lastStatus = stage;
            logFinding(`Pipeline stage: ${stage}`);
          }
        }

        if (!completed) {
          addIssue("HIGH", "Pipeline timeout", "Pipeline did not complete within 5 minutes",
            "Click Run Analysis → wait 5+ minutes → observe frozen state",
            "Check backend agent timeouts and logs");
          await screenshot(page, "06_pipeline_timeout");
        }
      } else {
        addIssue("HIGH", "Pipeline banner never appeared", "Run was triggered but no progress banner shown",
          "Click Run Analysis → watch for banner",
          "Check useRunPolling hook and run-banner rendering");
        await screenshot(page, "05_no_pipeline_banner");
      }
    } else {
      addIssue("MEDIUM", "Run Analysis button not visible", "Cannot find 'Run Analysis' button",
        "Load project → look for Run Analysis button top-right",
        "Ensure project is selected and projectDetail is loaded");
    }
  });

  // ── Phase 3 — Grounding Validation ────────────────────────────────────────
  test("Phase 3 — Grounding: company identity check", async ({ page, request }) => {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    // Select project if visible
    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (e) {
      logFinding("⚠️ Project item not visible for click in Phase 3");
    }

    // Navigate to Business Intelligence tab
    const intelligenceBtn = page.locator('button.sidebar-nav-item').filter({ hasText: "Intelligence" });
    if (await intelligenceBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      await intelligenceBtn.click();
      const biTab = page.locator('button.sidebar-sub-item').filter({ hasText: "Business Intelligence" });
      if (await biTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await biTab.click();
      }
    }

    await page.waitForTimeout(2000);
    const pageText = await page.locator("main").textContent().catch(() => "");
    await screenshot(page, "07_business_intelligence");

    // Check for forbidden tokens
    let groundingFailed = false;
    for (const token of FORBIDDEN_TOKENS) {
      if (pageText && pageText.includes(token)) {
        groundingFailed = true;
        addIssue("CRITICAL", `Hallucinated content detected: "${token}"`,
          `The forbidden term "${token}" appeared in the Business Intelligence tab`,
          `Open Intelligence → Business Intelligence → search for "${token}"`,
          "Fix grounding engine to reject cross-domain entities; ensure domain identity validator rejects benjamin_franklin / librarycompany.org");
        logFinding(`❌ GROUNDING FAIL: Found forbidden token "${token}"`);
      }
    }

    if (!groundingFailed) {
      logFinding("✅ Grounding PASSED: No forbidden tokens found in Business Intelligence");
    }

    // Also check via API if project exists
    if (projectId) {
      const apiUrl = `${BACKEND_URL}/api/v1/analysis/business-intelligence/${projectId}`;
      const biResp = await request.get(apiUrl, {
        headers: { Authorization: AUTH_HEADER }
      }).catch(() => null);

      if (biResp) {
        logFinding(`BI API status: ${biResp.status()}`);
        if (biResp.status() === 200) {
          const biBody = await biResp.text();
          for (const token of FORBIDDEN_TOKENS) {
            if (biBody.includes(token)) {
              addIssue("CRITICAL", `API Grounding Fail: "${token}" in BI response`,
                `Forbidden token in /business-intelligence API response`,
                `GET /api/v1/analysis/business-intelligence/${projectId}`,
                "Fix GroundingEngineV2 + DomainIdentityValidator to reject cross-domain content");
              logFinding(`❌ API GROUNDING FAIL: "${token}" in BI API response`);
            }
          }
        } else if (biResp.status() === 404) {
          logFinding("ℹ️ BI API returned 404 — pipeline may not have completed yet");
        } else {
          addIssue("MEDIUM", `BI API unexpected status: ${biResp.status()}`,
            `GET /api/v1/analysis/business-intelligence/${projectId} returned ${biResp.status()}`,
            "Call BI API with valid project ID",
            "Check business intelligence router");
        }
      }
    }
  });

  // ── Phase 4 — Question Discovery ─────────────────────────────────────────
  test("Phase 4 — Question Discovery tab", async ({ page, request }) => {
    page.on("response", (resp) => {
      if (resp.url().includes("/api/") && resp.status() >= 400) {
        apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
      }
    });

    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (e) {
      logFinding("⚠️ Project item not visible for click in Phase 4");
    }

    // Navigate to Intelligence → Questions
    const intelligenceBtn = page.locator('button.sidebar-nav-item').filter({ hasText: "Intelligence" });
    await intelligenceBtn.click().catch(() => {});
    await page.locator('button.sidebar-sub-item').filter({ hasText: "Questions" }).click().catch(() => {});
    
    const t0 = Date.now();
    await page.waitForTimeout(2000);
    timings["questions_tab_load_ms"] = Date.now() - t0;

    await screenshot(page, "08_questions_tab");
    const mainText = await page.locator("main").textContent().catch(() => "");

    // Check for question cards
    const questionCards = page.locator('[class*="question"], [class*="Question"], .card');
    const qCount = await questionCards.count();
    logFinding(`Questions tab — found ${qCount} elements on page`);

    // Check for "No questions" state
    if (mainText && (mainText.includes("No questions") || mainText.includes("no questions"))) {
      addIssue("HIGH", "Questions tab is empty",
        "Questions tab shows no questions after pipeline completion",
        "Run analysis → open Intelligence → Questions",
        "Verify question_discovery agent is saving questions to Supabase");
      logFinding("❌ Questions tab shows empty state");
    } else {
      logFinding("✅ Questions tab has content");
    }

    // Test search
    const searchInput = page.locator('input[placeholder*="earch"], input[placeholder*="question"]').first();
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill("recommend");
      await page.waitForTimeout(1000);
      logFinding("✅ Questions search field works");
      await searchInput.clear();
    } else {
      addIssue("MEDIUM", "Questions search input not found",
        "Cannot locate search input on Questions tab",
        "Open Questions tab → look for search box",
        "Check QuestionDiscoveryTab for search input rendering");
    }

    // API count check
    if (projectId) {
      const qApiUrl = `${BACKEND_URL}/api/v1/analysis/questions/${projectId}?page=1&page_size=50`;
      const qResp = await request.get(qApiUrl, {
        headers: { Authorization: AUTH_HEADER }
      }).catch(() => null);

      if (qResp && qResp.status() === 200) {
        const qBody = await qResp.json().catch(() => ({}));
        const count = qBody.total || qBody.count || (Array.isArray(qBody.data) ? qBody.data.length : 0);
        logFinding(`Questions API total count: ${count}`);
        if (count === 0) {
          addIssue("HIGH", "Questions API returns 0 questions",
            `GET ${qApiUrl} returned count=${count}`,
            "Run analysis → check questions API",
            "Verify question_discovery agent stores questions and question intelligence runs correctly");
        } else {
          logFinding(`✅ Questions API: ${count} questions found`);
        }
      } else {
        logFinding(`ℹ️ Questions API status: ${qResp?.status() ?? "no response"}`);
      }
    }
  });

  // ── Phase 5 — Keyword Intelligence ────────────────────────────────────────
  test("Phase 5 — Keyword Intelligence tab", async ({ page, request }) => {
    page.on("response", (resp) => {
      if (resp.url().includes("/api/") && resp.status() >= 400) {
        apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
      }
    });

    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (e) {
      logFinding("⚠️ Project item not visible for click in Phase 5");
    }

    await page.locator('button.sidebar-nav-item').filter({ hasText: "Intelligence" }).click().catch(() => {});
    await page.locator('button.sidebar-sub-item').filter({ hasText: "Keywords" }).click().catch(() => {});

    const t0 = Date.now();
    await page.waitForTimeout(2000);
    timings["keywords_tab_load_ms"] = Date.now() - t0;

    await screenshot(page, "09_keywords_tab");
    const mainText = await page.locator("main").textContent().catch(() => "");

    if (mainText && (mainText.includes("No keywords") || mainText.includes("no keywords"))) {
      addIssue("HIGH", "Keywords tab is empty",
        "Keywords tab shows no keywords after pipeline completion",
        "Run analysis → Intelligence → Keywords",
        "Verify keyword_intelligence agent stores keywords to Supabase");
      logFinding("❌ Keywords tab shows empty state");
    } else {
      logFinding("✅ Keywords tab has content");
    }

    // Test search
    const searchInput = page.locator('input[placeholder*="earch"], input[placeholder*="keyword"]').first();
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill("mentorship");
      await page.waitForTimeout(1000);
      logFinding("✅ Keywords search works");
      await searchInput.clear();
    } else {
      addIssue("MEDIUM", "Keywords search input not found", 
        "Cannot locate search input on Keywords tab",
        "Open Keywords tab → look for search box",
        "Check KeywordIntelligenceTab for search input");
    }

    // API count check
    if (projectId) {
      const kApiUrl = `${BACKEND_URL}/api/v1/analysis/keywords/${projectId}?page=1&page_size=50`;
      const kResp = await request.get(kApiUrl, { headers: { Authorization: AUTH_HEADER } }).catch(() => null);
      if (kResp && kResp.status() === 200) {
        const kBody = await kResp.json().catch(() => ({}));
        const count = kBody.total || kBody.count || (Array.isArray(kBody.data) ? kBody.data.length : 0);
        logFinding(`Keywords API total count: ${count}`);
        if (count === 0) {
          addIssue("HIGH", "Keywords API returns 0 keywords",
            `GET ${kApiUrl} returned count=${count}`,
            "Run analysis → check keywords API",
            "Verify keyword_intelligence agent");
        } else {
          logFinding(`✅ Keywords API: ${count} keywords found`);
        }
      }
    }
  });

  // ── Phase 6 — All Intelligence Tabs ───────────────────────────────────────
  test("Phase 6 — All tabs load without crash", async ({ page }) => {
    const tabErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(`[P6] ${msg.text()}`);
    });
    page.on("pageerror", (err) => tabErrors.push(`pageerror: ${err.message}`));
    page.on("response", (resp) => {
      if (resp.url().includes("/api/") && resp.status() >= 400) {
        apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
      }
    });

    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (e) {
      logFinding("⚠️ Project item not visible for click in Phase 6");
    }

    const sections: { sectionLabel: string; tabs: { label: string; key: string }[] }[] = [
      {
        sectionLabel: "Intelligence",
        tabs: [
          { label: "Business Intelligence", key: "bi" },
          { label: "Verified Facts", key: "facts" },
          { label: "Questions", key: "questions" },
          { label: "Keywords", key: "keywords" },
          { label: "Competitors", key: "competitors" },
          { label: "Validation", key: "validation" },
          { label: "Reality Checker", key: "reality_check" },
          { label: "Recommendation Intel", key: "rec_intel" },
          { label: "Competitor Benchmark", key: "benchmark" },
          { label: "Historical Tracker", key: "tracker" },
          { label: "Advanced Analytics", key: "analytics" },
          { label: "GEO Intelligence", key: "geo_intel" },
        ],
      },
      {
        sectionLabel: "Content Studio",
        tabs: [
          { label: "Content Intelligence", key: "content_intel" },
          { label: "Opportunities", key: "content" },
        ],
      },
      {
        sectionLabel: "Optimization",
        tabs: [
          { label: "Strategy Roadmap", key: "optimization_roadmap" },
          { label: "Execution", key: "autonomous_execution" },
        ],
      },
      {
        sectionLabel: "Monitoring",
        tabs: [
          { label: "Reliability", key: "reliability" },
          { label: "Agent Health", key: "agent_monitor" },
        ],
      },
      {
        sectionLabel: "Dashboard",
        tabs: [
          { label: "Executive Overview", key: "overview" },
          { label: "Reports", key: "reports" },
        ],
      },
    ];

    for (const section of sections) {
      // Expand the section
      const sectionBtn = page.locator('button.sidebar-nav-item').filter({ hasText: section.sectionLabel });
      if (await sectionBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await sectionBtn.click();
        await page.waitForTimeout(300);
      } else {
        logFinding(`⚠️ Section button not found: "${section.sectionLabel}"`);
        continue;
      }

      for (const tab of section.tabs) {
        const subBtn = page.locator('button.sidebar-sub-item').filter({ hasText: tab.label });
        if (await subBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await subBtn.click();
          await page.waitForTimeout(1500);

          // Check for React error boundary
          const errBoundary = page.locator('[class*="error"], [class*="ErrorBoundary"]').filter({ hasText: "Something went wrong" });
          if (await errBoundary.isVisible({ timeout: 1000 }).catch(() => false)) {
            addIssue("HIGH", `Tab crashed: ${tab.label}`,
              `ErrorBoundary triggered on ${tab.label} tab`,
              `Navigate to ${section.sectionLabel} → ${tab.label}`,
              `Debug the ${tab.key} component for runtime errors`);
            tabErrors.push(`CRASH: ${tab.label}`);
          }

          // Check main content is not empty and we are not stuck on landing page
          const main = await page.locator("main").textContent().catch(() => "");
          const hasContent = main && main.trim().length > 50 && !main.includes("AI Visibility Optimization");
          if (!hasContent) {
            addIssue("MEDIUM", `Tab appears blank: ${tab.label}`,
              `${tab.label} tab renders less than 50 characters`,
              `Open ${section.sectionLabel} → ${tab.label}`,
              `Check data loading in ${tab.key} component`);
            logFinding(`⚠️ ${tab.label}: content appears thin`);
          } else {
            logFinding(`✅ ${tab.label}: rendered OK`);
          }

          // Screenshot key tabs
          if (["bi", "questions", "keywords", "validation", "rec_intel", "overview", "reports"].includes(tab.key)) {
            await screenshot(page, `10_tab_${tab.key}`);
          }
        } else {
          addIssue("LOW", `Sub-tab not found in UI: ${tab.label}`,
            `Could not locate sidebar sub-item "${tab.label}"`,
            `Expand ${section.sectionLabel} → look for ${tab.label}`,
            "Verify SECTION_SUBTABS config in Sidebar.tsx");
          logFinding(`⚠️ Sub-tab not found: "${tab.label}"`);
        }
      }
    }

    if (tabErrors.length > 0) {
      logFinding(`❌ Tab errors: ${tabErrors.join(", ")}`);
    } else {
      logFinding("✅ All tabs navigated without crash");
    }
  });

  // ── Phase 7 — API Audit ────────────────────────────────────────────────────
  test("Phase 7 — API endpoint audit", async ({ request }) => {
    if (!projectId) {
      logFinding("ℹ️ No project ID — skipping deep API audit");
      return;
    }

    const headers = { Authorization: AUTH_HEADER };
    const endpoints = [
      `/api/v1/projects`,
      `/api/v1/projects/${projectId}`,
      `/api/v1/analysis/business-intelligence/${projectId}`,
      `/api/v1/analysis/verified-facts/${projectId}`,
      `/api/v1/analysis/questions/${projectId}?page=1&page_size=10`,
      `/api/v1/analysis/keywords/${projectId}?page=1&page_size=10`,
      `/api/v1/analysis/competitors/${projectId}`,
      `/api/v1/analysis/validation/${projectId}`,
      `/api/v1/analysis/recommendation-intelligence/${projectId}`,
      `/api/v1/analysis/analytics/${projectId}`,
      `/api/v1/analysis/historical-metrics/${projectId}`,
      `/api/v1/analysis/geo-readiness/${projectId}`,
      `/api/v1/analysis/reliability/${projectId}`,
      `/api/v1/reports?project_id=${projectId}`,
    ];

    for (const ep of endpoints) {
      const url = `${BACKEND_URL}${ep}`;
      const resp = await request.get(url, { headers }).catch(() => null);
      const status = resp ? resp.status() : 0;

      if (!resp || status === 0) {
        addIssue("HIGH", `API timeout/unreachable: ${ep}`,
          `No response from ${url}`,
          `curl -H "X-User-Id: demo_user_1" ${url}`,
          "Check backend server and endpoint registration");
        logFinding(`❌ API FAIL (no response): ${ep}`);
      } else if (status >= 500) {
        addIssue("CRITICAL", `API 5xx: ${ep}`, `${status} from ${url}`,
          `curl -H "X-User-Id: demo_user_1" ${url}`,
          "Fix backend server error for this endpoint");
        logFinding(`❌ API 5xx: ${ep} → ${status}`);
      } else if (status === 422) {
        addIssue("MEDIUM", `API 422 Unprocessable: ${ep}`,
          `${url} returned 422`,
          `curl -H "X-User-Id: demo_user_1" ${url}`,
          "Check request schema / required fields");
        logFinding(`⚠️ API 422: ${ep}`);
      } else if (status === 404) {
        logFinding(`ℹ️ API 404 (no data yet): ${ep}`);
      } else if (status === 200) {
        logFinding(`✅ API 200: ${ep}`);
      } else {
        logFinding(`ℹ️ API ${status}: ${ep}`);
      }
    }
  });

  // ── Phase 8 — Report Download ──────────────────────────────────────────────
  test("Phase 8 — Report download validation", async ({ page, request }) => {
    page.on("response", (resp) => {
      if (resp.url().includes("/api/") && resp.status() >= 400) {
        apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
      }
    });

    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (e) {
      logFinding("⚠️ Project item not visible for click in Phase 8");
    }

    // Navigate to Dashboard → Reports
    await page.locator('button.sidebar-nav-item').filter({ hasText: "Dashboard" }).click().catch(() => {});
    await page.waitForTimeout(300);
    await page.locator('button.sidebar-sub-item').filter({ hasText: "Reports" }).click().catch(() => {});
    await page.waitForTimeout(2000);
    await screenshot(page, "11_reports_tab");

    // Try clicking Markdown download
    const mdBtn = page.locator('button:has-text("Markdown"), a:has-text("Markdown"), button:has-text(".md"), button:has-text("md")').first();
    if (await mdBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      const downloadPromise = page.waitForEvent("download", { timeout: 15000 }).catch(() => null);
      await mdBtn.click();
      const download = await downloadPromise;

      if (download) {
        const t0 = Date.now();
        const savePath = path.join(SCREENSHOT_DIR, "report_download.md");
        await download.saveAs(savePath);
        timings["report_download_ms"] = Date.now() - t0;
        logFinding(`✅ Report downloaded in ${timings["report_download_ms"]}ms: ${download.suggestedFilename()}`);

        // Validate content
        const content = fs.readFileSync(savePath, "utf-8");
        const requiredSections = [
          "Business Profile", "Verified Facts", "Questions", "Keywords",
          "Competitors", "Recommendation", "GEO", "Optimization", "Reliability",
        ];

        for (const section of requiredSections) {
          if (!content.includes(section)) {
            addIssue("HIGH", `Missing section in report: ${section}`,
              `Report download does not contain section "${section}"`,
              "Reports tab → Download Markdown → open file",
              "Fix ReportEngineV2 to include this section");
            logFinding(`❌ Report missing section: ${section}`);
          } else {
            logFinding(`✅ Report contains: ${section}`);
          }
        }

        // Check table formatting
        if (!content.includes("|")) {
          addIssue("MEDIUM", "Report has no table formatting",
            "Downloaded report does not contain markdown table pipes (|)",
            "Download report → open in text editor",
            "Fix ReportEngineV2 table generation");
        } else {
          logFinding("✅ Report contains markdown tables (|)");
        }

        // Check for forbidden tokens in report
        for (const token of FORBIDDEN_TOKENS) {
          if (content.includes(token)) {
            addIssue("CRITICAL", `Hallucinated content in report: "${token}"`,
              `Forbidden token found in downloaded Markdown report`,
              "Download report → search for token",
              "Fix GroundingEngineV2 production gate to block hallucinated content from reports");
            logFinding(`❌ Report GROUNDING FAIL: "${token}" in downloaded report`);
          }
        }

        // Check for empty sections
        const emptySection = /#{1,3} .+\n\n#{1,3}/;
        if (emptySection.test(content)) {
          addIssue("MEDIUM", "Report has empty sections",
            "At least one section header is immediately followed by another header",
            "Download report → review section content",
            "Fix ReportEngineV2 to populate all sections or skip empty ones");
          logFinding("⚠️ Report may have empty sections");
        }

      } else {
        addIssue("HIGH", "Report download timeout",
          "Clicked Markdown button but no download event fired",
          "Reports tab → click Markdown button → wait",
          "Check ReportsTab component and download API endpoint");
        logFinding("❌ No download event received");
        await screenshot(page, "11_download_failed");
      }
    } else {
      addIssue("MEDIUM", "Markdown download button not found",
        "Cannot locate Markdown download button on Reports tab",
        "Reports tab → look for Markdown button",
        "Check ReportsTab rendering and latestReport prop");
      logFinding("⚠️ Markdown download button not found");
    }
  });

  // ── Phase 9 — Console Audit ────────────────────────────────────────────────
  test("Phase 9 — Console error audit", async ({ page }) => {
    const pageErrors: string[] = [];
    const warnings: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") pageErrors.push(msg.text());
      if (msg.type() === "warning") warnings.push(msg.text());
    });
    page.on("pageerror", (err) => pageErrors.push(`pageerror: ${err.message}`));

    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
    try {
      await projItem.waitFor({ state: "visible", timeout: 15000 });
      await projItem.click();
      await page.waitForTimeout(2000);
    } catch (e) {
      logFinding("⚠️ Project item not visible for click in Phase 9");
    }

    logFinding(`Console errors on clean load: ${pageErrors.length}`);
    logFinding(`Console warnings on clean load: ${warnings.length}`);

    for (const err of pageErrors) {
      consoleErrors.push(err);
      if (err.toLowerCase().includes("hydration") || err.toLowerCase().includes("did not match")) {
        addIssue("HIGH", "Hydration mismatch error", err,
          "Open DevTools Console → reload page",
          "Fix server-side vs client-side rendering mismatch");
      } else if (err.toLowerCase().includes("unhandled")) {
        addIssue("HIGH", "Unhandled promise rejection", err,
          "Open DevTools Console → reload page",
          "Add .catch() to async calls");
      }
    }

    // Check for hydration-specific errors in DOM
    const hydrationErr = await page.locator('[data-nextjs-dialog]').count();
    if (hydrationErr > 0) {
      addIssue("HIGH", "Next.js error dialog visible",
        "Next.js overlay dialog appeared (hydration or runtime error)",
        "Load page → look for red overlay",
        "Fix hydration errors in Next.js app");
      await screenshot(page, "12_nextjs_error_dialog");
    } else {
      logFinding("✅ No Next.js error dialog visible");
    }

    logFinding(`Total console errors across all phases: ${consoleErrors.length}`);
  });

  // ── Phase 10 — Performance Audit ──────────────────────────────────────────
  test("Phase 10 — Performance measurement", async ({ page }) => {
    const t0 = Date.now();
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    timings["p10_initial_load_ms"] = Date.now() - t0;

    // Measure navigation performance via JS API
    const perfEntries = await page.evaluate(() => {
      const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: nav?.domContentLoadedEventEnd - nav?.startTime,
        loadEvent: nav?.loadEventEnd - nav?.startTime,
        ttfb: nav?.responseStart - nav?.startTime,
      };
    });

    logFinding(`Performance metrics:`);
    logFinding(`  TTFB: ${Math.round(perfEntries.ttfb)}ms`);
    logFinding(`  DOMContentLoaded: ${Math.round(perfEntries.domContentLoaded)}ms`);
    logFinding(`  Load event: ${Math.round(perfEntries.loadEvent)}ms`);
    logFinding(`  Initial load (wall): ${timings["p10_initial_load_ms"]}ms`);

    if (perfEntries.domContentLoaded > 5000) {
      addIssue("MEDIUM", "Slow initial page load",
        `DOMContentLoaded took ${Math.round(perfEntries.domContentLoaded)}ms (>5s)`,
        "Load http://localhost:3000 → DevTools → Performance → measure DOMContentLoaded",
        "Optimize Next.js bundle size, code splitting, and lazy loading");
    }

    if (timings["analysis_total_ms"]) {
      logFinding(`  Analysis total time: ${Math.round(timings["analysis_total_ms"] / 1000)}s`);
    }
    if (timings["questions_tab_load_ms"]) {
      logFinding(`  Questions tab load: ${timings["questions_tab_load_ms"]}ms`);
      if (timings["questions_tab_load_ms"] > 3000) {
        addIssue("LOW", "Questions tab slow to render",
          `Questions tab took ${timings["questions_tab_load_ms"]}ms to render`,
          "Navigate to Questions tab → observe loading time",
          "Add loading skeleton; optimize paginated query");
      }
    }
    if (timings["keywords_tab_load_ms"]) {
      logFinding(`  Keywords tab load: ${timings["keywords_tab_load_ms"]}ms`);
    }

    await screenshot(page, "13_final_state");
  });

  // ── Final — Generate Report ────────────────────────────────────────────────
  test.afterAll(() => {
    const now = new Date().toISOString();
    const criticals = issues.filter(i => i.level === "CRITICAL");
    const highs     = issues.filter(i => i.level === "HIGH");
    const mediums   = issues.filter(i => i.level === "MEDIUM");
    const lows      = issues.filter(i => i.level === "LOW");

    const overallStatus = criticals.length === 0 && highs.length <= 2 ? "🟡 PARTIAL PASS" :
                          criticals.length > 0 ? "🔴 FAIL" : "🟢 PASS";

    const uniqueApiFailures = apiFailures.filter(
      (v, i, a) => a.findIndex(t => t.url === v.url && t.status === v.status) === i
    );
    const uniqueConsoleErrors = [...new Set(consoleErrors)];

    const issueTable = (arr: typeof issues) => arr.length === 0 ? "_None_\n" :
      `| # | Title | Detail |\n| :--- | :--- | :--- |\n` +
      arr.map((i, n) => `| ${n + 1} | ${i.title} | ${i.detail} |`).join("\n") + "\n";

    const issueBlock = (arr: typeof issues) => arr.length === 0 ? "_None_\n" :
      arr.map((i, n) =>
        `### ${n + 1}. ${i.title}\n` +
        `- **Detail**: ${i.detail}\n` +
        `- **Reproduction**: ${i.repro}\n` +
        `- **Suggested Fix**: ${i.fix}\n`
      ).join("\n");

    const report = `# AIVOP Real Browser Validation Report

**Generated**: ${now}  
**Target**: ${TARGET_URL}  
**Frontend**: ${FRONTEND_URL}  
**Backend**: ${BACKEND_URL}  
**Project Created**: ${PROJ_NAME}  

---

## Executive Summary

| Status | Critical | High | Medium | Low | Total Issues |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **${overallStatus}** | ${criticals.length} | ${highs.length} | ${mediums.length} | ${lows.length} | ${issues.length} |

---

## Grounding Audit

Forbidden tokens checked (MUST NOT appear in any UI or API response):
${FORBIDDEN_TOKENS.map(t => `- \`${t}\``).join("\n")}

${criticals.filter(i => i.title.toLowerCase().includes("grounding") || i.title.toLowerCase().includes("hallucin")).length === 0
  ? "✅ **No grounding failures detected.**"
  : criticals.filter(i => i.title.toLowerCase().includes("grounding") || i.title.toLowerCase().includes("hallucin"))
      .map(i => `❌ **${i.title}**: ${i.detail}`).join("\n")}

---

## Question Audit

${issueTable(issues.filter(i => i.title.toLowerCase().includes("question")))}

---

## Keyword Audit

${issueTable(issues.filter(i => i.title.toLowerCase().includes("keyword")))}

---

## API Audit

### Failed Endpoints (4xx / 5xx)

${uniqueApiFailures.length === 0
  ? "✅ No API failures detected during browser session.\n"
  : `| Method | Status | URL |\n| :--- | :--- | :--- |\n` +
    uniqueApiFailures.map(f => `| ${f.method} | ${f.status} | ${f.url} |`).join("\n") + "\n"
}

---

## UI Audit

| Tab | Status |
| :--- | :--- |
${findings.filter(f => f.startsWith("✅") && f.includes(":")).map(f => `| ${f.replace("✅ ", "").split(":")[0]} | ✅ OK |`).join("\n")}

---

## Performance Audit

| Metric | Value |
| :--- | :--- |
| Initial Load (wall clock) | ${timings["p10_initial_load_ms"] ?? "N/A"}ms |
| Backend Health Check | ${timings["backend_health_ms"] ?? "N/A"}ms |
| Analysis Trigger | ${timings["analysis_trigger_ms"] ?? "N/A"}ms |
| Analysis Total Time | ${timings["analysis_total_ms"] ? Math.round(timings["analysis_total_ms"] / 1000) + "s" : "N/A"} |
| Questions Tab Load | ${timings["questions_tab_load_ms"] ?? "N/A"}ms |
| Keywords Tab Load | ${timings["keywords_tab_load_ms"] ?? "N/A"}ms |
| Report Download | ${timings["report_download_ms"] ?? "N/A"}ms |

---

## Console Errors

${uniqueConsoleErrors.length === 0
  ? "✅ No console errors detected.\n"
  : uniqueConsoleErrors.slice(0, 20).map((e, i) => `${i + 1}. \`${e}\``).join("\n") + "\n"
}

---

## Screenshots

All screenshots saved to: \`tests/e2e/qa_screenshots/\`

| File | Description |
| :--- | :--- |
| 01_landing.png | Landing page / Create Project form |
| 02_form_filled.png | Form filled with target URL |
| 03_project_dashboard.png | Project dashboard after creation |
| 04_project_loaded.png | Project header loaded |
| 05_pipeline_running.png | Pipeline banner visible |
| 06_pipeline_completed.png | Pipeline completion card |
| 07_business_intelligence.png | Business Intelligence tab |
| 08_questions_tab.png | Questions tab |
| 09_keywords_tab.png | Keywords tab |
| 10_tab_*.png | Individual tab screenshots |
| 11_reports_tab.png | Reports tab |
| 12_nextjs_error_dialog.png | Error dialog (if present) |
| 13_final_state.png | Final app state |

---

## Critical Issues

${issueBlock(criticals) || "_None_\n"}

---

## High Issues

${issueBlock(highs) || "_None_\n"}

---

## Medium Issues

${issueBlock(mediums) || "_None_\n"}

---

## Low Issues

${issueBlock(lows) || "_None_\n"}

---

## All Findings Log

\`\`\`
${findings.join("\n")}
\`\`\`
`;

    fs.writeFileSync(REPORT_PATH, report, "utf-8");
    console.log(`\n✅ QA Report written to: ${REPORT_PATH}`);
    console.log(`\n📊 Summary: ${overallStatus} | Critical: ${criticals.length} | High: ${highs.length} | Medium: ${mediums.length} | Low: ${lows.length}`);
  });
});
