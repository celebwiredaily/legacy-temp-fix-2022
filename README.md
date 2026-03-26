# 🎬 Video Automation with GitHub Actions

## What This Is

A **complete conversion** of the local video automation workflow to **GitHub Actions**, enabling:
- ✅ Cloud-based automated video generation
- ✅ No local servers or infrastructure needed
- ✅ Pinterest scraper integration (NO API keys required!)
- ✅ ActivePieces integration for automated triggering
- ✅ 100% free for public repositories

## 📁 Files Included

### Core Workflow
- **`.github/workflows/video-generation.yml`** - Main GitHub Actions workflow
  - Handles video generation in the cloud
  - Automatically clones VUZA
  - Configures Pinterest scraper or API sources
  - Uploads videos as artifacts

### Integration
- **`activepieces_github_trigger.py`** - Python script to trigger workflows from ActivePieces
  - Call GitHub API from ActivePieces
  - Handle repository_dispatch events
  - Test script for manual triggering

### Documentation
- **`GITHUB_ACTIONS_SETUP.md`** - Complete setup guide
  - Step-by-step instructions
  - ActivePieces integration
  - Cloud storage setup
  - Troubleshooting

- **`PINTEREST_SCRAPER_GUIDE.md`** - Pinterest scraper configuration
  - Why use Pinterest vs. APIs
  - Configuration options
  - Keyword optimization
  - Performance tuning

- **`QUICK_REFERENCE.md`** - Quick reference card
  - Pinterest vs. API comparison
  - Copy-paste configs
  - Decision guide
  - Templates

### Configuration
- **`requirements.txt`** - Python dependencies
- **`.env.template`** - Environment variables template

---

## 🚀 Quick Start

### 1. Set Up Repository

```bash
# Create repository
mkdir video-automation
cd video-automation
git init

# Copy workflow file
mkdir -p .github/workflows
cp video-generation.yml .github/workflows/

# Push to GitHub
git add .
git commit -m "Initial setup"
git remote add origin https://github.com/YOUR_USERNAME/video-automation.git
git push -u origin main
```

### 2. Test Manual Trigger

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select "Video Generation Pipeline"
4. Click **Run workflow**
5. Fill in:
   - Title: "Test Video"
   - Script: "This is a test..."
   - Keywords: "technology,coding"
   - Use Pinterest: `true`
6. Wait 10-15 minutes
7. Download from **Artifacts** section

### 3. Integrate with ActivePieces

**Option A: Simple HTTP Request**

In ActivePieces, add HTTP Request step:

```json
POST https://api.github.com/repos/YOUR_USERNAME/REPO/dispatches
Headers:
  Authorization: Bearer YOUR_GITHUB_TOKEN
  Accept: application/vnd.github+json
Body:
{
  "event_type": "generate_video",
  "client_payload": {
    "title": "{{title}}",
    "script": "{{script}}",
    "keywords": ["tech", "coding"],
    "metadata": {
      "use_pinterest": true
    }
  }
}
```

**Option B: Use Python Script**

```bash
# Configure environment
cp .env.template .env
nano .env  # Add your credentials

# Test trigger
python activepieces_github_trigger.py
```

---

## 🎯 Key Differences from Local Setup

### Local Setup (Original)
```
ActivePieces → Webhook Server → Queue → Processor → VUZA
               (localhost)        (files)  (Python)
```
**Requires:**
- Running servers
- Queue management
- Complex deployment

### GitHub Actions (New)
```
ActivePieces → GitHub API → Workflow → VUZA → Artifact
               (cloud)        (cloud)   (cloud)
```
**Requires:**
- Just a GitHub repository
- API token
- Nothing else!

---

## 📌 Using Pinterest Scraper

### Why Pinterest?

✅ **No API registration required**
✅ **No rate limits**
✅ **Millions of videos available**
✅ **More creative/diverse content**

### How to Enable

**In Manual Trigger:**
```
Use Pinterest: true
```

**In ActivePieces:**
```json
{
  "metadata": {
    "use_pinterest": true
  }
}
```

**That's it!** No additional setup needed.

### Configuration Options

The workflow automatically generates this config:

