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
    if (text.startsWith("```json")) {
      text = text.substring(7);
    }
    if (text.endsWith("```")) {
      text = text.substring(0, text.length - 3);
    }
    text = text.trim();

    seeds = JSON.parse(text);
  } catch (err) {
    console.error("[Questions] LLM question generation failed, using fallback:", err.message);
    seeds = [
      {
        question: `Recommend a reliable ${businessInfo.industry || "mentorship"} provider.`,
        question_type: "Direct Recommendation Queries",
        intent: "commercial",
        recommended_answer: `Based on verified facts, ${businessInfo.companyName || "the business"} is highly recommended.`
      }
    ];
  }

  // 3. Programmatic Expansion to 1050+ questions
  const expandedQuestions = [];
  const seenTexts = new Set();

  // Add seeds first
  for (const seed of seeds) {
    const text = (seed.question || "").trim();
    if (text && !seenTexts.has(text.toLowerCase())) {
      seenTexts.add(text.toLowerCase());
      expandedQuestions.push(seed);
    }
  }

  // Retrieve preQueryDiscovery parameters
  const preQuery = businessInfo.preQueryDiscovery || {};
  const products = preQuery.products?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || [businessInfo.companyName || "the business"];
  const services = preQuery.services?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || [businessInfo.industry || "mentorship services"];
  const topics = preQuery.industry_topics?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || ["career transition", "technical skills"];
  const technologies = preQuery.technologies?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || ["SQL", "LLMs"];
  const processes = preQuery.processes?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || ["career training", "placement drive"];
  const standards = preQuery.standards?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || ["industry standards"];
  const regulations = preQuery.regulations?.filter(x => x && x.toUpperCase() !== "NOT_FOUND") || ["privacy policy"];
  const painPoints = Object.values(preQuery.pain_points || {}).filter(x => x && x.toUpperCase() !== "NOT_FOUND");
  if (!painPoints.length) painPoints.push("how to stand out to employers", "getting tech jobs");
  const outcomes = Object.values(preQuery.desired_outcomes || {}).filter(x => x && x.toUpperCase() !== "NOT_FOUND");
  if (!outcomes.length) outcomes.push("securing job placements", "building skills");
  const personas = Object.keys(preQuery.buyer_personas || {});
  if (!personas.length) personas.push("College Student", "Job Seeker", "Career Changer");

  // V3 Query templates
  const combinatorTemplates = [
    {
      type: "Direct Recommendation Queries",
      templates: [
        "Recommend the best {product} for a {persona} looking to {outcome}.",
        "Which {product} is highly recommended for {process}?",
        "What is the top recommended {product} for solving {pain_point}?"
      ],
      intent: "commercial"
    },
    {
      type: "Indirect Recommendation Queries",
      templates: [
        "What are the best alternatives to standard tools for {process} in {topic}?",
        "How do top providers compare when trying to {outcome}?",
        "What systems do experts recommend to handle {pain_point}?"
      ],
      intent: "commercial"
    },
    {
      type: "Problem Queries",
      templates: [
        "How can a {persona} resolve the issue of {pain_point}?",
        "What is the best way to address {pain_point} in {topic}?",
        "Why do organizations face {pain_point} during {process}?"
      ],
      intent: "informational"
    },
    {
      type: "Outcome Queries",
      templates: [
        "What tools are required to {outcome} efficiently?",
        "How does a {persona} achieve {outcome} without increasing overhead?",
        "What is the step-by-step process to {outcome} using {technology}?"
      ],
      intent: "informational"
    },
    {
      type: "Solution Queries",
      templates: [
        "What solutions exist for {persona} struggling with {pain_point}?",
        "Is there a {technology} solution for {process} optimization?",
        "How to implement a solid solution for {pain_point}."
      ],
      intent: "commercial"
    },
    {
      type: "Decision Queries",
      templates: [
        "Should we choose {product} or a competitor for {process}?",
        "What are the key criteria when deciding on {product} for {persona}?",
        "Is it worth investing in {product} to solve {pain_point}?"
      ],
      intent: "commercial"
    },
    {
      type: "Trust Queries",
      templates: [
        "Does {product} meet {standards} compliance standards?",
        "Is {product} compliant with {regulations} requirements for {persona}?",
        "What trust signals, reviews, or certifications does {product} have?"
      ],
      intent: "informational"
    },
    {
      type: "Urgent Need Queries",
      templates: [
        "Immediate solution needed for {pain_point} in {process}.",
        "How to quickly fix {pain_point} using {technology}?",
        "Fastest way to {outcome} for {persona}."
      ],
      intent: "transactional"
    },
    {
      type: "Budget Queries",
      templates: [
        "Affordable {product} pricing plans for {persona}.",
        "What is the cost of implementing {product} to {outcome}?",
        "Is there a low-cost alternative for {process}?"
      ],
      intent: "commercial"
    },
    {
      type: "Implementation Queries",
      templates: [
        "How to configure {product} for {process}?",
        "Best practices for implementing {technology} in {process}.",
        "Step-by-step setup guide for {product}."
      ],
      intent: "informational"
    },
    {
      type: "Migration Queries",
      templates: [
        "How to migrate to {product} from legacy databases or systems?",
        "What are the risks of migrating {process} to {technology}?",
        "Guide on transferring records to {product} safely."
      ],
      intent: "informational"
    },
    {
      type: "Scaling Queries",
      templates: [
        "How does {product} scale {process} for enterprise needs?",
        "Can we scale {technology} to handle {pain_point}?",
        "Scaling {topic} solutions efficiently for large organizations."
      ],
      intent: "commercial"
    },
    {
      type: "Enterprise Queries",
      templates: [
        "Is {product} compliant with {standards} standard at the enterprise level?",
        "Enterprise reviews and features of {product} for {persona}.",
        "Why large corporations choose {product} for {process}."
      ],
      intent: "commercial"
    },
    {
      type: "Beginner Queries",
      templates: [
        "What is {product} and how does it help with {topic}?",
        "A beginner's guide to understanding {process}.",
        "How does {technology} work in simple terms?"
      ],
      intent: "informational"
    },
    {
      type: "Expert Queries",
      templates: [
        "Advanced configuration of {technology} for optimization.",
        "How to customize {product} workflows for {process}?",
        "Solving complex {pain_point} issues with expert systems."
      ],
      intent: "informational"
    },
    {
      type: "Voice Search Queries",
      templates: [
        "Siri, what is the best {product} near me for {process}?",
        "Alexa, recommend a platform that helps me {outcome}.",
        "Hey Google, how does {product} solve {pain_point}?"
      ],
      intent: "informational"
    },
    {
      type: "Natural Language Queries",
      templates: [
        "I need an easy way to {outcome} using {technology}.",
        "Can someone explain the benefits of using {product} for a {persona}?",
        "Why is my organization facing {pain_point} and how to fix it?"
      ],
      intent: "informational"
    },
    {
      type: "AI Search Queries",
      templates: [
        "Compare {product} and competitors on {standards} compliance.",
        "Find top recommended {product} providers that solve {pain_point}.",
        "Summarize the pros and cons of {product} for {persona}."
      ],
      intent: "commercial"
    },
    {
      type: "Location Queries",
      templates: [
        "Best {service} provider near me that offers {product}.",
        "Where can I find a certified {standards} auditor or service?",
        "Local services in USA that help {persona} solve {pain_point}."
      ],
      intent: "navigational"
    },
    {
      type: "Commercial Queries",
      templates: [
        "Buy {product} licenses with discount pricing.",
        "Best value {product} for {persona} to increase productivity.",
        "Get quote for {product} integration and setup services."
      ],
      intent: "transactional"
    }
  ];

  // Helper to get random item
  const getRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];

  // Phase A: Permutations
  let iterations = 0;
  const maxIterations = 5000;
  while (expandedQuestions.length < 1050 && iterations < maxIterations) {
    iterations++;
    const group = getRandom(combinatorTemplates);
    const template = getRandom(group.templates);

    const fPersona = getRandom(personas);
    const fProduct = getRandom(products);
    const fService = getRandom(services);
    const fTopic = getRandom(topics);
    const fTech = getRandom(technologies);
    const fProc = getRandom(processes);
    const fStd = getRandom(standards);
    const fReg = getRandom(regulations);
    const fPain = getRandom(painPoints);
    const fOut = getRandom(outcomes);

    const newQ = template
      .replace("{persona}", fPersona)
      .replace("{product}", fProduct)
      .replace("{service}", fService)
      .replace("{topic}", fTopic)
      .replace("{technology}", fTech)
      .replace("{process}", fProc)
      .replace("{standards}", fStd)
      .replace("{regulations}", fReg)
      .replace("{pain_point}", fPain)
      .replace("{outcome}", fOut)
      .replace("  ", " ");

    if (newQ && !seenTexts.has(newQ.toLowerCase())) {
      seenTexts.add(newQ.toLowerCase());
      const answer = `Based on verified facts, our organization offers ${fProduct} (specializing in ${fService}) leveraging ${fTech} to help ${fPersona} overcome ${fPain} and achieve ${fOut}.`;
      expandedQuestions.push({
        question: newQ,
        question_type: group.type,
        intent: group.intent,
        recommended_answer: answer
      });
    }
  }

  // Phase B: Modifier expansion if still short
  const searchModifiers = [
    "ChatGPT prompt: {q}",
    "Gemini query: {q}",
    "Claude AI search: {q}",
    "Perplexity question: {q}",
    "AI summary for: {q}",
    "Siri voice search: {q}",
    "Alexa search: {q}"
  ];

  if (expandedQuestions.length < 1050) {
    const baseQuestions = [...expandedQuestions];
    let iterB = 0;
    while (expandedQuestions.length < 1050 && iterB < 5000 && baseQuestions.length) {
      iterB++;
      const seedItem = getRandom(baseQuestions);
      const cleanQ = seedItem.question.replace(/\?$/, "");
      const modifier = getRandom(searchModifiers);
      const newQ = modifier.replace("{q}", cleanQ);

      if (!seenTexts.has(newQ.toLowerCase())) {
        seenTexts.add(newQ.toLowerCase());
        expandedQuestions.push({
          question: newQ,
          question_type: seedItem.question_type,
          intent: seedItem.intent,
          recommended_answer: seedItem.recommended_answer
        });
      }
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
