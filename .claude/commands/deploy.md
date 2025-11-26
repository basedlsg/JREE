# Deploy Application

Deploy the JRE Quote Search application.

## Backend
```bash
cd /home/user/JREE
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Frontend (Development)
```bash
cd /home/user/JREE/frontend
npm run dev
```

## Frontend (Production Build)
```bash
cd /home/user/JREE/frontend
npm run build
npm run preview
```

Verify deployment by checking the health endpoint:
```bash
curl http://localhost:8000/health
```
