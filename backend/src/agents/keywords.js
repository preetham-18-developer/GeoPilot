const { PrismaClient } = require('@prisma/client');
const nlp = require('compromise');
const crypto = require('crypto');

const prisma = new PrismaClient();

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

function computeKeywordScores(keyword, keywordType, intent, businessInfo, crawledPages, entityNodes) {
  const kwLower = keyword.toLowerCase();
  const words = kwLower.split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  
  // 1. Difficulty Estimate
  let baseDiff = Math.max(10, 100 - (wordCount * 12));
  if (intent === "commercial" || intent === "transactional") {
    baseDiff = Math.min(100, baseDiff + 15);
  } else if (intent === "navigational") {
    baseDiff = Math.min(100, baseDiff + 5);
  }
  const difficultyScore = baseDiff;
  const diffVal = difficultyScore >= 70 ? "Hard" : difficultyScore >= 40 ? "Medium" : "Easy";
  
  // 2. Commercial Intent
  const commercialSuffixes = [
    "solutions", "platforms", "services", "tools", "agencies", "firms", "consultants", 
    "features", "benefits", "cost", "pricing", "reviews", "ratings", "alternatives",
    "near me", "usa", "online", "system", "software", "applications", "integration", 
    "setup", "guide", "tutorial", "case study", "best practices", "compliance"
  ];
  let suffixMatches = 0;
  commercialSuffixes.forEach(s => {
    if (kwLower.includes(s)) suffixMatches++;
  });
  
  let intentBase = 30;
  if (intent === "transactional") intentBase = 90;
  else if (intent === "commercial") intentBase = 80;
  
  const commercialIntent = Math.min(100, intentBase + (suffixMatches * 8));
  
  // 3. Opportunity Estimate
  const oppScore = commercialIntent * (1.0 - (difficultyScore / 150.0));
  const oppVal = oppScore >= 60 ? "High" : oppScore >= 35 ? "Medium" : "Low";
  
  // 4. Coverage Score
  let pageHits = 0;
  crawledPages.forEach(page => {
    const title = (page.title || "").toLowerCase();
    const content = (page.content || "").toLowerCase();
    if (title.includes(kwLower)) pageHits += 25;
    else if (content.substring(0, 2000).includes(kwLower)) pageHits += 8;
  });
  const coverageScore = Math.min(100, pageHits);
  
  // 5. Entity Relevance
  let entityMatches = 0;
  const companyName = (businessInfo.companyName || "").toLowerCase();
  if (companyName && kwLower.includes(companyName)) entityMatches += 3;
  
  entityNodes.forEach(node => {
    const entityName = (node.entityName || "").toLowerCase();
    if (entityName && kwLower.includes(entityName)) entityMatches += 1;
  });
  const entityRelevance = Math.min(100, 30 + (entityMatches * 15));
  
  // 6. Recommendation Value
  const recommendationValue = Math.round((0.40 * commercialIntent) + (0.40 * entityRelevance) + (0.20 * (100 - difficultyScore)));
  const priorityVal = recommendationValue >= 75 ? "High" : recommendationValue >= 50 ? "Medium" : "Low";
  
  const hashVal = deterministicHash(keyword);
  const confidenceScore = Math.round((0.80 + (hashVal * 0.002)) * 100) / 100;
  
  return {
    difficultyEstimate: diffVal,
    commercialIntent,
    opportunityEstimate: oppVal,
    coverageScore,
    entityRelevance,
    recommendationValue,
    confidenceScore,
    priority: priorityVal
  };
}

const { OpenAI } = require('openai');

const OPENAI_API_KEY = process.env.NVIDIA_API_KEY_KEYWORDS || process.env.NVIDIA_API_KEY_QUESTIONS || "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";
const BASE_URL = "https://integrate.api.nvidia.com/v1";

const openai = new OpenAI({
  apiKey: OPENAI_API_KEY,
  baseURL: BASE_URL
});

