const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function runReport(projectId, state) {
  console.log(`[Report] Running Agent 8 (Local Math) for project ${projectId}...`);

  const businessInfo = state.businessProfile || {};
  const verifiedFacts = state.verifiedFacts || [];
  const questions = state.questions || [];
  const keywords = state.keywords || [];
  const competitors = state.competitors || [];

  // SWOT parameters
  const strengths = businessInfo.strengths || [];
  const weaknesses = businessInfo.weaknesses || [];
  const opportunities = businessInfo.opportunities || [];
  const risks = businessInfo.risks || [];

  const reportContent = {
    industry: businessInfo.industry || "Unknown",
    executive_summary: businessInfo.description || "No description compiled",
    business_overview: `Mission: ${businessInfo.mission || "NOT FOUND"}\nVision: ${businessInfo.vision || "NOT FOUND"}\nUSP: ${businessInfo.usp || "NOT FOUND"}`,
    product_analysis: `USP: ${businessInfo.usp || "NOT FOUND"}`,
    service_analysis: `Target Audience: ${businessInfo.targetAudience || "NOT FOUND"}`,
    trust_analysis: `Verified Facts and Audited Credentials`,
    swot: {
      strengths,
      weaknesses,
      opportunities,
      threats: risks
    },
    ai_visibility_analysis: `GEO Targets: ${opportunities.join(', ')}`,
    total_verified_facts: verifiedFacts.length,
    total_questions_discovered: questions.length,
    total_keywords_strategized: keywords.length,
    total_competitors_discovered: competitors.length
  };

  // Save Report to database
  const report = await prisma.report.create({
    data: {
      projectId,
      reportType: "Full Analysis",
      reportTitle: `${businessInfo.companyName || "Company"} Brand Visibility Intelligence Audit`,
      reportContent: reportContent,
      generatedBy: "Report Compiler Agent"
    }
  });

  console.log(`[Report] Report compiled and saved: ${report.reportTitle}`);

  return {
    report: reportContent
  };
}

module.exports = { runReport };
