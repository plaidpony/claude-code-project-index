import express from 'express';
import { validateUser } from 'shared';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.post('/api/users', (req, res) => {
  const userData = req.body;
  
  if (!validateUser(userData)) {
    return res.status(400).json({ error: 'Invalid user data' });
  }
  
  // Process user creation
  res.status(201).json({ message: 'User created successfully' });
});

app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
});

export default app;