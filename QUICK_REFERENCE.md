# 🎯 Quick Reference: Pinterest vs. API Sources

## TL;DR - What You Need to Know

### Using Pinterest Scraper (NO API KEYS!)
```yaml
# In your GitHub Actions workflow trigger
use_pinterest: 'true'

# No secrets needed!
# No Pexels/Pixabay registration required
```

### Using Pexels/Pixabay (API KEYS REQUIRED)
```yaml
# In your GitHub Actions workflow trigger
use_pinterest: 'false'

# Add to GitHub Secrets:
# - PEXELS_API_KEY
# - PIXABAY_API_KEY
```

---

## 📋 Comparison Table

| Feature | Pinterest Scraper | Pexels API | Pixabay API |
|---------|------------------|------------|-------------|
| **API Key Required** | ❌ No | ✅ Yes (free) | ✅ Yes (free) |
| **Setup Time** | 2 min | 5 min | 5 min |
| **Speed** | 🐌 Slower | ⚡ Fast | ⚡ Fast |
| **Content Variety** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Rate Limits** | None | 200/hour | 100/min |
| **Video Quality** | HD | 4K | HD |
| **Reliability** | ⚠️ Can break | ✅ Stable | ✅ Stable |

**Recommendation:** Start with Pinterest, add Pexels as backup.

---

## 🚀 Quick Setup Examples

### Example 1: Pinterest Only (Simplest)

**Manual Trigger:**
```yaml
# When running manually in GitHub Actions
Title: "My Video"
Script: "This is my video script..."
Keywords: "technology,coding,startup"
Use Pinterest: true  # ← Set this to true
```

**From ActivePieces:**
```json
{
  "event_type": "generate_video",
  "client_payload": {
    "title": "My Video",
    "script": "This is my video script...",
    "keywords": ["technology", "coding", "startup"],
    "metadata": {
      "use_pinterest": true,
      "duration": 600
    }
  }
}
```

**Result:** Video uses Pinterest clips, no API keys needed!

---

### Example 2: Pexels Only

**Setup:**
1. Get Pexels API key: https://www.pexels.com/api/
2. Add to GitHub Secrets: `PEXELS_API_KEY`

**Manual Trigger:**
```yaml
Use Pinterest: false  # ← Set this to false
```

**Modify workflow** (in `.github/workflows/video-generation.yml`):
```yaml
"pexels_settings": {
  "api_key": "${{ secrets.PEXELS_API_KEY }}",
  "enabled": true  # ← Change to true
}
```

---

### Example 3: Hybrid (Best Quality)

**Use both Pinterest AND Pexels for maximum variety:**

**Modify the config generation step in workflow:**

```yaml
- name: Generate VUZA configuration
  run: |
    cat > config/${PROJECT_ID}_config.json << 'EOF'
    {
      "content": {
        "use_pinterest": true,
        "pinterest_settings": {
          "search_keywords": ["main", "theme", "visual"],
          "max_clips_per_keyword": 2
        },
        "pexels_settings": {
          "api_key": "${{ secrets.PEXELS_API_KEY }}",
          "enabled": true,
          "max_clips": 3
        }
      }
    }
    EOF
```

**Result:** 6 Pinterest clips + 3 Pexels clips = diverse visuals!

---

## 🎨 Keyword Optimization by Source

### Pinterest Keywords (More Creative)
```json
{
  "keywords": [
    "aesthetic coding setup",
    "modern office vibes",
    "startup culture moments",
    "creative workspace design"
  ]
}
```

Pinterest responds well to:
- Aesthetic/vibe keywords
- "Moments" and "culture"
- Visual style descriptors

### Pexels Keywords (More Literal)
```json
{
  "keywords": [
    "person coding laptop",
    "office team meeting",
    "startup workspace",
    "technology modern"
  ]
}
```

Pexels responds well to:
- Concrete objects and actions
- Professional stock footage terms
- Specific scenarios

---

## 🔄 Switching Between Sources

### In ActivePieces Flow

**Add a condition step:**

