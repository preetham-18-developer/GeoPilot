const { PrismaClient } = require('@prisma/client');
const OpenAI = require('openai');

const prisma = new PrismaClient();

const nvidia = new OpenAI({
  baseURL: process.env.NVIDIA_BASE_URL || 'https://integrate.api.nvidia.com/v1',
  apiKey: process.env.NVIDIA_API_KEY,
  timeout: 90000,
  maxRetries: 2
});

const PROFILER_MODEL = 'nvidia/llama-3.1-nemotron-ultra-253b-v1';

async function runProfiler(projectId, emit) {
  emit(projectId, 'agent:stream', '→ Starting Business Profiler (Pass 1: Core pages)');

  // MOCK MODE (always check first)
  if (process.env.NVIDIA_API_KEY === 'mock_key') {
    const mockProfile = getMockProfile();
    const validTopics = validateSeedTopics(mockProfile.seed_topics || []);
    mockProfile.seed_topics = validTopics;

    // Log mock cost
    await logAgentCost(projectId, 'profiler_mock', 1000, 500);

    // Save to DB
    await prisma.$executeRawUnsafe(`
      UPDATE projects
      SET business_profile = $1::jsonb,
          seed_topics = $2::text[],
          low_content_warning = $3::boolean,
          status = 'profiled'
      WHERE id = $4::uuid
    `, JSON.stringify(mockProfile), validTopics, validTopics.length < 5, projectId);

    // Save to business_profiles table
    await prisma.businessProfile.create({
      data: {
        projectId,
        companyName: mockProfile.business_name,
        industry: mockProfile.industry,
        description: mockProfile.business_type,
        mission: "Empowering Students and Women to Transform Their Careers",
        vision: "Guidance to connect passion with profession",
        usp: mockProfile.unique_selling_points?.[0] || "",
        targetAudience: mockProfile.target_customers?.join(", ") || "",
        strengths: ["Personalized Mentorship", "Industry-aligned programs"],
        weaknesses: [],
        opportunities: ["Relaunch careers in tech"],
        risks: [],
        trustSignals: ["Partner Colleges", "Co-founder recommendation"],
        businessModel: "Mentorship and Workshops",
        aiVisibility: []
      }
    }).catch(e => console.error('DB BusinessProfile create error:', e.message));

    const verifiedFacts = await verifyAndPersistFacts(projectId, mockProfile.facts || []);

    emit(projectId, 'agent:stream', `🎉 Profiler complete (MOCK): ${validTopics.length} seed topics ready`);
    return {
      businessProfile: mockProfile,
      verifiedFacts
    };
  }

  // PASS 1 — Core pages only
  const corePages = await prisma.$queryRawUnsafe(`
    SELECT url, content FROM web_pages
    WHERE project_id = $1::uuid
      AND (
        url ILIKE '%/about%' OR
        url ILIKE '%/service%' OR
        url ILIKE '%/course%' OR
        url ILIKE '%/program%' OR
        url ILIKE '%/home%' OR
        url ILIKE '%/index%'
      )
    ORDER BY created_at ASC
    LIMIT 5
  `, projectId);

  // Also always include the homepage (shortest URL = homepage)
  const allPages = await prisma.$queryRawUnsafe(`
    SELECT url, content FROM web_pages
    WHERE project_id = $1::uuid
    ORDER BY url ASC
  `, projectId);

  if (!allPages || !allPages.length) {
    throw new Error('No crawled page contents found in database');
  }

  // Homepage = the page with shortest URL for this domain
  const homepage = allPages.reduce((shortest, page) =>
    page.url.length < shortest.url.length ? page : shortest
  , allPages[0]);

  // Combine core pages + homepage, deduplicate by URL
  const coreContent = [homepage, ...(corePages || [])]
    .filter(Boolean)
    .filter((page, index, self) =>
      index === self.findIndex(p => p.url === page.url)
    )
    .map(p => `=== PAGE: ${p.url} ===\n${p.content}`)
    .join('\n\n');

  // Take first 3000 words
  const pass1Text = coreContent.split(/\s+/).slice(0, 3000).join(' ');

  emit(projectId, 'agent:stream', `→ Pass 1: ${pass1Text.split(/\s+/).length} words from core pages`);

  // NVIDIA CALL — PASS 1
  const pass1Result = await callNvidiaProfiler(pass1Text, null, projectId);
  
  emit(projectId, 'agent:stream', `✓ Pass 1 complete: ${pass1Result.seed_topics?.length || 0} seed topics found`);

  // PASS 2 — Remaining pages
  const usedUrls = [homepage?.url, ...(corePages?.map(p => p.url) || [])].filter(Boolean);
  
  const remainingPages = await prisma.$queryRawUnsafe(`
    SELECT url, content FROM web_pages
    WHERE project_id = $1::uuid
      AND NOT (url = ANY($2::text[]))
  `, projectId, usedUrls);

  let pass2Result = null;
  if (remainingPages && remainingPages.length > 0) {
    emit(projectId, 'agent:stream', `→ Pass 2: ${remainingPages.length} additional pages`);

    const pass2Text = remainingPages
      .map(p => `=== PAGE: ${p.url} ===\n${p.content}`)
      .join('\n\n')
      .split(/\s+/).slice(0, 2000).join(' ');

    pass2Result = await callNvidiaProfiler(pass2Text, pass1Result, projectId);

    // MERGE
    const mergedTopics = [
      ...(pass1Result.seed_topics || []),
      ...(pass2Result.additional_seed_topics || [])
    ];

    // Deduplicate topics (lowercase + trim)
    const uniqueTopics = [...new Set(
      mergedTopics.map(t => t.toLowerCase().trim())
    )].map(t =>
      mergedTopics.find(orig => orig.toLowerCase().trim() === t)
    );

    pass1Result.seed_topics = uniqueTopics;
    pass1Result.additional_facts = [
      ...(pass1Result.additional_facts || []),
      ...(pass2Result.additional_facts || [])
    ];

    emit(projectId, 'agent:stream', `✓ Pass 2 complete: ${uniqueTopics.length} total seed topics`);
  }

  // VALIDATE SEED TOPICS
  const validTopics = validateSeedTopics(pass1Result.seed_topics || []);
  pass1Result.seed_topics = validTopics;

  if (validTopics.length < 5) {
    emit(projectId, 'agent:stream', `⚠ WARNING: Only ${validTopics.length} valid seed topics found. Website may have thin content.`);
  }

  // SAVE TO DB
  await prisma.$executeRawUnsafe(`
    UPDATE projects
    SET business_profile = $1::jsonb,
        seed_topics = $2::text[],
        low_content_warning = $3::boolean,
        status = 'profiled'
    WHERE id = $4::uuid
  `, JSON.stringify(pass1Result), validTopics, validTopics.length < 5, projectId);

  // SAVE TO business_profiles table as well!
  await prisma.businessProfile.create({
    data: {
      projectId,
      companyName: pass1Result.business_name || null,
      industry: pass1Result.industry || null,
      description: pass1Result.business_type || null,
      mission: pass1Result.mission || null,
      vision: pass1Result.vision || null,
      usp: pass1Result.unique_selling_points?.[0] || null,
      targetAudience: pass1Result.target_customers?.join(", ") || null,
      strengths: pass1Result.services?.map(s => s.name) || [],
      weaknesses: [],
      opportunities: [],
      risks: [],
      trustSignals: [],
      businessModel: null,
      aiVisibility: []
    }
  }).catch(e => console.error('DB BusinessProfile create error:', e.message));

  // Extract all facts from pass1Result and optionally pass2Result
  const allFacts = [
    ...(pass1Result.facts || []),
    ...(pass2Result?.facts || [])
  ];

  const verifiedFacts = await verifyAndPersistFacts(projectId, allFacts);

  emit(projectId, 'agent:stream', `🎉 Profiler complete: ${validTopics.length} seed topics ready`);

  return {
    businessProfile: pass1Result,
    verifiedFacts
  };
}

