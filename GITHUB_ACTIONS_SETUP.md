# 🎬 GitHub Actions Video Automation - Complete Setup Guide

## 🌟 Overview

This guide converts the local video automation workflow to **GitHub Actions**, eliminating the need for:
- ❌ Local servers running 24/7
- ❌ Webhook receivers
- ❌ Queue processors
- ❌ Complex deployment

Instead, you get:
- ✅ Cloud-based video generation
- ✅ Triggered by ActivePieces or manual input
- ✅ Automatic artifact storage
- ✅ No infrastructure management

---

## 🏗️ Architecture Comparison

### Local Setup (Original)
```
ActivePieces → Webhook Server → Queue → Processor → VUZA → Video
               (localhost:5000)   (files)  (Python)
```

### GitHub Actions Setup (New)
```
ActivePieces → GitHub API → Actions Workflow → VUZA → Video Artifact
               (repository_dispatch)              (cloud)
```

---

## 🚀 Quick Start (10 Minutes)

### Step 1: Fork or Create Repository

```bash
# Create new repository
mkdir video-automation-actions
cd video-automation-actions
git init

# Create directory structure
mkdir -p .github/workflows
mkdir -p config scripts
```

### Step 2: Add Workflow File

Copy the GitHub Actions workflow:

```bash
# Copy the workflow file I created
cp video-generation.yml .github/workflows/
```

Or create it manually in `.github/workflows/video-generation.yml` (see previous file).

### Step 3: Configure Repository Secrets

Go to **Settings → Secrets and variables → Actions** and add:

#### Optional (for Pexels/Pixabay fallback):
- `PEXELS_API_KEY` - Get from https://www.pexels.com/api/
- `PIXABAY_API_KEY` - Get from https://pixabay.com/api/docs/

#### For ActivePieces Integration:
- `GITHUB_TOKEN` - Auto-generated (no action needed)

### Step 4: Push to GitHub

```bash
git add .
git commit -m "Initial video automation setup"
git remote add origin https://github.com/YOUR_USERNAME/video-automation-actions.git
git push -u origin main
```

### Step 5: Test Manual Trigger

1. Go to **Actions** tab in your repository
2. Click "Video Generation Pipeline"
3. Click "Run workflow"
4. Fill in the form:
   - **Title:** "Test Video"
   - **Script:** "This is a test script for automated video generation."
   - **Keywords:** "technology,automation,coding"
   - **Use Pinterest:** `true`
5. Click "Run workflow"
6. Wait ~5-15 minutes
7. Download video from **Artifacts**

---

## 🔌 ActivePieces Integration

### Option 1: Using Repository Dispatch (Recommended)

