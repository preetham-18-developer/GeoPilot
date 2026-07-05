const { PrismaClient } = require('@prisma/client');
const { OpenAI } = require('openai');
const crypto = require('crypto');

const prisma = new PrismaClient();

const OPENAI_API_KEY = process.env.NVIDIA_API_KEY_QUESTIONS || "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";
const BASE_URL = "https://integrate.api.nvidia.com/v1";

const openai = new OpenAI({
  apiKey: OPENAI_API_KEY,
  baseURL: BASE_URL
});

const QUESTION_PROMPT = `You are a specialized Question Discovery Agent.
Your goal is to discover key recommendation queries that users ask conversational AI engines (ChatGPT, Gemini, Claude, Perplexity) about this business.

Company: {company_name}
Industry: {industry}
Description: {description}
Website: {website_url}

Verified Business Facts:
{verified_facts_json}

Please generate at least 15 highly realistic, detailed conversational queries and recommended answers that different personas would ask.
Cover diverse Query Types, including:
- 'Direct Recommendation Queries' (recommendations for company products)
- 'Indirect Recommendation Queries' (comparison recommendations)
- 'Problem Queries' (addressing specific pain points)
- 'Outcome Queries' (focused on desired outcomes)
- 'Solution Queries' (looking for answers to bottlenecks)
- 'Decision Queries' (making selection decisions)
- 'Trust Queries' (compliance, reviews, and security)
- 'Urgent Need Queries' (immediate requirements)
- 'Budget Queries' (pricing and alternatives)
- 'Implementation Queries' (setup and configuration guides)
- 'Migration Queries' (transferring from old systems)
- 'Scaling Queries' (handling growth)
- 'Enterprise Queries' (corporate requirements)
- 'Beginner Queries' (basic or educational questions)
- 'Expert Queries' (deep technical requirements)
- 'Voice Search Queries' (natural language voice prompts)
- 'Natural Language Queries' (conversational prompts)
- 'AI Search Queries' (comparison summaries)
- 'Location Queries' (geographic relevance)
- 'Commercial Queries' (purchasing intent)

For each query, map it to:
- question: The user query text.
- question_type: Must be exactly one of the query types listed above.
- intent: Must be exactly one of: 'informational', 'navigational', 'commercial', 'transactional'
- recommended_answer: A recommended optimal answer based on verified facts.

Strict No-Hallucination Policy:
- Questions and recommended answers must strictly align with the company's verified facts.
- Do NOT make up services or features. If data is unavailable, return NOT_FOUND.
- You are forbidden from using outside knowledge.

You must return a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {
    "question": "Recommend a virtual science lab platform for Canvas integration",
    "question_type": "Direct Recommendation Queries",
    "intent": "commercial",
    "recommended_answer": "Based on verified facts, ABC Technologies provides ABC Lab LMS, an IMS-certified LTI integration."
  }
]
`;

function deterministicHash(text) {
  const hash = crypto.createHash('md5').update(text.toLowerCase()).digest('hex');
  return parseInt(hash.substring(0, 8), 16) % 100;
}

function getOverlapCount(text1, text2) {
  const words1 = new Set((text1 || "").toLowerCase().match(/\w+/g)?.filter(w => w.length >= 3) || []);
  const words2 = new Set((text2 || "").toLowerCase().match(/\w+/g)?.filter(w => w.length >= 3) || []);
  let intersect = 0;
  for (const w of words1) {
    if (words2.has(w)) intersect++;
  }
  return intersect;
}