async function callNvidiaProfiler(contentText, existingProfile, projectId) {
  const isPass2 = existingProfile !== null;
  
  const systemPrompt = `You extract structured business facts from \nwebsite content. Use ONLY information present in the provided text.\nReturn null for any field not found. Return valid JSON only.\nNo explanation. No markdown. No code blocks.`;

  const userPrompt = isPass2
    ? buildPass2Prompt(contentText, existingProfile)
    : buildPass1Prompt(contentText);

  const response = await nvidia.chat.completions.create({
    model: PROFILER_MODEL,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ],
    temperature: 0.1,
    max_tokens: 3000,
    stream: false
  });

  const rawOutput = response.choices[0].message.content;
  
  // Log cost
  await logAgentCost(projectId, 'profiler_pass' + (isPass2 ? '2' : '1'),
    response.usage.prompt_tokens,
    response.usage.completion_tokens);

  // Parse JSON safely
  try {
    const cleaned = rawOutput
      .replace(/```json/g, '')
      .replace(/```/g, '')
      .trim();
    return JSON.parse(cleaned);
  } catch(e) {
    console.error('Profiler JSON parse failed:', rawOutput.slice(0, 200));
    throw new Error('Profiler returned invalid JSON');
  }
}

function buildPass1Prompt(contentText) {
  return `Extract business facts from this website content:

${contentText}

Return EXACTLY this JSON structure (no other text):
{
  "business_name": "exact name from website",
  "business_type": "specific type (e.g. Historical Library, SQL Training Institute, Dental Clinic)",
  "industry": "industry name",
  "city": "city name or null",
  "state": "state name or null",
  "country": "country name or null",
  "is_local_business": true or false,
  "primary_language": "language",
  
  "services": [
    { "name": "specific service name", "description": "what it actually is" }
  ],
  "courses": [
    { "name": "specific course name", "description": "what it covers" }
  ],
  "products": [
    { "name": "specific product name", "description": "what it is" }
  ],
  
  "target_customers": ["specific type of customer"],
  "problems_they_solve": ["specific problem in customer language"],
  "unique_selling_points": ["specific unique claim from website"],
  
  "pricing_mentioned": "any pricing info or null",
  "schedule_mentioned": "any schedule/timing info or null",
  
  "has_faq_page": true or false,
  "has_blog": true or false,
  "has_testimonials": true or false,
  "has_location_info": true or false,
  "has_schema_markup": true or false,
  
  "seed_topics": []
}

SEED TOPICS — most critical field. Rules:

1. Each seed topic = something a real person would search for
2. Must be SPECIFIC — not generic category names
3. Must exist in the website content provided
4. Format: "[specific thing] [optional location]"

WRONG examples (too generic, reject these):
"library services", "our collections", "research help", "quality education"

RIGHT examples (specific, searchable):
"Benjamin Franklin original manuscripts Philadelphia"
"18th century colonial American documents"
"genealogy research assistance Philadelphia"
"SQL weekend batch classes Nellore"
"teeth whitening Nellore dental clinic"
"emergency dental care same day appointment"

Think: if someone typed this into ChatGPT and asked
"recommend a [business type] for this" — would this business
come up if it had content about this topic?

If YES → include as seed topic.
If NO → exclude.

Generate between 10-40 seed topics.
Return ONLY the JSON. Nothing else.`;
}

