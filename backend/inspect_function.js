const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  try {
    const result = await prisma.$queryRawUnsafe(`
      SELECT pg_get_functiondef('public.current_user_id'::regproc) as def;
    `);
    console.log('Function definition:');
    console.log(result[0].def);
  } catch (err) {
    console.error('Error fetching function definition:', err);
  } finally {
    await prisma.$disconnect();
  }
}

main();
