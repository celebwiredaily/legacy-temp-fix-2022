# 📌 Pinterest Scraper Configuration for VUZA

## Overview

VUZA includes a built-in Pinterest scraper that can download videos directly without needing API keys from Pexels or Pixabay. This is completely FREE and doesn't require any API registration.

---

## 🚀 Why Use Pinterest Scraper?

### Advantages:
- ✅ **No API keys required** - No Pexels/Pixabay registration needed
- ✅ **Unlimited downloads** - No rate limits
- ✅ **Diverse content** - Access to millions of videos
- ✅ **High quality** - HD video content
- ✅ **Better variety** - More creative and unique clips

### Considerations:
- ⚠️ **Slower downloads** - Scraping takes longer than API calls
- ⚠️ **Content licensing** - Ensure compliance with Pinterest's terms
- ⚠️ **Stability** - Web scraping can break if Pinterest changes their site

---

## 📝 Configuration in GitHub Actions

### Method 1: Using Workflow Config (Recommended)

In your GitHub Actions workflow, set `use_pinterest: 'true'`:

```yaml
workflow_dispatch:
  inputs:
    use_pinterest:
      description: 'Use Pinterest scraper'
      required: false
      default: 'true'  # Enable by default
```

### Method 2: In VUZA Config JSON

The workflow automatically generates this config:

```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["technology", "innovation", "automation"],
      "max_clips_per_keyword": 3,
      "min_duration": 3,
      "max_duration": 8,
      "quality": "hd",
      "download_path": "assets/pinterest"
    },
    "pexels_settings": {
      "enabled": false
    },
    "pixabay_settings": {
      "enabled": false
    }
  }
}
```

---

## 🔧 Pinterest Scraper Settings Explained

### `search_keywords`
- **Type:** Array of strings
- **Description:** Keywords to search for on Pinterest
- **Example:** `["coding", "technology", "workspace", "programming"]`
- **Tips:** 
  - Use 3-5 keywords for best results
  - Mix general and specific terms
  - Include synonyms for variety

### `max_clips_per_keyword`
- **Type:** Integer (1-10)
- **Description:** How many video clips to download per keyword
- **Default:** 3
- **Recommendation:** 
  - 2-3 for 10-minute videos
  - 4-5 for longer content
  - Fewer clips = faster processing

### `min_duration` / `max_duration`
- **Type:** Integer (seconds)
- **Description:** Filter clips by duration
- **Default:** 3-8 seconds
- **Tips:**
  - Shorter clips (3-5s) = more dynamic video
  - Longer clips (5-10s) = smoother transitions
  - Match to your narration pace

### `quality`
- **Type:** String
- **Options:** `"hd"`, `"sd"`, `"any"`
- **Default:** `"hd"`
- **Recommendation:** Always use `"hd"` for professional results

### `download_path`
- **Type:** String
- **Description:** Where to save downloaded clips
- **Default:** `"assets/pinterest"`
- **Note:** Path is relative to VUZA directory

---

## 🎯 Optimizing Pinterest Searches

### Keyword Strategy

**Good Keywords:**
```json
{
  "keywords": [
    "modern office workspace",
    "coding on laptop",
    "technology innovation",
    "digital transformation"
  ]
}
```

**Better Keywords (More Specific):**
```json
{
  "keywords": [
    "programmer typing code",
    "startup team meeting",
    "data visualization screen",
    "AI robot technology"
  ]
}
```

### Matching Keywords to Script

If your script talks about:
- **AI & Machine Learning:** `["artificial intelligence", "neural networks", "robot automation", "data science"]`
- **Business Growth:** `["business success", "growing startup", "team collaboration", "office celebration"]`
- **Nature & Environment:** `["forest aerial view", "ocean waves", "mountain landscape", "green energy"]`
- **Technology:** `["modern technology", "futuristic interface", "coding screen", "smart devices"]`

---

## 🛠️ Troubleshooting Pinterest Scraper

### Issue: "No videos found for keywords"

