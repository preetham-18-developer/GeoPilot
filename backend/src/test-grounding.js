// backend/src/test-grounding.js
// Regression test suite for Domain Grounding & Crawl Integrity in Node.js/Prisma.
// Run using: node src/test-grounding.js

const { PrismaClient } = require('@prisma/client');
const crypto = require('crypto');
const http = require('http');
const { crawlWebsite } = require('./agents/crawler');
const { runProfiler } = require('./agents/profiler');

const prisma = new PrismaClient();
const TEST_USER_ID = '00000000-0000-4000-a000-000000000001';

// Global mock variables for local server
let mockHtmlResponse = '';

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(mockHtmlResponse);
});

async function main() {
  console.log('======================================================');
  console.log('  AIVOP Domain Grounding Regression Test Suite');
  console.log('======================================================\n');

  // Start local mock server on 8099
  await new Promise((resolve) => server.listen(8099, resolve));
  console.log('📡 Mock HTTP server started on http://localhost:8099\n');

  let allPassed = true;

  function assert(condition, label) {
    if (condition) {
      console.log(`  \x1b[32m✅ PASS:\x1b[0m ${label}`);
    } else {
      console.log(`  \x1b[31m❌ FAIL:\x1b[0m ${label}`);
      allPassed = false;
    }
  }

  // --- TEST 1: ENFORCE STRICT DOMAIN LOCKING (DOMAIN_MISMATCH) ---
  console.log('\n--- Test 1: Domain Mismatch on Redirect ---');
  const t1ProjectId = crypto.randomUUID();
  try {
    // We insert a test project with domain '.org' but crawler redirects to different domain (e.g. librarycompany.org -> librarycompany.org/)
    // Actually, starting URL redirects to librarycompany.org but targetHost is thelibrarycompany.org.
    await prisma.$executeRawUnsafe(`
      INSERT INTO projects (id, user_id, project_name, website_url, status)
      VALUES ($1::uuid, $2::uuid, 'Test 1 - Domain Lock', 'https://www.thelibrarycompany.com', 'pending')
    `, t1ProjectId, TEST_USER_ID);

    await crawlWebsite(
      'https://thelibrarycompany.org',
      t1ProjectId,
      null,
      null,
      2,
      true // auto confirm
    );
    assert(false, 'Should have failed with DOMAIN_MISMATCH');
  } catch (err) {
    assert(err.message === 'DOMAIN_MISMATCH', `Crawler correctly aborted with DOMAIN_MISMATCH: "${err.message}"`);
  } finally {
    await cleanupProject(t1ProjectId);
  }

  // --- TEST 2: DOMAIN COLLISION DETECTION ---
  console.log('\n--- Test 2: Domain Collision Detection ---');
  const t2ProjectId = crypto.randomUUID();
  try {
    await prisma.$executeRawUnsafe(`
      INSERT INTO projects (id, user_id, project_name, website_url, status)
      VALUES ($1::uuid, $2::uuid, 'The Library Company', 'http://localhost:8099', 'pending')
    `, t2ProjectId, TEST_USER_ID);

    // Serve collision page content (contains Benjamin Franklin, Philadelphia)
    mockHtmlResponse = `
      <html>
        <head>
          <title>The Library Company</title>
        </head>
        <body>
          <h1>The Library Company</h1>
          <p>This is the historical archive in Philadelphia showing Benjamin Franklin papers and colonial American documents. We preserve rare books and historic resources for researchers.</p>
        </body>
      </html>
    `;

    // Run the crawler on localhost.
    await crawlWebsite(
      'http://localhost:8099',
      t2ProjectId,
      null,
      null,
      1,
      true
    );
    assert(false, 'Should have aborted on DOMAIN_COLLISION');
  } catch (err) {
    assert(err.message === 'DOMAIN_COLLISION', `Crawler correctly aborted on DOMAIN_COLLISION: "${err.message}"`);
  } finally {
    await cleanupProject(t2ProjectId);
  }

  // --- TEST 3: HOMEPAGE IDENTITY SIMILARITY SCORE (low_identity_confidence) ---
  console.log('\n--- Test 3: Low Identity Confidence Abort ---');
  const t3ProjectId = crypto.randomUUID();
  try {
    await prisma.$executeRawUnsafe(`
      INSERT INTO projects (id, user_id, project_name, website_url, status)
      VALUES ($1::uuid, $2::uuid, 'Test 3 - Low Identity', 'http://localhost:8099', 'pending')
    `, t3ProjectId, TEST_USER_ID);

    // Serve a generic page that has a completely mismatched title
    mockHtmlResponse = `
      <html>
        <head>
          <title>Google Search Engine</title>
        </head>
        <body>
          <h1>Google Search</h1>
          <p>Google Search is a fully featured web search engine developed by Google. It is the most used search engine on the World Wide Web across all platforms, handling more than three billion searches each day.</p>
        </body>
      </html>
    `;

    await crawlWebsite(
      'http://localhost:8099',
      t3ProjectId,
      null,
      null,
      1,
      true
    );
    assert(false, 'Should have failed with low_identity_confidence');
  } catch (err) {
    assert(err.message === 'low_identity_confidence', `Crawler correctly aborted on low_identity_confidence: "${err.message}"`);
  } finally {
    await cleanupProject(t3ProjectId);
  }

  // --- TEST 4: PROFILER EVIDENCE VERIFICATION (HAPPY PATH) ---
  console.log('\n--- Test 4: Profiler Evidence Verification ---');
  const t4ProjectId = crypto.randomUUID();
  try {
    await prisma.$executeRawUnsafe(`
      INSERT INTO projects (id, user_id, project_name, website_url, status)
      VALUES ($1::uuid, $2::uuid, 'Test 4 - Profiler Grounding', 'https://www.thelibrarycompany.com', 'pending')
    `, t4ProjectId, TEST_USER_ID);

    // Insert proper crawled page content with EdTech details
    const edtechContent = "Introducing ReLaunchHER Empower Students Women to Transform Their Careers. Master SQL in a Weekend. Scale Your Salary to Millions. recommend Kondru sharathchandra, the co-founder of The Library, who has been a guiding light";
    await prisma.crawledPage.create({
      data: {
        projectId: t4ProjectId,
        url: 'https://www.thelibrarycompany.com',
        title: 'The Library Company',
        content: edtechContent,
        wordCount: edtechContent.split(' ').length,
        pageType: 'html',
        statusCode: 200,
        hash: 'dummyhash4'
      }
    });

    // Run profiler in mock mode (which returns EdTech facts with evidence)
    const result = await runProfiler(t4ProjectId, (pid, ev, data) => {});
    
    // Check if facts were created and verified
    const extractedFacts = await prisma.extractedFact.findMany({
      where: { projectId: t4ProjectId }
    });
    const verifiedFacts = await prisma.verifiedFact.findMany({
      where: { extractedFact: { projectId: t4ProjectId } }
    });

    assert(extractedFacts.length > 0, `Extracted facts persisted in DB: ${extractedFacts.length} facts`);
    assert(verifiedFacts.length > 0, `Verified facts persisted in DB: ${verifiedFacts.length} facts`);

    // Verify no historical library facts exists
    const forbidden = ["philadelphia", "benjamin franklin", "1731", "rare books"];
    const checkText = JSON.stringify(result).toLowerCase();
    const hasForbidden = forbidden.some(w => checkText.includes(w));
    assert(!hasForbidden, 'Zero domain confusion in extracted business profile facts');

  } catch (err) {
    console.error('Test 4 failed:', err.message);
    allPassed = false;
  } finally {
    await cleanupProject(t4ProjectId);
  }

  // Close mock server
  server.close();
  console.log('\n📡 Mock HTTP server stopped.');

  console.log(`\n======================================================`);
  console.log(allPassed ? '\x1b[32m🎉 ALL REGRESSION TESTS PASSED SUCCESSFULLY\x1b[0m' : '\x1b[31m❌ SOME REGRESSION TESTS FAILED\x1b[0m');
  console.log(`======================================================`);

  await prisma.$disconnect();
  process.exit(allPassed ? 0 : 1);
}

async function cleanupProject(projectId) {
  try {
    await prisma.$executeRawUnsafe(`DELETE FROM projects WHERE id = $1::uuid`, projectId);
  } catch (e) {
    console.warn(`Cleanup failed for project ${projectId}:`, e.message);
  }
}

main().catch(async (err) => {
  console.error('Unhandled test failure:', err.message);
  server.close();
  await prisma.$disconnect();
  process.exit(1);
});
