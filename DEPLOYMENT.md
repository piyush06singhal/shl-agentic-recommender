# 🚀 Deployment Guide

## Deploy Backend to Render

1. **Create Render Account**
   - Go to [render.com](https://render.com) and sign up/login

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `https://github.com/piyush06singhal/shl-agentic-recommender`

3. **Configure Service**
   - **Name**: `shl-recommender-backend`
   - **Runtime**: `Docker`
   - **Branch**: `main`
   - **Dockerfile Path**: `Dockerfile`

4. **Set Environment Variables**

   ```
   OPENAI_API_KEY=your_openai_api_key_here
   MODEL_NAME=gpt-4o
   EMBEDDING_MODEL=text-embedding-3-small
   LOG_LEVEL=INFO
   PORT=8000
   HOST=0.0.0.0
   ALLOWED_ORIGINS=*
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Copy your backend URL: `https://your-service.onrender.com`

6. **Verify**
   ```bash
   curl https://your-service.onrender.com/health
   ```

---

## Deploy Frontend to Vercel

1. **Create Vercel Account**
   - Go to [vercel.com](https://vercel.com) and sign up with GitHub

2. **Import Project**
   - Click "Add New" → "Project"
   - Import: `https://github.com/piyush06singhal/shl-agentic-recommender`

3. **Configure Build Settings**
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

4. **Set Environment Variable**

   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
   ```

5. **Deploy**
   - Click "Deploy"
   - Wait for build (2-3 minutes)
   - Your app will be live at: `https://your-project.vercel.app`

6. **Update Backend CORS** (Important!)
   - Go back to Render → Environment Variables
   - Update `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS=https://your-project.vercel.app
   ```

   - Save and redeploy

---

## Post-Deployment Test

1. Open your Vercel URL
2. Go to "Health Check" tab - should show green
3. Go to "Consultant Chat" tab
4. Send test message: "I need a test for software engineers"
5. Verify recommendations appear

**Done!** ✅