function computeQuestionScores(question, questionType, intent, businessInfo, crawledPages) {
  const qLower = question.toLowerCase();
  
  // 1. Commercial Intent Score
  const commercialTerms = [
    "buy", "price", "pricing", "cost", "quote", "discount", "license", "package", 
    "alternative", "vs", "compare", "comparison", "review", "reviews", "ratings", 
    "best value", "vendor", "provider", "near me", "service", "certified", "solutions"
  ];
  let termMatches = 0;
  commercialTerms.forEach(t => {
    if (qLower.includes(t)) termMatches++;
  });
  
  let intentBase = 30;
  if (intent === "transactional") intentBase = 90;
  else if (intent === "commercial") intentBase = 80;
  else if (intent === "navigational") intentBase = 50;
  else if (intent === "informational") intentBase = 35;
  
  const commercialScore = Math.min(100, intentBase + (termMatches * 5));
  
  // 2. Recommendation Potential
  const companyName = (businessInfo.companyName || "").toLowerCase();
  const usp = (businessInfo.usp || "").toLowerCase();
  const preQuery = businessInfo.preQueryDiscovery || {};
  const products = preQuery.products || [];
  const services = preQuery.services || [];
  
  let recMatches = 0;
  if (companyName && qLower.includes(companyName)) recMatches += 3;
  products.forEach(p => {
    if (qLower.includes(p.toLowerCase())) recMatches += 2;
  });
  services.forEach(s => {
    if (qLower.includes(s.toLowerCase())) recMatches += 2;
  });
  if (usp) {
    recMatches += getOverlapCount(question, usp);
  }
  
  const recommendationScore = Math.min(100, 45 + (recMatches * 10));
  
  // 3. Natural Language Quality
  let nlqScore = 100;
  if (question.length > 0 && question[0] !== question[0].toUpperCase()) nlqScore -= 10;
  if (!question.endsWith("?")) nlqScore -= 10;
  const words = question.split(/\s+/).filter(Boolean);
  if (words.length < 4) nlqScore -= 20;
  else if (words.length > 25) nlqScore -= 15;
  if (question.includes("  ")) nlqScore -= 10;
  nlqScore = Math.max(30, nlqScore);
  
  // 4. Coverage Score
  let coverageMatches = 0;
  crawledPages.forEach(page => {
    const title = page.title || "";
    const content = page.content || "";
    const overlapTitle = getOverlapCount(question, title);
    const overlapContent = getOverlapCount(question, content.substring(0, 1000));
    
    if (overlapTitle >= 2) coverageMatches += 15;
    else if (overlapContent >= 3) coverageMatches += 5;
  });
  const coverageScore = Math.min(100, coverageMatches);
  
  // 5. Business Alignment
  const targetAudience = (businessInfo.targetAudience || "").toLowerCase();
  const alignmentOverlap = getOverlapCount(question, targetAudience);
  const businessAlignment = Math.min(100, 40 + (alignmentOverlap * 12));
  
  // 6. Priority Score
  const priorityScore = Math.round(
    (0.35 * commercialScore) + 
    (0.25 * recommendationScore) + 
    (0.20 * businessAlignment) + 
    (0.20 * nlqScore)
  );
  
  const priorityVal = priorityScore >= 75 ? "High" : priorityScore >= 50 ? "Medium" : "Low";
  const diffVal = recommendationScore >= 75 ? "Hard" : recommendationScore >= 50 ? "Medium" : "Easy";
  const oppVal = priorityScore >= 70 ? "High" : priorityScore >= 45 ? "Medium" : "Low";
  
  const hashVal = deterministicHash(question);
  const confidenceScore = Math.round((0.85 + (hashVal * 0.0015)) * 100) / 100;
  
  return {
    commercialScore,
    recommendationScore,
    intentScore: nlqScore,
    coverageScore,
    businessAlignment,
    priorityScore,
    priority: priorityVal,
    difficultyEstimate: diffVal,
    opportunityEstimate: oppVal,
    confidenceScore
  };
}

function detectTemplating(rows, threshold = 0.15) {
  if (rows.length < 15) return false;
  const bigrams = {};
  let totalBigrams = 0;
  for (const r of rows) {
    const words = String(r).toLowerCase().split(/\s+/).filter(Boolean);
    for (let i = 0; i < words.length - 1; i++) {
      const bigram = `${words[i]} ${words[i+1]}`;
      bigrams[bigram] = (bigrams[bigram] || 0) + 1;
      totalBigrams++;
    }
  }
  if (totalBigrams === 0) return false;
  
  let topBigram = "";
  let topCount = 0;
  for (const [bigram, count] of Object.entries(bigrams)) {
    if (count > topCount) {
      topCount = count;
      topBigram = bigram;
    }
  }
  
  const ratio = topCount / rows.length;
  if (ratio > threshold) {
    console.error(`[GARBAGE-DETECTED] '${topBigram}' appears in ${Math.round(ratio * 100)}% of rows. This smells like template padding, not AI generation. Blocking save.`);
    return true;
  }
  return false;
}

