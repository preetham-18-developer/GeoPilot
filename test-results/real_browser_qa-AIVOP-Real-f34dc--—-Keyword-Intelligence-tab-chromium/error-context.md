# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: real_browser_qa.spec.ts >> AIVOP Real Browser QA Audit >> Phase 5 — Keyword Intelligence tab
- Location: tests\e2e\real_browser_qa.spec.ts:462:7

# Error details

```
Test timeout of 600000ms exceeded.
```

```
Error: page.waitForTimeout: Target page, context or browser has been closed
```

# Test source

```ts
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
  400 |     await page.waitForTimeout(2000);
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
> 484 |     await page.waitForTimeout(2000);
      |                ^ Error: page.waitForTimeout: Target page, context or browser has been closed
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
  501 |     const searchInput = page.locator('input[placeholder*="earch"], input[placeholder*="keyword"]').first();
  502 |     if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
  503 |       await searchInput.fill("mentorship");
  504 |       await page.waitForTimeout(1000);
  505 |       logFinding("✅ Keywords search works");
  506 |       await searchInput.clear();
  507 |     } else {
  508 |       addIssue("MEDIUM", "Keywords search input not found", 
  509 |         "Cannot locate search input on Keywords tab",
  510 |         "Open Keywords tab → look for search box",
  511 |         "Check KeywordIntelligenceTab for search input");
  512 |     }
  513 | 
  514 |     // API count check
  515 |     if (projectId) {
  516 |       const kApiUrl = `${BACKEND_URL}/api/v1/analysis/keywords/${projectId}?page=1&page_size=50`;
  517 |       const kResp = await request.get(kApiUrl, { headers: { Authorization: AUTH_HEADER } }).catch(() => null);
  518 |       if (kResp && kResp.status() === 200) {
  519 |         const kBody = await kResp.json().catch(() => ({}));
  520 |         const count = kBody.total || kBody.count || (Array.isArray(kBody.data) ? kBody.data.length : 0);
  521 |         logFinding(`Keywords API total count: ${count}`);
  522 |         if (count === 0) {
  523 |           addIssue("HIGH", "Keywords API returns 0 keywords",
  524 |             `GET ${kApiUrl} returned count=${count}`,
  525 |             "Run analysis → check keywords API",
  526 |             "Verify keyword_intelligence agent");
  527 |         } else {
  528 |           logFinding(`✅ Keywords API: ${count} keywords found`);
  529 |         }
  530 |       }
  531 |     }
  532 |   });
  533 | 
  534 |   // ── Phase 6 — All Intelligence Tabs ───────────────────────────────────────
  535 |   test("Phase 6 — All tabs load without crash", async ({ page }) => {
  536 |     const tabErrors: string[] = [];
  537 |     page.on("console", (msg) => {
  538 |       if (msg.type() === "error") consoleErrors.push(`[P6] ${msg.text()}`);
  539 |     });
  540 |     page.on("pageerror", (err) => tabErrors.push(`pageerror: ${err.message}`));
  541 |     page.on("response", (resp) => {
  542 |       if (resp.url().includes("/api/") && resp.status() >= 400) {
  543 |         apiFailures.push({ url: resp.url(), status: resp.status(), method: resp.request().method() });
  544 |       }
  545 |     });
  546 | 
  547 |     await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  548 |     await page.waitForTimeout(3000);
  549 |     const projItem = page.locator('.sidebar-project-item').filter({ hasText: PROJ_NAME }).first();
  550 |     try {
  551 |       await projItem.waitFor({ state: "visible", timeout: 15000 });
  552 |       await projItem.click();
  553 |       await page.waitForTimeout(2000);
  554 |     } catch (e) {
  555 |       logFinding("⚠️ Project item not visible for click in Phase 6");
  556 |     }
  557 | 
  558 |     const sections: { sectionLabel: string; tabs: { label: string; key: string }[] }[] = [
  559 |       {
  560 |         sectionLabel: "Intelligence",
  561 |         tabs: [
  562 |           { label: "Business Intelligence", key: "bi" },
  563 |           { label: "Verified Facts", key: "facts" },
  564 |           { label: "Questions", key: "questions" },
  565 |           { label: "Keywords", key: "keywords" },
  566 |           { label: "Competitors", key: "competitors" },
  567 |           { label: "Validation", key: "validation" },
  568 |           { label: "Reality Checker", key: "reality_check" },
  569 |           { label: "Recommendation Intel", key: "rec_intel" },
  570 |           { label: "Competitor Benchmark", key: "benchmark" },
  571 |           { label: "Historical Tracker", key: "tracker" },
  572 |           { label: "Advanced Analytics", key: "analytics" },
  573 |           { label: "GEO Intelligence", key: "geo_intel" },
  574 |         ],
  575 |       },
  576 |       {
  577 |         sectionLabel: "Content Studio",
  578 |         tabs: [
  579 |           { label: "Content Intelligence", key: "content_intel" },
  580 |           { label: "Opportunities", key: "content" },
  581 |         ],
  582 |       },
  583 |       {
  584 |         sectionLabel: "Optimization",
```