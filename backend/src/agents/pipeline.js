const { PrismaClient } = require('@prisma/client');
const { runProfiler } = require('./profiler');
const { runQuestions } = require('./questions');
const { runKeywords } = require('./keywords');
const { runGapFinder } = require('./gapFinder');
const { runAISimulator } = require('./aiSimulator');
const { runQA } = require('./qa');
const { runReport } = require('./report');

const prisma = new PrismaClient();

async function runAgentPipeline(projectId, io = null, socketId = null) {
  const emit = (event, data) => {
    if (io && socketId) {
      io.to(socketId).emit(event, data);
    }
  };

  const updateStatus = async (status, currentAgent) => {
    try {
      await prisma.project.update({
        where: { id: projectId },
        data: { status, currentAgent }
      });
      // Also emit a streaming status change event for the client dashboard
      emit('agent:stream', {
        message: `🔄 Stage: ${status} | Agent: ${currentAgent || 'None'}`,
        type: 'info'
      });
    } catch (err) {
      console.error(`[Pipeline] Failed to update project status:`, err.message);
    }
  };

  const state = {
    projectId,
    runId: require('crypto').randomUUID(),
    businessProfile: {},
    verifiedFacts: [],
    questions: [],
    keywords: [],
    competitors: [],
    competitorFeatureMatrix: {},
    contentCoverage: [],
    gapAnalysis: [],
    recommendationSimulations: [],
    qaReport: {},
    report: {}
  };

  console.log(`[Pipeline] Starting sequential agent network for project ${projectId}...`);
  emit('agent:stream', { message: '🧠 Initializing multi-agent intelligence pipeline...', type: 'info' });

  try {
    // 0. Clean up stale analysis records
    await updateStatus('extracting', 'Database Cleanup');
    await prisma.verifiedFact.deleteMany({
      where: { extractedFact: { projectId } }
    });
    await prisma.extractedFact.deleteMany({ where: { projectId } });
    await prisma.businessProfile.deleteMany({ where: { projectId } });
    await prisma.question.deleteMany({ where: { projectId } });
    await prisma.keyword.deleteMany({ where: { projectId } });
    await prisma.competitor.deleteMany({ where: { projectId } });
    await prisma.competitorFeatureMatrix.deleteMany({ where: { projectId } });
    await prisma.contentCoverage.deleteMany({ where: { projectId } });
    await prisma.gapAnalysis.deleteMany({ where: { projectId } });
    await prisma.recommendationSimulation.deleteMany({ where: { projectId } });
    await prisma.report.deleteMany({ where: { projectId } });
    await prisma.qAReport.deleteMany({ where: { projectId } });
    console.log(`[Pipeline] Stale analysis data cleaned up for project ${projectId}.`);

    // 1. Run Agent 2 (Profiler)
    await updateStatus('extracting', 'Fact Extractor');
    emit('agent:stream', { message: '🔍 Running Agent 2: Profiling business & extracting facts...', type: 'info' });
    const profilerState = await runProfiler(projectId);
    state.businessProfile = profilerState.businessProfile;
    state.verifiedFacts = profilerState.verifiedFacts;

    // 2. Run Agent 3 (Questions)
    await updateStatus('analyzing', 'Question Discovery');
    emit('agent:stream', { message: '❓ Running Agent 3: Generating conversational search questions...', type: 'info' });
    const questionsState = await runQuestions(projectId, state);
    state.questions = questionsState.questions;

    // 3. Run Agent 4 (Keywords)
    await updateStatus('analyzing', 'Keyword Agent');
    emit('agent:stream', { message: '🏷️ Running Agent 4: Extracting and clustering keywords (local NLP)...', type: 'info' });
    const keywordsState = await runKeywords(projectId, state);
    state.keywords = keywordsState.keywords;

    // 4. Run Agent 5 (Gap Finder)
    await updateStatus('analyzing', 'Content Coverage');
    emit('agent:stream', { message: '🏁 Running Agent 5: Analyzing competitor gaps & content coverage...', type: 'info' });
    const gapState = await runGapFinder(projectId, state);
    state.competitors = gapState.competitors;
    state.competitorFeatureMatrix = gapState.competitorFeatureMatrix;
    state.contentCoverage = gapState.contentCoverage;
    state.gapAnalysis = gapState.gapAnalysis;

    // 5. Run Agent 6 (AI Simulator)
    await updateStatus('analyzing', 'Recommendation Sim');
    emit('agent:stream', { message: '🤖 Running Agent 6: Simulating AI search engine recommendations...', type: 'info' });
    const simState = await runAISimulator(projectId, state);
    state.recommendationSimulations = simState.recommendationSimulations;

    // 6. Run Agent 7 (QA)
    await updateStatus('compiling', 'Quality Assurance');
    emit('agent:stream', { message: '🛡️ Running Agent 7: Auditing data consistency (rules-based)...', type: 'info' });
    const qaState = await runQA(projectId, state);
    state.qaReport = qaState.qaReport;

    // 7. Run Agent 8 (Report)
    await updateStatus('compiling', 'Report Compiler');
    emit('agent:stream', { message: '📊 Running Agent 8: Aggregating analytics and compiling reports...', type: 'info' });
    const reportState = await runReport(projectId, state);
    state.report = reportState.report;

    // 8. Completed
    await updateStatus('completed', null);
    emit('agent:stream', { message: '🎉 Multi-agent intelligence pipeline successfully completed!', type: 'complete' });
    console.log(`[Pipeline] Pipeline finished successfully for project ${projectId}.`);

  } catch (err) {
    console.error(`[Pipeline] Pipeline failed for project ${projectId}:`, err.message);
    await updateStatus('failed', null);
    emit('agent:error', { message: `Pipeline failed: ${err.message}` });
  } finally {
    await prisma.$disconnect();
  }
}

module.exports = runAgentPipeline;
