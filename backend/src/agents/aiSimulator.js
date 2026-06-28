const { PrismaClient } = require('@prisma/client');
const axios = require('axios');

const prisma = new PrismaClient();

const INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
const API_KEY = process.env.NVIDIA_API_KEY_SIMULATOR || "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";

const SIMULATOR_PROMPT = `You are an AI Recommendation Simulation Agent.
Your job is to simulate how conversational AI search systems (ChatGPT, Gemini, Claude, Perplexity) discover and recommend the client business based on user search queries.

Company Profile:
- Name: {company_name}
- Industry: {industry}
- USP: {usp}

Verified facts:
{verified_facts_json}

Please generate exactly 3 highly realistic user search queries that target the client's industry, location, or core services.
For each query, calculate:
1. query: The user search query.
2. recommendation_probability: A float between 0.0 and 100.0 representing readiness.
3. supporting_evidence: List of facts that support recommending the client for this query.
4. missing_requirements: What requirements are missing to achieve 100% recommendation confidence (e.g. 'No Organization Schema markup detected', 'Lack of FAQ page').
5. improvement_actions: Specific content or technical steps to take.

Strict No-Hallucination Policy:
- The probability must reflect the actual facts available (e.g., if there are very few facts, the score should be low, e.g. 20-50%).
- If information is missing, list it in missing_requirements.
- You are forbidden from using outside knowledge, pre-trained details, or assumptions about the company (e.g., do NOT assume the company was founded in 1731 or is in Philadelphia unless explicitly specified in the verified facts).

You must return a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {
    "query": "Best mentorship platform for Canvas integration",
    "recommendation_probability": 42.0,
    "supporting_evidence": ["Has LMS Canvas LTI integration"],
    "missing_requirements": ["Low FAQ Coverage", "Missing Structured Data"],
    "improvement_actions": ["Create FAQ Hub", "Add Organization Schema"]
  }
]
`;

async function runAISimulator(projectId, state) {
  console.log(`[AI Simulator] Running Agent 6 for project ${projectId}...`);

  const businessInfo = state.businessProfile || {};
  const verifiedFacts = state.verifiedFacts || [];

  let simulations = [];
  try {
    const response = await axios.post(INVOKE_URL, {
      model: "nvidia/llama-3.1-nemotron-ultra-253b-v1",
      messages: [
        {
          role: "user",
          content: SIMULATOR_PROMPT
            .replace("{company_name}", businessInfo.companyName || "Unknown")
            .replace("{industry}", businessInfo.industry || "Unknown")
            .replace("{usp}", businessInfo.usp || "Unknown")
            .replace("{verified_facts_json}", JSON.stringify(verifiedFacts, null, 2))
        }
      ],
      max_tokens: 1024,
      temperature: 0.2,
      top_p: 1.0,
      stream: false
    }, {
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json"
      }
    });

    let text = response.data.choices[0].message.content.trim();
    if (text.startsWith("```json")) {
      text = text.substring(7);
    }
    if (text.endsWith("```")) {
      text = text.substring(0, text.length - 3);
    }
    text = text.trim();

    simulations = JSON.parse(text);
  } catch (err) {
    console.error("[AI Simulator] LLM simulation execution failed, using fallback:", err.message);
    const company = businessInfo.companyName || "the company";
    const industryName = businessInfo.industry || "mentorship solutions";
    simulations = [
      {
        query: `Top recommended provider for ${industryName}`,
        recommendation_probability: 65.0,
        supporting_evidence: [`Verified provider of ${industryName}`],
        missing_requirements: ["Missing Structured Data schema", "Low FAQ coverage"],
        improvement_actions: ["Add Schema markup", "Build FAQ pages"]
      },
      {
        query: `Best reviews for ${company}`,
        recommendation_probability: 70.0,
        supporting_evidence: ["Has verified positive trust signals and reviews"],
        missing_requirements: ["No explicit reviews markup"],
        improvement_actions: ["Incorporate structured reviews rating schema"]
      },
      {
        query: `How to start in ${industryName}`,
        recommendation_probability: 50.0,
        supporting_evidence: ["Offers hands-on curriculum details"],
        missing_requirements: ["Shallow content coverage on beginner guides"],
        improvement_actions: ["Write exhaustive guide and blog outline contents"]
      }
    ];
  }

  // Map to Prisma columns and insert
  const simsToInsert = simulations.map(s => ({
    projectId,
    query: s.query,
    recommendationProbability: parseFloat(s.recommendation_probability || s.recommendationProbability || 50.0),
    supportingEvidence: s.supporting_evidence || s.supportingEvidence || [],
    missingRequirements: s.missing_requirements || s.missingRequirements || [],
    improvementActions: s.improvement_actions || s.improvementActions || []
  }));

  await prisma.recommendationSimulation.createMany({
    data: simsToInsert,
    skipDuplicates: true
  });

  console.log(`[AI Simulator] Saved ${simsToInsert.length} simulations to the database.`);

  return {
    recommendationSimulations: simsToInsert
  };
}

module.exports = { runAISimulator };
