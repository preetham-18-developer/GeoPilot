// backend/src/server.js
// Express + Socket.io server entry point for the AIVOP Node.js backend.
// Exposes a single POST /api/analyze endpoint that triggers the crawl pipeline.

const http = require('http');
const express = require('express');
const { Server } = require('socket.io');
const cors = require('cors');
const dotenv = require('dotenv');
const { crawlWebsite } = require('./agents/crawler');
const { runProfiler } = require('./agents/profiler');

dotenv.config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*', methods: ['GET', 'POST'] },
});

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(cors());
app.use(express.json());

// ── Simple Mock Auth Middleware ───────────────────────────────────────────────
// Accepts either "Bearer mock-<userId>" (for development) or a real JWT.
function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization || '';
  const token = authHeader.replace('Bearer ', '').trim();

  if (!token) {
    return res.status(401).json({ error: 'Missing Authorization header.' });
  }

  if (token.startsWith('mock-')) {
    // Mock mode: extract userId from "mock-<userId>"
    req.userId = token.slice(5) || 'mock-user';
    return next();
  }

  // Real JWT verification (requires JWT_SECRET in .env)
  try {
    const jwt = require('jsonwebtoken');
    const payload = jwt.verify(token, process.env.JWT_SECRET);
    req.userId = payload.sub || payload.userId;
    return next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token.' });
  }
}

// ── Health Check ──────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ── POST /api/analyze ─────────────────────────────────────────────────────────
// Triggers a crawl + analysis pipeline for a given website URL and project ID.
// Body: { projectId: string, websiteUrl: string, socketId: string }
app.post('/api/analyze', authMiddleware, async (req, res) => {
  const { projectId, websiteUrl, socketId } = req.body;

  if (!projectId || !websiteUrl) {
    return res.status(400).json({ error: 'projectId and websiteUrl are required.' });
  }

  // Validate URL format
  try {
    new URL(websiteUrl);
  } catch (_) {
    return res.status(400).json({ error: 'Invalid websiteUrl format.' });
  }

  // Respond immediately — crawl runs asynchronously
  res.json({
    message: 'Crawl initiated.',
    projectId,
    socketId: socketId || null,
  });

  // Run crawl in background (non-blocking)
  setImmediate(async () => {
    try {
      const { pagesCount, identity } = await crawlWebsite(
        websiteUrl,
        projectId,
        io,
        socketId || null,
        parseInt(process.env.MAX_PAGES_PER_CRAWL || '30', 10),
        false // require identity confirmation
      );
      console.log(`[Server] Crawl finished: ${pagesCount} pages, identity:`, identity);

      // Run Agent Pipeline (Profiler, Questions, Keywords, Gap Finder, AI Simulator, QA, Report)
      const runAgentPipeline = require('./agents/pipeline');
      await runAgentPipeline(projectId, io, socketId || null);

    } catch (err) {
      console.error('[Server] Crawl pipeline error:', err.message);
      if (socketId) {
        io.to(socketId).emit('agent:error', {
          message: `Crawl failed: ${err.message}`,
        });
      }
    }
  });
});

// ── POST /api/confirm-identity ────────────────────────────────────────────────
// Updates project status to 'identity_confirmed' so the crawler can resume.
// Body: { projectId: string }
app.post('/api/confirm-identity', authMiddleware, async (req, res) => {
  const { projectId } = req.body;
  if (!projectId) {
    return res.status(400).json({ error: 'projectId is required.' });
  }

  try {
    const { PrismaClient } = require('@prisma/client');
    const prisma = new PrismaClient();
    await prisma.project.update({
      where: { id: projectId },
      data: { status: 'identity_confirmed' },
    });
    await prisma.$disconnect();
    res.json({ message: 'Identity confirmed. Crawl will resume.' });
  } catch (err) {
    console.error('[Server] Identity confirm error:', err.message);
    res.status(500).json({ error: 'Failed to confirm identity.' });
  }
});

// ── POST /api/profile ─────────────────────────────────────────────────────────
// Triggers the Business Profiler agent run in the background.
// Body: { projectId: string, socketId: string }
app.post('/api/profile', authMiddleware, async (req, res) => {
  const { projectId, socketId } = req.body;
  if (!projectId) {
    return res.status(400).json({ error: 'projectId is required' });
  }

  res.json({ message: 'Profiling started', projectId });

  const emit = (pid, event, data) => {
    if (io && socketId) {
      io.to(socketId).emit(event, data);
    }
  };

  // Run in background
  runProfiler(projectId, emit).catch(err => {
    console.error('Profiler failed:', err);
    emit(projectId, 'agent:error', { message: err.message });
  });
});

// ── Socket.io Connection Handler ──────────────────────────────────────────────
io.on('connection', (socket) => {
  console.log(`[Socket] Client connected: ${socket.id}`);

  socket.on('disconnect', () => {
    console.log(`[Socket] Client disconnected: ${socket.id}`);
  });
});

// ── Start Server ──────────────────────────────────────────────────────────────
const PORT = parseInt(process.env.PORT || '3001', 10);
server.listen(PORT, () => {
  console.log(`[Server] AIVOP backend running on http://localhost:${PORT}`);
  console.log(`[Server] Mock mode: ${process.env.MOCK_MODE === 'true' ? 'ON' : 'OFF'}`);
});

module.exports = { app, server, io };