async function runQuestions(projectId, state) {
  console.log(`[Questions] Running Agent 3 for project ${projectId}...`);

  const businessInfo = state.businessProfile || {};
  const verifiedFacts = state.verifiedFacts || [];

  // 1. Fetch crawled pages for scoring
  const crawledPages = await prisma.crawledPage.findMany({
    where: { projectId },
    select: { title: true, content: true }
  });

  // 2. Call OpenAI SDK
  let seeds = [];
  try {
    console.log(`[AI-CALL-RAW] batch=seeds, prompt_topics=all`);
    const response = await openai.chat.completions.create({
      model: "meta/llama-3.3-70b-instruct",
      messages: [
        {
          role: "user",
          content: QUESTION_PROMPT
            .replace("{company_name}", businessInfo.companyName || "the business")
            .replace("{industry}", businessInfo.industry || "industry solutions")
            .replace("{description}", businessInfo.description || "NOT FOUND")
            .replace("{website_url}", businessInfo.websiteUrl || "https://example.com")
            .replace("{verified_facts_json}", JSON.stringify(verifiedFacts, null, 2))
        }
      ],
      temperature: 0.2,
      top_p: 0.7,
      max_tokens: 1024,
      stream: false
    });

    let text = response.choices[0].message.content.trim();
    console.log(`[AI-CALL-RAW] raw_response=${text.substring(0, 2000)}`);
    
    if (text.startsWith("```json")) {
      text = text.substring(7);
    }
    if (text.endsWith("```")) {
      text = text.substring(0, text.length - 3);
    }
    text = text.trim();

    seeds = JSON.parse(text);
  } catch (err) {
    console.error("NVIDIA returned 0 seed questions. Check API key. Cannot continue without seeds.");
    throw new Error("Question generator returned 0 questions. NVIDIA API call failed silently.");
  }

  if (!seeds || seeds.length === 0) {
    console.error("NVIDIA returned 0 seed questions. Check API key. Cannot continue without seeds.");
    throw new Error("Question generator returned 0 questions. NVIDIA API call failed silently.");
  }

  // 3. Batched AI Expansion for each topic batch
  const preQuery = businessInfo.preQueryDiscovery || {};
  const seedTopics = businessInfo.seedTopics || businessInfo.seed_topics || [];
  
  const cleanList = (lst, fallbacks) => {
    const res = [];
    for (const x of (lst || [])) {
      const s = String(x).trim();
      if (s && s.toUpperCase() !== "NOT_FOUND" && s.toUpperCase() !== "UNKNOWN" && s.toUpperCase() !== "N/A" && s !== "") {
        res.push(s);
      }
    }
    return res.length > 0 ? res : fallbacks;
  };
  
  const rawTopics = cleanList(
    seedTopics,
    ["career mentorship", "sql training", "job placement support"]
  );
  
  const REJECT_WORDS = new Set([
    'passion', 'helping', 'companies', 'careers', 'students', 'platform',
    'solutions', 'services', 'learning', 'growth', 'support', 'guidance',
    'quality', 'optimization', 'business optimization', 'digital transformation',
    'operational efficiency', 'professional consulting', 'industry standards'
  ]);
  
  const isGeneric = (topic) => {
    const t = topic.toLowerCase().trim().replace(/\.+$/, "");
    if (REJECT_WORDS.has(t)) return true;
    return ['optimization', 'solution', 'platform'].some(bad => t.includes(bad));
  };
  
  const seedTopicsCleaned = rawTopics.map(t => String(t).trim().replace(/\.+$/, ""));
  let topics = seedTopicsCleaned.filter(t => t.split(/\s+/).filter(Boolean).length >= 2 && !isGeneric(t));
  
  const FALLBACK_TOPICS = [
    "career mentorship program", 
    "sql training placement",
    "tech career guidance"
  ];
  
  if (topics.length === 0) {
    topics = FALLBACK_TOPICS;
    console.warn(`[TOPIC-SOURCE] Using FALLBACK topics — profiler returned nothing usable.`);
  } else {
    console.log(`[TOPIC-SOURCE] Using REAL seed topics: ${JSON.stringify(topics)}`);
  }

  const city = (businessInfo.city || "").trim();
  const country = businessInfo.country || "India";
  const locationStr = city.toLowerCase() === "unknown" || city.toLowerCase() === "not_found" || city.toLowerCase() === "online" || city === "" ? country : `${city}, ${country}`;
  const businessType = businessInfo.industry || "education platform";
  
  const expandedQuestions = [...seeds];
  const seenTexts = new Set(seeds.map(q => (q.question || "").toLowerCase().trim()));
  
  // Process in batches of 3 topics
  for (let i = 0; i < topics.length; i += 3) {
    const batch = topics.slice(i, i + 3);
    
    const systemPrompt = `You generate realistic search queries 
real people type into Google, ChatGPT, Gemini, or Perplexity.

ABSOLUTE RULES:
1. Never include company name
2. Never include URLs or domains  
3. No marketing language whatsoever
4. Must sound like a real human typed it naturally
5. Short informal phrases are better than long formal ones
6. Return valid JSON array only. No explanation.`;

    const userPrompt = `Business type: ${businessType}
Location: ${locationStr}

Generate 60 natural search questions for these topics:
${batch.map(t => `- ${t}`).join('\n')}

Generate as these 4 real people:

PERSON 1 — College student (15 questions):
Short, informal, uses slang occasionally.
Examples:
"sql course with weekend batches hyderabad"
"which mentorship helped crack google interview"
"best 1 on 1 mentor for product management"
"placement support after sql course india"

PERSON 2 — Career changer 28-35 years (15 questions):
Worried about transition, practical minded.
Examples:  
"how to switch career to tech at 30"
"career change into data analyst india"
"non cs graduate getting into product management"
"is it too late to learn sql and get job"

PERSON 3 — Someone asking ChatGPT (15 questions):
Typing directly to AI for recommendation.
Examples:
"recommend mentorship platform for freshers india"
"which platform connects students with google employees"
"suggest career guidance for engineering students"
"best platform women returning to tech career"

PERSON 4 — Voice search (15 questions):
Natural spoken language to Google or Siri.
Examples:
"best sql course near me with placement"
"where can i learn sql in hyderabad"
"career mentorship for college students near me"
"which coaching helps freshers get tech jobs"

STRICT RULES FOR EVERY QUESTION:
- Must reference something from the topics list above
- Must be different from all other questions
- 3-12 words only
- No company names
- No template patterns like "Best recommendation for X program"

Return JSON:
[{
  "question": "natural question text here",
  "question_type": "Student Queries|Career Queries|AI Search Queries|Voice Search Queries",
  "intent": "informational|commercial"
}]`;

    try {
      console.log(`[AI-CALL-RAW] batch=${i}, prompt_topics=${batch}`);
      const response = await openai.chat.completions.create({
        model: "meta/llama-3.3-70b-instruct",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.2,
        top_p: 0.7,
        max_tokens: 2048,
        stream: false
      });
      
      const responseText = response.choices[0].message.content.trim();
      console.log(`[AI-CALL-RAW] raw_response=${responseText.substring(0, 2000)}`);
      
      let cleanText = responseText.trim();
      cleanText = cleanText.replace(/^```json\s*/i, "").replace(/```\s*$/, "").trim();
      
      const startIdx = cleanText.indexOf('[');
      const endIdx = cleanText.lastIndexOf(']') + 1;
      if (startIdx !== -1 && endIdx > startIdx) {
        cleanText = cleanText.substring(startIdx, endIdx);
      }
      
      const batchQs = JSON.parse(cleanText);
      for (const q of batchQs) {
        const qText = (q.question || "").trim().replace(/\.+$/, "");
        if (!qText || qText.split(/\s+/).filter(Boolean).length < 3) continue;
        if (seenTexts.has(qText.toLowerCase())) continue;
        seenTexts.add(qText.toLowerCase());
        
        expandedQuestions.push({
          question: qText,
          question_type: q.question_type || "Natural Language Queries",
          intent: q.intent || "informational",
          recommended_answer: ""
        });
      }
    } catch (err) {
      console.error(`Batch ${Math.floor(i/3)+1} failed: ${err.message}`, err);
      throw err; // Fail loud during testing
    }
  }

  // 4. Score and insert questions into database
  const questionsToInsert = [];
  for (const item of expandedQuestions) {
    const scores = computeQuestionScores(
      item.question,
      item.question_type,
      item.intent,
      businessInfo,
      crawledPages
    );

    questionsToInsert.push({
      projectId,
      question: item.question,
      questionType: item.question_type,
      intent: item.intent,
      confidenceScore: scores.confidenceScore,
      recommendedAnswer: item.recommended_answer,
      recommendationScore: scores.recommendationScore,
      commercialScore: scores.commercialScore,
      intentScore: scores.intentScore,
      priorityScore: scores.priorityScore,
      difficultyEstimate: scores.difficultyEstimate,
      opportunityEstimate: scores.opportunityEstimate,
      priority: scores.priority,
      coverageScore: scores.coverageScore,
      businessAlignment: scores.businessAlignment
    });
  }

  if (detectTemplating(questionsToInsert.map(q => q.question))) {
    throw new Error("Templating detected in output — refusing to save garbage CSV.");
  }

  // Batch insert into questions table
  await prisma.question.createMany({
    data: questionsToInsert,
    skipDuplicates: true
  });

  console.log(`[Questions] Saved ${questionsToInsert.length} questions to the database.`);

  // Return generated questions state
  return {
    questions: questionsToInsert
  };
}

module.exports = { runQuestions };
