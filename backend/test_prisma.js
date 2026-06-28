const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log('Connecting via Prisma...');
  try {
    const projects = await prisma.project.findMany();
    console.log(`Projects count: ${projects.length}`);
    for (const p of projects) {
      console.log(`Project ID: ${p.id} | Name: ${p.projectName} | URL: ${p.websiteUrl} | Status: ${p.status}`);
    }
  } catch (err) {
    console.error('Prisma Error:', err);
  } finally {
    await prisma.$disconnect();
  }
}

main();