**Solutions:**
1. Make keywords more general:
   ```json
   "keywords": ["technology", "office", "work"]
   ```

2. Try alternative phrasing:
   - ❌ "SaaS dashboard interface"
   - ✅ "software application screen"

3. Use Pinterest search manually first to verify content exists

### Issue: "Download timeout"

**Solutions:**
1. Reduce `max_clips_per_keyword`:
   ```json
   "max_clips_per_keyword": 2
   ```

2. Increase workflow timeout:
   ```yaml
   jobs:
     generate-video:
       timeout-minutes: 90  # Increase from 60
   ```

### Issue: "Low quality videos"

**Solutions:**
1. Ensure HD filter is enabled:
   ```json
   "quality": "hd"
   ```

2. Adjust duration filters:
   ```json
   "min_duration": 4,
   "max_duration": 10
   ```

### Issue: "Scraper blocked by Pinterest"

**Solutions:**
1. Add delays between requests (VUZA should handle this)
2. Rotate user agents (check VUZA documentation)
3. Use VPN if necessary (not ideal for GitHub Actions)
4. Fall back to Pexels/Pixabay temporarily:
   ```json
   "use_pinterest": false,
   "pexels_settings": {
     "enabled": true,
     "api_key": "your_key"
   }
   ```

---

## 🔄 Hybrid Approach (Best of Both Worlds)

You can use Pinterest AND API-based sources:

```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["main", "theme"],
      "max_clips_per_keyword": 2
    },
    "pexels_settings": {
      "enabled": true,
      "api_key": "${{ secrets.PEXELS_API_KEY }}",
      "max_clips": 5
    }
  }
}
```

**When to use hybrid:**
- Need high variety of content
- Want backup sources if Pinterest fails
- Specific stock footage requirements

---

## 📊 Performance Comparison

| Source | API Key | Speed | Variety | Quality | Cost |
|--------|---------|-------|---------|---------|------|
| **Pinterest** | ❌ No | 🐌 Slow | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Free |
| **Pexels** | ✅ Yes | ⚡ Fast | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Free |
| **Pixabay** | ✅ Yes | ⚡ Fast | ⭐⭐⭐ | ⭐⭐⭐⭐ | Free |

**Recommendation:** Start with Pinterest for simplicity, add Pexels if you need speed.

---

## 🎨 Example Configurations

### Minimal Setup (Fastest)
```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["tech", "work"],
      "max_clips_per_keyword": 2,
      "quality": "any"
    }
  }
}
```

### Balanced Setup (Recommended)
```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["technology", "innovation", "coding", "startup"],
      "max_clips_per_keyword": 3,
      "min_duration": 3,
      "max_duration": 8,
      "quality": "hd"
    }
  }
}
```

### Maximum Quality (Slowest)
```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["cinematic tech", "modern workspace", "ai visualization", "coding aesthetic", "startup culture"],
      "max_clips_per_keyword": 4,
      "min_duration": 5,
      "max_duration": 10,
      "quality": "hd"
    }
  }
}
```

---

## 🚦 Next Steps

1. **Test Pinterest scraper locally first:**
   ```bash
   cd VUZA-Free-AI-Video-Creator-and-Pinterest-Video-Scraper
   python main.py --test-pinterest --keywords "technology,coding"
   ```

2. **Verify downloads:**
   ```bash
   ls assets/pinterest/
   ```

3. **Enable in GitHub Actions:**
   - Set `use_pinterest: 'true'` in workflow
   - Add your keywords to the workflow input

4. **Monitor first run:**
   - Check GitHub Actions logs
   - Verify video output quality
   - Adjust settings as needed

---

## ✅ Checklist

- [ ] VUZA repository cloned
- [ ] Pinterest scraper tested locally
- [ ] Keywords optimized for your niche
- [ ] Duration settings configured
- [ ] GitHub Actions workflow updated
- [ ] First test run successful
- [ ] Video quality meets expectations

**You're ready to use Pinterest scraper in your automated video pipeline!**