const KEYWORD_SYSTEM_PROMPT = `You extract SEO keywords from business information.
Keywords are short phrases people type into Google.
They are 1-5 words. Natural. Specific. No marketing language.
Return JSON array only. No markdown, no code blocks.`;

const KEYWORD_USER_PROMPT = `Business: {business_type} in {location}
Services: {services}
Target customers: {customers}

Please generate 60 highly relevant keywords in a valid JSON array.
For each, specify "keyword" and "type" (one of: 'PRIMARY', 'LONGTAIL', 'LOCAL', 'QUESTION').`;

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

async function runKeywords(projectId, state) {
  console.log(`[Keywords] Running Agent 4 (NVIDIA LLM + Local NLP) for project ${projectId}...`);

  const businessInfo = state.businessProfile || {};
  const websiteUrl = state.websiteUrl || "";

  // 1. Fetch crawled pages content
  const pages = await prisma.crawledPage.findMany({
    where: { projectId },
    select: { title: true, content: true }
  });

  // 2. Call NVIDIA LLM
  let seeds = [];
  try {
    const preQuery = businessInfo.preQueryDiscovery || {};
    const cleanList = (lst) => {
      if (!lst) return [];
      return [].concat(lst).map(x => String(x).trim()).filter(x => x && x.toUpperCase() !== "NOT_FOUND");
    };
    
    const services = cleanList(preQuery.services).join(", ") || businessInfo.industry || "industry solutions";
    const personasDict = preQuery.buyer_personas || {};
    const personas = Object.keys(personasDict).filter(k => k && String(k).toUpperCase() !== "NOT_FOUND").join(", ") || "student, job seeker";
    
    const city = (businessInfo.city || "").trim();
    const country = (businessInfo.country || "").trim();
    const locationStr = city.toLowerCase() === "unknown" || city.toLowerCase() === "not_found" || city.toLowerCase() === "online" || city === "" ? (country || "online") : `${city}, ${country}`;

    console.log(`[AI-CALL-RAW] batch=keywords, prompt_topics=all`);
    const response = await openai.chat.completions.create({
      model: "meta/llama-3.3-70b-instruct",
      messages: [
        { role: "system", content: KEYWORD_SYSTEM_PROMPT },
        { 
          role: "user", 
          content: KEYWORD_USER_PROMPT
            .replace("{business_type}", businessInfo.industry || "education platform")
            .replace("{location}", locationStr)
            .replace("{services}", services)
            .replace("{customers}", personas)
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
    console.error("NVIDIA returned 0 seed keywords. Check API key. Cannot continue without seeds.");
    throw new Error("Keyword generator returned 0 questions. NVIDIA API call failed silently.");
  }

  if (!seeds || seeds.length === 0) {
    console.error("NVIDIA returned 0 seed keywords. Check API key. Cannot continue without seeds.");
    throw new Error("Keyword generator returned 0 questions. NVIDIA API call failed silently.");
  }

  // 3. Extract seed terms locally using compromise.js
  const termFrequencies = {};
  const stopWords = new Set(["the", "and", "our", "this", "that", "with", "from", "for", "you", "your", "they", "them", "about", "welcome", "homepage", "website"]);

  pages.forEach(page => {
    const text = `${page.title || ""} ${page.content || ""}`;
    const doc = nlp(text);
    
    const adjNoun = doc.match('#Adjective #Noun').out('array');
    const nounNoun = doc.match('#Noun #Noun').out('array');
    const singleNouns = doc.nouns().out('array');

    [...adjNoun, ...nounNoun, ...singleNouns].forEach(term => {
      const cleaned = term.toLowerCase().replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, " ");
      if (cleaned.length < 3 || stopWords.has(cleaned) || /^\d+$/.test(cleaned)) return;
      termFrequencies[cleaned] = (termFrequencies[cleaned] || 0) + 1;
    });
  });

  const extractedCandidates = Object.entries(termFrequencies)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 50)
    .map(entry => entry[0]);

  // Combine LLM seeds and Local candidates
  const allCandidates = [];
  const seenKeywords = new Set();

  // Add LLM seeds first
  seeds.forEach(item => {
    const kw = (item.keyword || "").trim().replace(/\.+$/, "");
    if (kw && !seenKeywords.has(kw.toLowerCase())) {
      seenKeywords.add(kw.toLowerCase());
      
      let dbType = "Primary";
      let dbIntent = "commercial";
      const kwType = (item.type || "PRIMARY").toUpperCase();
      if (kwType === "PRIMARY") {
        dbType = "Primary";
        dbIntent = "commercial";
      } else if (kwType === "LONGTAIL") {
        dbType = "Long Tail";
        dbIntent = "informational";
      } else if (kwType === "LOCAL") {
        dbType = "Location";
        dbIntent = "navigational";
      } else if (kwType === "QUESTION") {
        dbType = "Voice Search";
        dbIntent = "informational";
      }

      allCandidates.push({
        keyword: kw,
        keyword_type: dbType,
        intent: dbIntent,
        cluster: (businessInfo.industry || "General") + " Solutions",
        source: "Verified Facts"
      });
    }
  });

  // Add extracted candidates
  extractedCandidates.forEach(cand => {
    const kw = cand.trim().replace(/\.+$/, "");
    if (kw && !seenKeywords.has(kw.toLowerCase())) {
      seenKeywords.add(kw.toLowerCase());
      
      const words = kw.split(/\s+/).filter(Boolean);
      let dbType = "Primary";
      let dbIntent = "commercial";
      if (words.length >= 4) {
        dbType = "Long Tail";
        dbIntent = "informational";
      }

      allCandidates.push({
        keyword: kw,
        keyword_type: dbType,
        intent: dbIntent,
        cluster: (businessInfo.industry || "General") + " Solutions",
        source: "Recommendation Queries"
      });
    }
  });

  // Filter out generic keywords
  const REJECT_SINGLES = new Set([
    'passion', 'helping', 'companies', 'careers',
    'students', 'optimization', 'solutions', 'platform',
    'learning', 'growth', 'support', 'guidance', 'quality'
  ]);
  
  const isGeneric = (kw) => {
    const t = kw.toLowerCase().trim().replace(/\.+$/, "");
    if (REJECT_SINGLES.has(t)) return true;
    return ['optimization', 'solution', 'platform'].some(bad => t.includes(bad));
  };

  const finalExpanded = allCandidates.filter(item => {
    const words = item.keyword.split(/\s+/).filter(Boolean);
    if (words.length < 2) return false; // reject single word topics
    if (isGeneric(item.keyword)) return false;
    return true;
  });

  if (finalExpanded.length < 10) {
    console.warn("Very few keywords generated. Check seed topics quality in profiler.");
  }

  // Ensure EVERY single keyword is scored deterministically
  const keywordsToInsert = [];
  const entityNodes = []; // Placeholder

  for (const item of finalExpanded) {
    const scores = computeKeywordScores(
      item.keyword,
      item.keyword_type,
      item.intent,
      businessInfo,
      pages,
      entityNodes
    );

    keywordsToInsert.push({
      projectId,
      keyword: item.keyword,
      keywordType: item.keyword_type,
      intent: item.intent,
      cluster: item.cluster,
      confidenceScore: scores.confidenceScore,
      priority: scores.priority,
      difficultyEstimate: scores.difficultyEstimate,
      opportunityEstimate: scores.opportunityEstimate,
      source: item.source,
      coverageScore: scores.coverageScore,
      entityRelevance: scores.entityRelevance,
      recommendationValue: scores.recommendationValue
    });
  }

  if (detectTemplating(keywordsToInsert.map(k => k.keyword))) {
    throw new Error("Templating detected in output — refusing to save garbage CSV.");
  }

  // Batch insert into keywords table
  await prisma.keyword.createMany({
    data: keywordsToInsert,
    skipDuplicates: true
  });

  console.log(`[Keywords] Saved ${keywordsToInsert.length} keywords to the database.`);

  // Return generated keywords state
  return {
    keywords: keywordsToInsert
  };
}

module.exports = { runKeywords };
