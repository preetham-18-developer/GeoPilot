const { PrismaClient } = require('@prisma/client');
const crypto = require('crypto');

const prisma = new PrismaClient();

async function runQA(projectId, state) {
  console.log(`[QA] Running Agent 7 (Rules-Based) for project ${projectId}...`);

  const verifiedFacts = state.verifiedFacts || [];
  const runId = state.runId || crypto.randomUUID();

  // 1. Programmatic Audits
  let missingEvidenceCount = 0;
  let lowConfidenceCount = 0;
  let duplicatesCount = 0;

  const seenKeys = new Set();

  verifiedFacts.forEach(fact => {
    // Check missing evidence
    const evidence = (fact.evidence_text || "").trim();
    if (!evidence || evidence.toUpperCase() === "NOT FOUND" || evidence.toUpperCase() === "UNKNOWN") {
      missingEvidenceCount++;
    }

    // Check confidence score
    if ((fact.confidence_score || fact.confidenceScore || 0.0) < 0.70) {
      lowConfidenceCount++;
    }

    // Check duplicate key
    const key = `${fact.fact_category || "general"}-${fact.fact_key || "key"}-${fact.fact_value || "value"}`.toLowerCase();
    if (seenKeys.has(key)) {
      duplicatesCount++;
    } else {
      seenKeys.add(key);
    }
  });

  // Calculate deductions
  const deductions = (missingEvidenceCount * 10) + (duplicatesCount * 5) + (lowConfidenceCount * 10);
  const finalQaScore = Math.max(0, Math.min(100, 100 - deductions));

  // Determine approval status
  let approvalStatus = "approved";
  if (finalQaScore < 70 || missingEvidenceCount > 0) {
    approvalStatus = "flagged";
  }

  const checks = {
    missing_evidence_count: missingEvidenceCount,
    duplicate_facts_count: duplicatesCount,
    low_confidence_facts_count: lowConfidenceCount,
    unsupported_claims: []
  };

  // 2. Save QAReport to database
  const qaReport = await prisma.qAReport.create({
    data: {
      projectId,
      runId,
      approvalStatus,
      qaScore: parseFloat(finalQaScore),
      checks: checks
    }
  });

  console.log(`[QA] Report generated. Status: ${approvalStatus}, Score: ${finalQaScore}`);

  return {
    qaReport: {
      id: qaReport.id,
      approvalStatus,
      qaScore: finalQaScore,
      checks
    }
  };
}

module.exports = { runQA };