function buildPass2Prompt(contentText, existingProfile) {
  return `You already have this profile for ${existingProfile.business_name}:

EXISTING PROFILE SUMMARY:
Business: ${existingProfile.business_name}
Type: ${existingProfile.business_type}
Current seed topics: ${JSON.stringify(existingProfile.seed_topics)}

Now read this ADDITIONAL content from the same website:

${contentText}

Return ONLY new information NOT already captured:
{
  "additional_seed_topics": [
    "new specific searchable topic not in existing list"
  ],
  "additional_services": ["new service found"],
  "testimonial_highlights": ["specific customer outcome mentioned"],
  "team_specializations": ["specific expertise of team members"],
  "certifications": ["specific certification or accreditation"],
  "awards_recognition": ["specific award or recognition"],
  "additional_facts": ["any other specific fact useful for SEO"]
}

Same rules for additional_seed_topics:
- Must be specific and searchable
- Must not duplicate existing seed topics
- Must exist in the additional content provided
- Return ONLY the JSON. Nothing else.`;
}

const GENERIC_WORDS_BLACKLIST = [
  'services', 'service', 'solutions', 'quality', 'excellence',
  'best', 'great', 'amazing', 'professional', 'expert',
  'our', 'your', 'we', 'us', 'the', 'a', 'an',
  'information', 'resources', 'support', 'help', 'assistance',
  'general', 'various', 'multiple', 'comprehensive',
  'management', 'system', 'platform', 'tool'
];