```json
{
  "pinterest_settings": {
    "search_keywords": ["your", "keywords"],
    "max_clips_per_keyword": 3,
    "min_duration": 3,
    "max_duration": 8,
    "quality": "hd"
  }
}
```

**Customize by editing the workflow file** (see PINTEREST_SCRAPER_GUIDE.md for details).

---

## 🔧 Customization

### Change Video Duration

Edit workflow file:

```yaml
workflow_dispatch:
  inputs:
    duration:
      default: '600'  # Change to 300, 900, etc.
```

### Change Video Quality

Edit config generation step:

```yaml
"video": {
  "resolution": {"width": 3840, "height": 2160},  # 4K
  "fps": 60  # Smoother motion
}
```

### Add Cloud Storage

Uncomment the cloud upload step:

```yaml
- name: Upload to S3
  run: |
    aws s3 cp output/${PROJECT_ID}.mp4 s3://your-bucket/
```

See GITHUB_ACTIONS_SETUP.md for detailed instructions.

---

## 💰 Costs

### GitHub Actions (Public Repo)
- **Compute:** FREE unlimited minutes
- **Storage:** FREE 500MB artifacts (up to 90 days)
- **Total:** $0/month

### GitHub Actions (Private Repo)
- **Compute:** 2,000 minutes/month FREE
- **Storage:** 500MB FREE
- **Typical video:** ~10-15 minutes/video
- **Capacity:** ~130 videos/month FREE

### APIs (If Not Using Pinterest)
- **Pexels:** FREE (200 requests/hour)
- **Pixabay:** FREE (100 requests/minute)

**Bottom line:** Completely free for most use cases!

---

## 📊 Workflow Status

Check your video generation status:

```bash
# Install GitHub CLI
gh auth login

# List recent runs
gh run list --workflow=video-generation.yml

# View specific run
gh run view <run-id>

# Download artifact
gh run download <run-id>
```

Or check in GitHub UI: **Actions → Workflow runs**

---

## 🆘 Troubleshooting

### Workflow not triggering?
→ Check `GITHUB_TOKEN` in ActivePieces
→ Verify repository_dispatch event in workflow file

### VUZA not found?
→ Check VUZA clone step logs
→ Verify entry point detection

### No videos downloaded?
→ Check Pinterest keywords are valid
→ Try more general keywords
→ Enable debug logging

### Out of minutes?
→ Use public repository (unlimited)
→ Or use self-hosted runner

**See GITHUB_ACTIONS_SETUP.md for detailed troubleshooting.**

---

## 📚 Documentation Structure

```
├── README.md (this file)               - Overview & quick start
├── GITHUB_ACTIONS_SETUP.md            - Complete setup guide
├── PINTEREST_SCRAPER_GUIDE.md         - Pinterest configuration
├── QUICK_REFERENCE.md                 - Quick decision guide
├── .github/workflows/
│   └── video-generation.yml           - Main workflow
├── activepieces_github_trigger.py     - ActivePieces integration
├── requirements.txt                   - Dependencies
└── .env.template                      - Environment variables
```

**Start with:** GITHUB_ACTIONS_SETUP.md

---

## 🎉 What You Get

After setup, you'll have:

1. ✅ **Automated video generation** triggered by ActivePieces
2. ✅ **No local infrastructure** - everything runs in GitHub cloud
3. ✅ **Pinterest scraper** - no API keys needed
4. ✅ **Artifact storage** - videos saved for 7 days
5. ✅ **Scalable** - handle multiple videos in parallel
6. ✅ **Free** - 100% free for public repos

---

## 🚀 Next Steps

1. **Read:** GITHUB_ACTIONS_SETUP.md (complete guide)
2. **Set up:** Follow the quick start above
3. **Test:** Run manual workflow
4. **Configure:** Set up ActivePieces integration
5. **Optimize:** Read PINTEREST_SCRAPER_GUIDE.md
6. **Scale:** Add cloud storage, notifications, etc.

---

## 🤝 Support

**Issues?** Check:
1. Workflow logs in GitHub Actions
2. GITHUB_ACTIONS_SETUP.md troubleshooting section
3. VUZA repository issues: https://github.com/AliRash3ed/VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper/issues

---

## 📝 License

This automation workflow is provided as-is. VUZA has its own license - see the VUZA repository.

---

**Happy automating! 🎬**