#### 1. Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: "ActivePieces Video Automation"
4. Scopes: Select `repo` (all)
5. Click "Generate token"
6. **Copy the token** (you won't see it again!)

#### 2. Configure ActivePieces Environment

In ActivePieces, add these environment variables:
- `GITHUB_TOKEN` - Your personal access token
- `GITHUB_REPO_OWNER` - Your GitHub username
- `GITHUB_REPO_NAME` - Repository name (e.g., "video-automation-actions")

#### 3. Create ActivePieces Flow

**Trigger:** Your choice (schedule, webhook, etc.)

**Step 1: Generate Content** (AI or template)
- Use Claude/GPT to generate script
- Extract keywords from script
- Format data

**Step 2: HTTP Request**
- **Method:** POST
- **URL:** `https://api.github.com/repos/{{GITHUB_REPO_OWNER}}/{{GITHUB_REPO_NAME}}/dispatches`
- **Headers:**
  ```json
  {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer {{GITHUB_TOKEN}}",
    "X-GitHub-Api-Version": "2022-11-28"
  }
  ```
- **Body:**
  ```json
  {
    "event_type": "generate_video",
    "client_payload": {
      "title": "{{script_title}}",
      "script": "{{generated_script}}",
      "keywords": {{keywords_array}},
      "metadata": {
        "voice": "en-US-AriaNeural",
        "duration": 600,
        "use_pinterest": true
      }
    }
  }
  ```

**Step 3: Check Status** (Optional)
- Wait 30 seconds
- Call GitHub Actions API to check run status
- Parse response and log

#### 4. Test Integration

```bash
# Use the test script I created
python activepieces_github_trigger.py
```

### Option 2: Using GitHub CLI (Alternative)

```bash
# Install GitHub CLI
# https://cli.github.com/

# Trigger workflow
gh workflow run video-generation.yml \
  -f title="Test Video" \
  -f script="This is a test" \
  -f keywords="tech,code" \
  -f use_pinterest="true"
```

---

## 📦 Handling Video Outputs

### Built-in: GitHub Artifacts (Free, 7 days)

Videos are automatically uploaded as artifacts:

```yaml
- name: Upload video artifact
  uses: actions/upload-artifact@v4
  with:
    name: video-${{ env.PROJECT_ID }}
    path: output/${{ env.PROJECT_ID }}.mp4
    retention-days: 7  # Free tier: 90 days max
```

**Download via:**
1. GitHub UI: Actions → Workflow Run → Artifacts section
2. GitHub API:
   ```bash
   gh run download <run_id> -n video-<project_id>
   ```

### Cloud Storage Integration

#### AWS S3

Add to workflow:

```yaml
- name: Upload to S3
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  run: |
    pip install awscli
    aws s3 cp output/${PROJECT_ID}.mp4 \
      s3://${{ secrets.S3_BUCKET }}/videos/${PROJECT_ID}.mp4 \
      --acl public-read
```

**Secrets to add:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET`

#### Google Drive

```yaml
- name: Upload to Google Drive
  run: |
    # Install rclone
    curl https://rclone.org/install.sh | sudo bash
    
    # Configure rclone (use secrets for config)
    echo "${{ secrets.RCLONE_CONFIG }}" > ~/.config/rclone/rclone.conf
    
    # Upload
    rclone copy output/${PROJECT_ID}.mp4 gdrive:Videos/
```

**Setup rclone config:** https://rclone.org/drive/

#### Dropbox

```yaml
- name: Upload to Dropbox
  env:
    DROPBOX_ACCESS_TOKEN: ${{ secrets.DROPBOX_ACCESS_TOKEN }}
  run: |
    pip install dropbox
    python upload_to_dropbox.py output/${PROJECT_ID}.mp4
```

---

## ⚙️ Advanced Configuration

### Parallel Video Generation

Process multiple videos simultaneously:

```yaml
strategy:
  matrix:
    video: [video1, video2, video3]
  max-parallel: 3  # Free tier: 20 max
```

### Scheduled Video Generation

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
```

### Conditional Processing

```yaml
- name: Run VUZA
  if: github.event.client_payload.metadata.use_pinterest == 'true'
  run: python vuza_pinterest.py
```

### Custom Notifications

```yaml
- name: Send completion notification
  if: success()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.MAIL_USERNAME }}
    password: ${{ secrets.MAIL_PASSWORD }}
    subject: Video Generated - ${{ steps.parse_input.outputs.title }}
    to: your-email@example.com
    body: |
      Video successfully generated!
      Download: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

---

## 🐛 Troubleshooting

### Issue: "Workflow not triggering"

**Check:**
1. Workflow file syntax: https://www.yamllint.com/
2. Repository dispatch permissions
3. GitHub token scopes
4. ActivePieces request logs

**Debug:**
```bash
# List recent workflow runs
gh run list --workflow=video-generation.yml

# View specific run
gh run view <run_id>
```

### Issue: "VUZA not found"

**Solution:** Verify VUZA clone step:

```yaml
- name: Debug VUZA
  run: |
    ls -la VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper/
    find . -name "*.py" -type f
```

### Issue: "ffmpeg not installed"

**Solution:** System dependencies step should install it:

```yaml
- name: Install ffmpeg
  run: |
    sudo apt-get update
    sudo apt-get install -y ffmpeg
    ffmpeg -version  # Verify
```

### Issue: "Out of disk space"

**Check:** GitHub Actions runners have ~14GB free space

**Solution:**
```yaml
- name: Check disk space
  run: df -h

- name: Clean up
  run: |
    sudo rm -rf /usr/share/dotnet
    sudo rm -rf /opt/ghc
    df -h
```

### Issue: "Timeout after 60 minutes"

**Solution:** Increase timeout:

```yaml
jobs:
  generate-video:
    timeout-minutes: 120  # Max: 360 (6 hours)
```

---

## 💰 GitHub Actions Limits

### Free Tier (Public Repos)
- ✅ **Unlimited** minutes
- ✅ **20** concurrent jobs
- ✅ **5GB** artifact storage (90 days)

### Free Tier (Private Repos)
- ⚠️ **2,000** minutes/month
- ⚠️ **500MB** artifact storage

### Optimization Tips

1. **Use caching:**
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
   ```

2. **Reduce artifact retention:**
   ```yaml
   retention-days: 3  # Instead of 7
   ```

3. **Self-hosted runners:** Free unlimited minutes!
   ```yaml
   runs-on: self-hosted  # Instead of ubuntu-latest
   ```

---

## 🔐 Security Best Practices

### Secrets Management

✅ **DO:**
- Store all API keys in GitHub Secrets
- Use environment-specific secrets
- Rotate tokens regularly
- Use least-privilege access

❌ **DON'T:**
- Hardcode credentials in workflow files
- Echo secrets in logs
- Commit .env files

### Example:

```yaml
# ❌ WRONG
- run: echo "API key is sk_12345"

# ✅ RIGHT
- run: echo "API key configured"
  env:
    API_KEY: ${{ secrets.API_KEY }}
```

### Audit Logs

Check who triggered workflows:
```bash
gh api repos/{owner}/{repo}/actions/runs \
  --jq '.workflow_runs[] | {id, actor, event, conclusion}'
```

---

## 📊 Monitoring & Logging

### View Logs

```bash
# List runs
gh run list --workflow=video-generation.yml

# View logs
gh run view <run_id> --log

# Download logs
gh run download <run_id> --name logs-<project_id>
```

### Workflow Status Badge

Add to README:

```markdown
![Video Generation](https://github.com/YOUR_USERNAME/REPO/actions/workflows/video-generation.yml/badge.svg)
```

### Slack Notifications

```yaml
- name: Slack notification
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 🎯 Next Steps

1. ✅ Set up repository and workflow
2. ✅ Test manual trigger
3. ✅ Configure ActivePieces integration
4. ✅ Add cloud storage (optional)
5. ✅ Set up monitoring
6. ✅ Optimize Pinterest scraper settings
7. ✅ Scale to production

---

## 📚 Resources

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **VUZA Repository:** https://github.com/AliRash3ed/VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper
- **ActivePieces Docs:** https://www.activepieces.com/docs
- **Repository Dispatch:** https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event

---

## ✅ Success Checklist

- [ ] Repository created with workflow file
- [ ] Secrets configured (if using Pexels/Pixabay)
- [ ] Manual test successful
- [ ] ActivePieces integration tested
- [ ] Pinterest scraper working
- [ ] Video downloaded from artifacts
- [ ] Cloud storage configured (optional)
- [ ] Monitoring set up
- [ ] Production ready!

**🎉 You now have a fully automated, cloud-based video generation pipeline!**

No servers, no maintenance, just automated video creation on demand.
