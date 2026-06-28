# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: real_browser_qa.spec.ts >> AIVOP Real Browser QA Audit >> Phase 4 — Question Discovery tab
- Location: tests\e2e\real_browser_qa.spec.ts:375:7

# Error details

```
Test timeout of 600000ms exceeded.
```

```
Error: page.waitForTimeout: Target page, context or browser has been closed
```

# Test source

```ts
  300 | 
  301 |     // Select project if visible
  302 |     const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
  303 |     try {
  304 |       await projItem.waitFor({ state: "visible", timeout: 15000 });
  305 |       await projItem.click();
  306 |       await page.waitForTimeout(2000);
  307 |     } catch (e) {
  308 |       logFinding("⚠️ Project item not visible for click in Phase 3");
  309 |     }
  310 | 
  311 |     // Navigate to Business Intelligence tab
  312 |     const intelligenceBtn = page.locator('button.sidebar-nav-item').filter({ hasText: "Intelligence" });
  313 |     if (await intelligenceBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
  314 |       await intelligenceBtn.click();
  315 |       const biTab = page.locator('button.sidebar-sub-item').filter({ hasText: "Business Intelligence" });
  316 |       if (await biTab.isVisible({ timeout: 3000 }).catch(() => false)) {
  317 |         await biTab.click();
  318 |       }
  319 |     }
  320 | 
  321 |     await page.waitForTimeout(2000);
  322 |     const pageText = await page.locator("main").textContent().catch(() => "");
  323 |     await screenshot(page, "07_business_intelligence");
  324 | 
  325 |     // Check for forbidden tokens
  326 |     let groundingFailed = false;
  327 |     for (const token of FORBIDDEN_TOKENS) {
  328 |       if (pageText && pageText.includes(token)) {
  329 |         groundingFailed = true;
  330 |         addIssue("CRITICAL", `Hallucinated content detected: "${token}"`,
  331 |           `The forbidden term "${token}" appeared in the Business Intelligence tab`,
  332 |           `Open Intelligence → Business Intelligence → search for "${token}"`,
  333 |           "Fix grounding engine to reject cross-domain entities; ensure domain identity validator rejects benjamin_franklin / librarycompany.org");
  334 |         logFinding(`❌ GROUNDING FAIL: Found forbidden token "${token}"`);
  335 |       }
  336 |     }
  337 | 
  338 |     if (!groundingFailed) {
  339 |       logFinding("✅ Grounding PASSED: No forbidden tokens found in Business Intelligence");
  340 |     }
  341 | 
  342 |     // Also check via API if project exists
  343 |     if (projectId) {
  344 |       const apiUrl = `${BACKEND_URL}/api/v1/analysis/business-intelligence/${projectId}`;
  345 |       const biResp = await request.get(apiUrl, {
  346 |         headers: { Authorization: AUTH_HEADER }
  347 |       }).catch(() => null);
  348 | 
  349 |       if (biResp) {
  350 |         logFinding(`BI API status: ${biResp.status()}`);
  351 |         if (biResp.status() === 200) {
  352 |           const biBody = await biResp.text();
  353 |           for (const token of FORBIDDEN_TOKENS) {
  354 |             if (biBody.includes(token)) {
  355 |               addIssue("CRITICAL", `API Grounding Fail: "${token}" in BI response`,
  356 |                 `Forbidden token in /business-intelligence API response`,
  357 |                 `GET /api/v1/analysis/business-intelligence/${projectId}`,
  358 |                 "Fix GroundingEngineV2 + DomainIdentityValidator to reject cross-domain content");
  359 |               logFinding(`❌ API GROUNDING FAIL: "${token}" in BI API response`);
  360 |             }
  361 |           }
  362 |         } else if (biResp.status() === 404) {
  363 |           logFinding("ℹ️ BI API returned 404 — pipeline may not have completed yet");
  364 |         } else {
  365 |           addIssue("MEDIUM", `BI API unexpected status: ${biResp.status()}`,
  366 |             `GET /api/v1/analysis/business-intelligence/${projectId} returned ${biResp.status()}`,
  367 |             "Call BI API with valid project ID",
  368 |             "Check business intelligence router");
  369 |         }
  370 |       }
  371 |     }
  372 |   });
  373 | 
  374 |   // ── Phase 4 — Question Discovery ─────────────────────────────────────────
  375 |   test("Phase 4 — Question Discovery tab", async ({ page, request }) => {
  376 |     page.on("response", (resp) => {
  377 |       if (resp.url().includes("/api/") && resp.status() >= 400) {
  378 |         apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
  379 |       }
  380 |     });
  381 | 
  382 |     await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  383 |     await page.waitForTimeout(3000);
  384 | 
  385 |     const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
  386 |     try {
  387 |       await projItem.waitFor({ state: "visible", timeout: 15000 });
  388 |       await projItem.click();
  389 |       await page.waitForTimeout(2000);
  390 |     } catch (e) {
  391 |       logFinding("⚠️ Project item not visible for click in Phase 4");
  392 |     }
  393 | 
  394 |     // Navigate to Intelligence → Questions
  395 |     const intelligenceBtn = page.locator('button.sidebar-nav-item').filter({ hasText: "Intelligence" });
  396 |     await intelligenceBtn.click().catch(() => {});
  397 |     await page.locator('button.sidebar-sub-item').filter({ hasText: "Questions" }).click().catch(() => {});
  398 |     
  399 |     const t0 = Date.now();
> 400 |     await page.waitForTimeout(2000);
      |                ^ Error: page.waitForTimeout: Target page, context or browser has been closed
  401 |     timings["questions_tab_load_ms"] = Date.now() - t0;
  402 | 
  403 |     await screenshot(page, "08_questions_tab");
  404 |     const mainText = await page.locator("main").textContent().catch(() => "");
  405 | 
  406 |     // Check for question cards
  407 |     const questionCards = page.locator('[class*="question"], [class*="Question"], .card');
  408 |     const qCount = await questionCards.count();
  409 |     logFinding(`Questions tab — found ${qCount} elements on page`);
  410 | 
  411 |     // Check for "No questions" state
  412 |     if (mainText && (mainText.includes("No questions") || mainText.includes("no questions"))) {
  413 |       addIssue("HIGH", "Questions tab is empty",
  414 |         "Questions tab shows no questions after pipeline completion",
  415 |         "Run analysis → open Intelligence → Questions",
  416 |         "Verify question_discovery agent is saving questions to Supabase");
  417 |       logFinding("❌ Questions tab shows empty state");
  418 |     } else {
  419 |       logFinding("✅ Questions tab has content");
  420 |     }
  421 | 
  422 |     // Test search
  423 |     const searchInput = page.locator('input[placeholder*="earch"], input[placeholder*="question"]').first();
  424 |     if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
  425 |       await searchInput.fill("recommend");
  426 |       await page.waitForTimeout(1000);
  427 |       logFinding("✅ Questions search field works");
  428 |       await searchInput.clear();
  429 |     } else {
  430 |       addIssue("MEDIUM", "Questions search input not found",
  431 |         "Cannot locate search input on Questions tab",
  432 |         "Open Questions tab → look for search box",
  433 |         "Check QuestionDiscoveryTab for search input rendering");
  434 |     }
  435 | 
  436 |     // API count check
  437 |     if (projectId) {
  438 |       const qApiUrl = `${BACKEND_URL}/api/v1/analysis/questions/${projectId}?page=1&page_size=50`;
  439 |       const qResp = await request.get(qApiUrl, {
  440 |         headers: { Authorization: AUTH_HEADER }
  441 |       }).catch(() => null);
  442 | 
  443 |       if (qResp && qResp.status() === 200) {
  444 |         const qBody = await qResp.json().catch(() => ({}));
  445 |         const count = qBody.total || qBody.count || (Array.isArray(qBody.data) ? qBody.data.length : 0);
  446 |         logFinding(`Questions API total count: ${count}`);
  447 |         if (count === 0) {
  448 |           addIssue("HIGH", "Questions API returns 0 questions",
  449 |             `GET ${qApiUrl} returned count=${count}`,
  450 |             "Run analysis → check questions API",
  451 |             "Verify question_discovery agent stores questions and question intelligence runs correctly");
  452 |         } else {
  453 |           logFinding(`✅ Questions API: ${count} questions found`);
  454 |         }
  455 |       } else {
  456 |         logFinding(`ℹ️ Questions API status: ${qResp?.status() ?? "no response"}`);
  457 |       }
  458 |     }
  459 |   });
  460 | 
  461 |   // ── Phase 5 — Keyword Intelligence ────────────────────────────────────────
  462 |   test("Phase 5 — Keyword Intelligence tab", async ({ page, request }) => {
  463 |     page.on("response", (resp) => {
  464 |       if (resp.url().includes("/api/") && resp.status() >= 400) {
  465 |         apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
  466 |       }
  467 |     });
  468 | 
  469 |     await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  470 |     await page.waitForTimeout(3000);
  471 |     const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
  472 |     try {
  473 |       await projItem.waitFor({ state: "visible", timeout: 15000 });
  474 |       await projItem.click();
  475 |       await page.waitForTimeout(2000);
  476 |     } catch (e) {
  477 |       logFinding("⚠️ Project item not visible for click in Phase 5");
  478 |     }
  479 | 
  480 |     await page.locator('button.sidebar-nav-item').filter({ hasText: "Intelligence" }).click().catch(() => {});
  481 |     await page.locator('button.sidebar-sub-item').filter({ hasText: "Keywords" }).click().catch(() => {});
  482 | 
  483 |     const t0 = Date.now();
  484 |     await page.waitForTimeout(2000);
  485 |     timings["keywords_tab_load_ms"] = Date.now() - t0;
  486 | 
  487 |     await screenshot(page, "09_keywords_tab");
  488 |     const mainText = await page.locator("main").textContent().catch(() => "");
  489 | 
  490 |     if (mainText && (mainText.includes("No keywords") || mainText.includes("no keywords"))) {
  491 |       addIssue("HIGH", "Keywords tab is empty",
  492 |         "Keywords tab shows no keywords after pipeline completion",
  493 |         "Run analysis → Intelligence → Keywords",
  494 |         "Verify keyword_intelligence agent stores keywords to Supabase");
  495 |       logFinding("❌ Keywords tab shows empty state");
  496 |     } else {
  497 |       logFinding("✅ Keywords tab has content");
  498 |     }
  499 | 
  500 |     // Test search
```