function validateSeedTopics(topics) {
  return topics.filter(topic => {
    if (!topic || typeof topic !== 'string') return false;
    
    const words = topic.toLowerCase().trim().split(/\s+/);
    
    // Must be at least 2 words
    if (words.length < 2) return false;
    
    // Must be under 8 words (too long = not a real search term)
    if (words.length > 8) return false;
    
    // Must not be ONLY generic words
    const nonGenericWords = words.filter(
      w => !GENERIC_WORDS_BLACKLIST.includes(w)
    );
    if (nonGenericWords.length === 0) return false;
    
    // Must be at least 10 characters
    if (topic.length < 10) return false;
    
    return true;
  });
}

async function logAgentCost(projectId, agentName, inputTokens, outputTokens) {
  const costUsd = (inputTokens * 0.000001) + (outputTokens * 0.000002);
  
  await prisma.$executeRawUnsafe(`
    INSERT INTO agent_logs (project_id, agent_name, input_tokens, output_tokens, cost_estimate_usd, model_used, cache_hit, status)
    VALUES ($1::uuid, $2::text, $3::integer, $4::integer, $5::double precision, $6::text, false, 'COMPLETE')
  `, projectId, agentName, inputTokens, outputTokens, costUsd, PROFILER_MODEL);
  
  console.log(`[COST] ${agentName}: $${costUsd.toFixed(5)} (${inputTokens} in / ${outputTokens} out)`);
}

async function verifyAndPersistFacts(projectId, facts) {
  if (!Array.isArray(facts)) return [];

  const pages = await prisma.crawledPage.findMany({
    where: { projectId }
  });

  const pageMap = new Map();
  const pageIdMap = new Map();
  for (const page of pages) {
    pageMap.set(page.url.toLowerCase(), page.content || '');
    pageIdMap.set(page.url.toLowerCase(), page.id);
  }

  const verifiedFactsList = [];

  for (const fact of facts) {
    if (!fact.source_url || !fact.evidence_text) continue;

    const sourceUrlLower = fact.source_url.toLowerCase();
    const pageContent = pageMap.get(sourceUrlLower);
    
    if (!pageContent) {
      console.log(`[Profiler] Evidence verification skipped: URL ${fact.source_url} not found in crawled pages.`);
      continue;
    }

    const normalizedContent = pageContent.toLowerCase().replace(/\s+/g, ' ');
    const normalizedEvidence = fact.evidence_text.toLowerCase().replace(/\s+/g, ' ');

    if (normalizedContent.includes(normalizedEvidence)) {
      const pageId = pageIdMap.get(sourceUrlLower);
      
      const extractedFact = await prisma.extractedFact.create({
        data: {
          projectId,
          pageId,
          factCategory: fact.category || 'general',
          factKey: fact.key || 'fact',
          factValue: fact.value || '',
          sourceUrl: fact.source_url,
          evidenceText: fact.evidence_text,
          confidenceScore: 1.0
        }
      });

      const verifiedFact = await prisma.verifiedFact.create({
        data: {
          extractedFactId: extractedFact.id,
          verificationStatus: 'verified',
          verificationScore: 100.0,
          verifiedBy: 'Verification Agent'
        }
      });

      verifiedFactsList.push({
        ...extractedFact,
        verifiedFact
      });
    } else {
      console.log(`[Profiler] Fact rejected (no matching evidence): ${JSON.stringify(fact)}`);
    }
  }

  return verifiedFactsList;
}

