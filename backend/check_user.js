const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  try {
    const project = await prisma.project.findUnique({
      where: { id: '0a3591d7-0c08-47f9-a66c-feb251246fb3' }
    });
    console.log('Project userId:', project.userId);

    const users = await prisma.user.findMany();
    console.log('Users in DB:');
    for (const u of users) {
      console.log(`User ID: ${u.id} | Email: ${u.email}`);
    }
  } catch (err) {
    console.error(err);
  } finally {
    await prisma.$disconnect();
  }
}

main();
