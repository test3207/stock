import Fastify from 'fastify';
import cors from '@fastify/cors';

const app = Fastify();
await app.register(cors, { origin: true });

app.get('/health', async () => ({ status: 'ok' }));

app.listen({ port: 3100 }).then(()=>{
  console.log('Server started on 3100');
});