function getMockProfile() {
  return {
    business_name: "The Library Company",
    business_type: "Career Mentorship Platform",
    industry: "Education/EdTech",
    city: null,
    state: null,
    country: "India",
    is_local_business: false,
    primary_language: "English",
    services: [
      { name: "Personalized Mentorship", description: "Industry professionals from leading companies guiding students" },
      { name: "SQL Weekend Workshop", description: "Master SQL in a weekend and scale salary" },
      { name: "Build Your Own AI Assistant Workshop", description: "Master LLMs, RAG, and Vector DBs from basics to real-world applications" }
    ],
    courses: [
      { name: "SQL Weekend Workshop", description: "Intensive training to master SQL database queries" },
      { name: "Build Your Own AI Assistant", description: "Learn LLMs, RAG, and Vector DBs" }
    ],
    products: [
      { name: "ReLaunchHER Program", description: "Designed to empower women returning to tech to transform their careers" },
      { name: "Lattice Program", description: "Personalized career mentorship and recruiting framework" }
    ],
    target_customers: [
      "students",
      "women returning to tech",
      "professionals wanting to transition careers"
    ],
    problems_they_solve: [
      "Traditional schools do not connect passion with profession",
      "Women returning to tech need confidence and mentorship to relaunch careers",
      "Need to master advanced skills like SQL and AI/LLMs in a short time"
    ],
    unique_selling_points: [
      "Mentors are industry professionals and experts from leading companies",
      "ReLaunchHER program specifically empowers women returning to tech",
      "Lattice framework connects students with top company recruitment"
    ],
    pricing_mentioned: "Scale salary to millions, pricing details not explicitly specified",
    schedule_mentioned: "Weekend workshops, master SQL in a weekend",
    has_faq_page: false,
    has_blog: false,
    has_testimonials: true,
    has_location_info: false,
    has_schema_markup: false,
    seed_topics: [
      "career mentorship platform",
      "relaunchher career program women",
      "women returning to tech mentorship",
      "master sql in a weekend workshop",
      "build your own ai assistant workshop",
      "lattice personalized mentorship program",
      "industry professional career guidance",
      "learn llms rag and vector databases",
      "partner colleges top company recruitment"
    ],
    facts: [
      {
        category: "products",
        key: "ReLaunchHER Program",
        value: "ReLaunchHER Program designed to empower women returning to tech to transform their careers.",
        source_url: "https://www.thelibrarycompany.com",
        evidence_text: "Introducing ReLaunchHER Empower Students Women to Transform Their Careers"
      },
      {
        category: "services",
        key: "SQL Weekend Workshop",
        value: "Master SQL in a Weekend workshop to scale salary.",
        source_url: "https://www.thelibrarycompany.com",
        evidence_text: "Master SQL in a Weekend. Scale Your Salary to Millions"
      },
      {
        category: "services",
        key: "Build Your Own AI Assistant Workshop",
        value: "Build Your Own AI Assistant workshop mastering LLMs, RAG, and Vector DBs.",
        source_url: "https://www.thelibrarycompany.com",
        evidence_text: "Build Your Own AI Assistant. Master LLM's, RAG & Vector DBs"
      },
      {
        category: "unique_selling_points",
        key: "Co-founder recommendation",
        value: "Co-founder Kondru sharathchandra is recommended as a guiding light.",
        source_url: "https://www.thelibrarycompany.com",
        evidence_text: "recommend Kondru sharathchandra, the co-founder of The Library, who has been a guiding light"
      }
    ]
  };
}

module.exports = { runProfiler, verifyAndPersistFacts };
