const { PrismaClient } = require('@prisma/client');
const { runProfiler } = require('./agents/profiler');
const crypto = require('crypto');

const prisma = new PrismaClient();

async function testProfiler() {
  console.log('=== PHASE 2 TEST: BUSINESS PROFILER ===\n');

  // Let's find or create a test project
  // We can fetch the first project from the projects table or create a new one.
  let testProject = await prisma.project.findFirst({
    where: { projectName: 'Library Company — Test Crawl' }
  });

  if (!testProject) {
    // If not found, let's see if there is any project in the DB
    testProject = await prisma.project.findFirst();
  }

  if (!testProject) {
    console.log('No project found in DB. Creating a dummy project with crawled page data...');
    
    // Create a dummy project and a crawled page
    const projectId = crypto.randomUUID();
    const userId = '00000000-0000-4000-a000-000000000001';
    
    await prisma.$executeRawUnsafe(`
      INSERT INTO projects (id, user_id, project_name, website_url, status)
      VALUES ($1::uuid, $2::uuid, 'Library Company — Test Crawl', 'https://thelibrarycompany.org', 'pending')
    `, projectId, userId);

    await prisma.$executeRawUnsafe(`
      INSERT INTO web_pages (id, project_id, url, title, content, word_count)
      VALUES ($1::uuid, $2::uuid, 'https://thelibrarycompany.org', 'The Library Company of Philadelphia', 'Benjamin Franklin original papers. Rare manuscript access Philadelphia. Colonial American history research. Genealogy research Philadelphia.', 100)
    `, crypto.randomUUID(), projectId);

    testProject = { id: projectId };
  }

  const projectId = testProject.id;
  console.log(`Using Project ID: ${projectId}`);
  
  const emit = (pid, event, data) => {
    console.log(`[${event}]`, typeof data === 'string' ? data : JSON.stringify(data));
  };
  
  try {
    const profile = await runProfiler(projectId, emit);
    
    console.log('\n=== VALIDATION ===');
    
    // Check 1: business_name is real
    const nameCheck = profile.business_name &&
      profile.business_name !== 'Unknown' &&
      profile.business_name.length > 3;
    console.log(nameCheck
      ? `✅ business_name: "${profile.business_name}"`
      : `❌ business_name invalid: "${profile.business_name}"`);
    
    // Check 2: seed_topics exist
    const topicsExist = Array.isArray(profile.seed_topics) &&
      profile.seed_topics.length >= 5;
    console.log(topicsExist
      ? `✅ seed_topics: ${profile.seed_topics.length} topics`
      : `❌ seed_topics: only ${profile.seed_topics?.length} (need 5+)`);
    
    // Check 3: no generic topics
    const GENERIC = ['services','quality','excellence','resources','support'];
    const genericFound = profile.seed_topics?.filter(t =>
      GENERIC.some(g => t.toLowerCase() === g)
    ) || [];
    console.log(genericFound.length === 0
      ? `✅ No generic seed topics`
      : `❌ Generic topics found: ${genericFound.join(', ')}`);
    
    // Check 4: topics are searchable (2+ words each)
    const shortTopics = profile.seed_topics?.filter(
      t => t.split(' ').length < 2
    ) || [];
    console.log(shortTopics.length === 0
      ? `✅ All topics are 2+ words`
      : `❌ Single-word topics found: ${shortTopics.join(', ')}`);
    
    // Check 5: city extracted if local
    if (profile.is_local_business) {
      console.log(profile.city
        ? `✅ City extracted: "${profile.city}"`
        : `⚠ Local business but no city found`);
    }
    
    // Print all seed topics for manual review
    console.log('\n=== SEED TOPICS (review manually) ===');
    profile.seed_topics?.forEach((t, i) => {
      console.log(`  ${i+1}. ${t}`);
    });
    
    console.log('\n=== AGENT LOG ===');
    const logs = await prisma.$queryRawUnsafe(`
      SELECT * FROM agent_logs
      WHERE project_id = $1::uuid
      ORDER BY created_at DESC
      LIMIT 3
    `, projectId);
    
    logs?.forEach(log => {
      console.log(
        `${log.agent_name}: $${log.cost_estimate_usd?.toFixed(5)} ` +
        `| ${log.input_tokens} in / ${log.output_tokens} out`
      );
    });
    
    const allPassed = nameCheck && topicsExist && genericFound.length === 0 && shortTopics.length === 0;
    console.log(allPassed
      ? '\n🎉 ALL CHECKS PASSED — Ready for Phase 3'
      : '\n❌ CHECKS FAILED — Fix profiler before Phase 3');
    
  } catch(err) {
    console.error('❌ Profiler crashed:', err.message);
  } finally {
    await prisma.$disconnect();
  }
}

testProfiler();
