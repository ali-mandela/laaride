# LaaRide Deployment Guide

Step-by-step guide to deploying LaaRide on Railway with MongoDB Atlas, Upstash Redis, and Backblaze B2.

---

## 1. MongoDB Atlas (Free M0)

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a free **M0** cluster — select **Mumbai (ap-south-1)** region
3. Create a database user with **readWrite** role
4. Under **Network Access**, whitelist all IPs: `0.0.0.0/0` (Railway uses dynamic IPs)
5. Get the connection string and set it as `MONGODB_URL`:
   ```
   mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   ```

---

## 2. Upstash Redis (Free)

1. Go to [upstash.com](https://upstash.com)
2. Create a Redis database — select **Mumbai** region
3. Copy the **TLS** REST URL (starts with `rediss://`)
4. Set environment variables:
   ```
   REDIS_URL=rediss://<user>:<password>@<host>.upstash.io:6379
   RATE_LIMIT_ENABLED=true
   ```

---

## 3. Backblaze B2 (Free, no credit card)

1. Go to [backblaze.com](https://www.backblaze.com), create account (no credit card needed)
2. Create a bucket named `laaride-uploads`, set to **Public**
3. Go to **App Keys** → create new key with **read+write** access to that bucket
4. Note your bucket region from the endpoint URL (e.g. `us-west-004`)
5. Set environment variables:
   ```
   BACKBLAZE_KEY_ID=<your-key-id>
   BACKBLAZE_APPLICATION_KEY=<your-app-key>
   BACKBLAZE_BUCKET_NAME=laaride-uploads
   BACKBLAZE_REGION=us-west-004
   ```

---

## 4. Railway (API hosting)

1. Go to [railway.app](https://railway.app), sign in with GitHub
2. **New Project** → **Deploy from GitHub repo**
3. Select the `laaride-server/` directory as root
4. Add all environment variables from `.env.example`
5. Railway auto-detects the Dockerfile and deploys
6. Get your public URL from the Railway dashboard
7. Update `ALLOWED_ORIGINS` with your Railway URL

---

## 5. Post-deployment

```bash
# Verify the server is running
curl https://<your-railway-url>/health

# Seed default routes
curl -X POST https://<your-railway-url>/api/v1/routes/seed

# Test OTP flow
curl -X POST https://<your-railway-url>/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+91XXXXXXXXXX"}'
```

---

## 6. Verify checklist

- [ ] `/health` returns `status: ok`
- [ ] MongoDB connected (health check shows `database: ok`)
- [ ] OTP send + verify working
- [ ] File upload working (profile photo)
- [ ] Admin dashboard returning stats