```javascript
// In ActivePieces Code Step
function determineVideoSource(inputs) {
  // Use Pinterest by default
  let usePinterest = true;
  
  // Fall back to Pexels if keywords need professional stock footage
  const professionalKeywords = ['corporate', 'business', 'professional'];
  if (inputs.keywords.some(k => professionalKeywords.includes(k))) {
    usePinterest = false;
  }
  
  return {
    use_pinterest: usePinterest,
    source: usePinterest ? "Pinterest" : "Pexels"
  };
}
```

### Dynamic Source Selection

**Modify your workflow to accept source parameter:**

```yaml
workflow_dispatch:
  inputs:
    source:
      description: 'Video source'
      required: false
      default: 'pinterest'
      type: choice
      options:
        - pinterest
        - pexels
        - pixabay
        - hybrid
```

---

## ⚡ Performance Tips

### For Faster Processing (Use APIs)
```json
{
  "use_pinterest": false,
  "pexels_settings": {
    "enabled": true,
    "max_clips": 5
  }
}
```
**Speed:** ~5-10 minutes for 10-min video

### For Better Quality (Use Pinterest)
```json
{
  "use_pinterest": true,
  "pinterest_settings": {
    "max_clips_per_keyword": 3,
    "quality": "hd"
  }
}
```
**Speed:** ~15-20 minutes for 10-min video

### Balanced (Hybrid)
```json
{
  "use_pinterest": true,
  "pinterest_settings": {
    "max_clips_per_keyword": 2
  },
  "pexels_settings": {
    "enabled": true,
    "max_clips": 2
  }
}
```
**Speed:** ~10-15 minutes for 10-min video

---

## 🛠️ Troubleshooting Flowchart

```
Video not generated?
├─ Check: Are clips downloading?
│  ├─ No Pinterest clips
│  │  └─ Try more general keywords
│  │     └─ Or switch to Pexels
│  ├─ No Pexels clips
│  │  └─ Check API key in Secrets
│  │     └─ Verify quota not exceeded
│  └─ Clips download but video fails
│     └─ Check ffmpeg installation
│        └─ Check VUZA logs
```

---

## 📝 Configuration Templates

### Copy-Paste Ready Configs

#### Minimal Pinterest Config
```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["tech", "work"],
      "max_clips_per_keyword": 2
    }
  }
}
```

#### Professional Pexels Config
```json
{
  "content": {
    "use_pinterest": false,
    "pexels_settings": {
      "api_key": "${{ secrets.PEXELS_API_KEY }}",
      "enabled": true,
      "search_keywords": ["business", "technology"],
      "max_clips": 5,
      "orientation": "landscape"
    }
  }
}
```

#### Hybrid High-Quality Config
```json
{
  "content": {
    "use_pinterest": true,
    "pinterest_settings": {
      "search_keywords": ["cinematic tech", "aesthetic workspace"],
      "max_clips_per_keyword": 2,
      "quality": "hd"
    },
    "pexels_settings": {
      "api_key": "${{ secrets.PEXELS_API_KEY }}",
      "enabled": true,
      "search_keywords": ["professional office"],
      "max_clips": 3
    }
  }
}
```

---

## ✅ Decision Guide

**Choose Pinterest if:**
- ✅ You want NO setup (no API keys)
- ✅ You need diverse, creative content
- ✅ Processing time isn't critical
- ✅ Your niche is visual/aesthetic

**Choose Pexels/Pixabay if:**
- ✅ You need fast processing
- ✅ You want professional stock footage
- ✅ You're okay with API registration
- ✅ You need 4K quality

**Choose Hybrid if:**
- ✅ You want the best of both worlds
- ✅ Quality matters more than speed
- ✅ You have varied content needs
- ✅ You want maximum variety

---

## 🎯 Action Items

1. **Test Pinterest first** (no setup required)
2. **If slow**, add Pexels API key
3. **If quality issues**, refine keywords
4. **If variety needed**, use hybrid approach
5. **Monitor and optimize** based on results

**Start simple, optimize later!**
