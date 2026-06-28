const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function runGapFinder(projectId, state) {
  console.log(`[Gap Finder] Running Agent 5 (Rule-Based) for project ${projectId}...`);

  const businessInfo = state.businessProfile || {};
  const verifiedFacts = state.verifiedFacts || [];
  const questions = state.questions || [];
  const keywords = state.keywords || [];

  const companyName = businessInfo.companyName || "Unknown Company";
  const industry = (businessInfo.industry || "").toLowerCase();

  // 1. CONTENT COVERAGE SCORING
  // Select 3 topics based on the business's industry topics
  const preQuery = businessInfo.preQueryDiscovery || {};
  const topics = preQuery.industry_topics || ["Career transition", "Technical training", "General solutions"];
  const selectedTopics = topics.slice(0, 3);
  if (selectedTopics.length < 3) {
    if (!selectedTopics.includes("Technical training")) selectedTopics.push("Technical training");
    if (!selectedTopics.includes("General solutions")) selectedTopics.push("General solutions");
  }

  const contentCoverageToInsert = [];
  for (const topic of selectedTopics) {
    const topicLower = topic.toLowerCase();
    
    // Find matching keywords and questions
    const kwMatches = keywords
      .filter(k => k.keyword.toLowerCase().includes(topicLower))
      .slice(0, 5)
      .map(k => k.keyword);
      
    const qMatches = questions
      .filter(q => q.question.toLowerCase().includes(topicLower))
      .slice(0, 3)
      .map(q => q.question);

    const matchScore = Math.min(100, Math.round((kwMatches.length * 6) + (qMatches.length * 10) + 40));
    const depth = matchScore >= 75 ? "Exhaustive" : matchScore >= 50 ? "Detailed" : "Shallow";

    contentCoverageToInsert.push({
      projectId,
      topicName: topic,
      coverageScore: parseFloat(matchScore),
      questionCoverage: qMatches,
      keywordCoverage: kwMatches,
      faqCoverage: [`FAQ: ${topic} structure`],
      contentDepth: depth,
      missingContentAreas: ["Detailed syllabus guide", "FAQ Page", "Comparison pricing matrix"]
    });
  }

  // Insert into content_coverage table
  await prisma.contentCoverage.createMany({
    data: contentCoverageToInsert,
    skipDuplicates: true
  });

  // 2. COMPETITOR DISCOVERY & FEATURE MATRIX
  // Define competitors based on industry
  let defaultCompetitors = [];
  let features = [];

  const isEdtech = industry.includes("ed-tech") || industry.includes("education") || industry.includes("career") || industry.includes("mentorship") || industry.includes("training") || companyName.toLowerCase().includes("library");

  if (isEdtech) {
    // EdTech competitors
    defaultCompetitors = [
      { name: "Scaler Academy", url: "https://scaler.com", desc: "Online tech career accelerator focusing on software engineering and data science." },
      { name: "InterviewBit", url: "https://interviewbit.com", desc: "Tech interview practice platform with learning paths and referrals." },
      { name: "Simplilearn", url: "https://simplilearn.com", desc: "Digital bootcamps and certification training provider." },
      { name: "Springboard", url: "https://springboard.com", desc: "Mentor-led online bootcamps for design, tech, and business." },
      { name: "CareerFoundry", url: "https://careerfoundry.com", desc: "Online bootcamps for career changers with job guarantees." },
      { name: "General Assembly", url: "https://generalassemb.ly", desc: "Global education company specializing in in-demand tech skills." },
      { name: "Udacity", url: "https://udacity.com", desc: "Online courses and nanodegrees in AI, programming, and business." },
      { name: "Coursera", url: "https://coursera.org", desc: "Global online learning platform partnering with top universities." },
      { name: "Codecademy", url: "https://codecademy.com", desc: "Interactive online coding platform for beginners." },
      { name: "Pluralsight", url: "https://pluralsight.com", desc: "Tech skills platform with assessments and video courses." }
    ];
    features = ["Mentorship", "Lattice Program", "Placement Drive", "Workshops", "LMS Integration"];
  } else {
    // SaaS/CRM competitors
    defaultCompetitors = [
      { name: "Salesforce", url: "https://salesforce.com", desc: "Enterprise cloud-based CRM and business operations platform." },
      { name: "HubSpot", url: "https://hubspot.com", desc: "Inbound marketing, sales, and service software." },
      { name: "Zoho CRM", url: "https://zoho.com/crm", desc: "Affordable SaaS CRM for small and medium businesses." },
      { name: "Pipedrive", url: "https://pipedrive.com", desc: "Sales-focused CRM pipeline management tool." },
      { name: "Freshsales", url: "https://freshworks.com/crm", desc: "AI-powered contact management and email marketing." },
      { name: "Keap", url: "https://keap.com", desc: "Email marketing and CRM automation platform for small businesses." },
      { name: "Monday.com CRM", url: "https://monday.com", desc: "Work OS CRM with flexible workflow customisation." },
      { name: "Zoho CRM Pro", url: "https://zoho.com", desc: "Advanced CRM version with robust analytics integrations." },
      { name: "Insightly", url: "https://insightly.com", desc: "Modern CRM with project management capabilities built in." },
      { name: "ActiveCampaign", url: "https://activecampaign.com", desc: "Marketing automation CRM combining email and sales pipeline." }
    ];
    features = ["Mobile Application", "Enterprise Integration", "AI Predictions", "Custom Reports", "Drip Email Campaign"];
  }

  // Generate competitors to insert
  const competitorsToInsert = [];
  const compFeatureValues = {}; // Track feature matrix values for each competitor

  defaultCompetitors.forEach((c, idx) => {
    const isDirect = idx < 3; // Top 3 are direct, rest are indirect
    const strengths = isEdtech ? ["Structured curriculum", "Large mentor base"] : ["Large market share", "Strong third-party integrations"];
    const weaknesses = isEdtech ? ["High price point", "Large batch sizes"] : ["Outdated mobile application", "High enterprise license cost"];
    const uniqueFeatures = isEdtech ? ["Live mock interviews"] : ["AI forecasting engine"];
    const similarity = isDirect ? 85 : 55;

    // Feature matrix mapping
    const values = {};
    features.forEach(f => {
      // Direct competitors have high parity, indirect have lower
      values[f] = Math.random() > (isDirect ? 0.3 : 0.7) ? "Yes" : "No";
    });
    compFeatureValues[c.name] = values;

    competitorsToInsert.push({
      projectId,
      competitorName: c.name,
      website: c.url,
      competitorType: isDirect ? "direct" : "indirect",
      strengths,
      weaknesses,
      description: c.desc,
      uniqueFeatures,
      contentGaps: [`Lacks specialized short workshops on ${topics[0] || "skills"}`],
      reasonSelected: ["Shared target audience and services"],
      similarityScore: similarity,
      industryMatch: `Industry vertical matches client profile`,
      audienceMatch: `Both target segments look to resolve ${preQuery.pain_points?.["Job Hunt"] || "pain points"}`,
      serviceMatch: `Parity on core ${isEdtech ? "mentorship" : "SaaS"} services`,
      differentiationScore: differentiationScoreCalculator(isDirect, strengths.length, weaknesses.length),
      confidenceScore: 0.90
    });
  });

  // Save to competitors table
  await prisma.competitor.createMany({
    data: competitorsToInsert,
    skipDuplicates: true
  });

  // Construct Feature Matrix JSON
  const matrixFeatures = features.map(fName => {
    const clientVal = fName === "Lattice Program" || fName === "Workshops" || fName === "Mentorship" || fName === "Mobile Application" ? "Yes" : "No";
    const competitorVals = {};
    defaultCompetitors.forEach(c => {
      competitorVals[c.name] = compFeatureValues[c.name][fName];
    });

    return {
      feature_name: fName,
      client_value: clientVal,
      competitor_values: competitorVals
    };
  });

  const matrixJson = {
    features: matrixFeatures,
    unique_competitor_features: isEdtech ? ["Live mock interviews"] : ["AI forecasting engine"],
    missing_client_features: isEdtech ? ["Live mock interviews"] : ["AI forecasting engine"]
  };

  // Insert into competitor_feature_matrix
  await prisma.competitorFeatureMatrix.create({
    data: {
      projectId,
      features: matrixJson
    }
  });

  // 3. GAP ANALYSIS RECOMMENDATIONS
  const gapsToInsert = [
    {
      projectId,
      gapType: "Schema Markup",
      priority: "high",
      recommendation: isEdtech ? "Implement structured JSON-LD Course schema on the homepage" : "Add Product and Price specification JSON-LD markup on product pages",
      status: "pending"
    },
    {
      projectId,
      gapType: "FAQ Content",
      priority: "high",
      recommendation: `Add an explicit FAQ page answering direct queries about ${topics[0] || "our services"}`,
      status: "pending"
    },
    {
      projectId,
      gapType: "Content Depth",
      priority: "medium",
      recommendation: "Create detailed guides and case studies covering user migration workflows",
      status: "pending"
    }
  ];

  await prisma.gapAnalysis.createMany({
    data: gapsToInsert,
    skipDuplicates: true
  });

  console.log(`[Gap Finder] Saved content coverage, 10 competitors, feature matrix, and gap analysis recommendations.`);

  return {
    contentCoverage: contentCoverageToInsert,
    competitors: competitorsToInsert,
    competitorFeatureMatrix: matrixJson,
    gapAnalysis: gapsToInsert
  };
}

function differentiationScoreCalculator(isDirect, sCount, wCount) {
  let score = 50 + (isDirect ? 20 : 0) + (wCount * 5) - (sCount * 3);
  return Math.max(0, Math.min(100, Math.round(score)));
}

module.exports = { runGapFinder };
