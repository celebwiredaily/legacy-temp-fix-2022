"""
ActivePieces Integration for GitHub Actions Video Pipeline

This script helps you integrate ActivePieces with GitHub Actions to trigger
video generation workflows via repository_dispatch events.
"""

import os
import requests
import json
from typing import Dict, List, Optional

class GitHubActionsVideoTrigger:
    """Trigger GitHub Actions video generation from ActivePieces"""
    
    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        """
        Initialize the GitHub Actions trigger
        
        Args:
            github_token: GitHub Personal Access Token with repo scope
            repo_owner: GitHub username or organization
            repo_name: Repository name
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
    
    def trigger_video_generation(
        self,
        title: str,
        script: str,
        keywords: List[str],
        voice: str = "en-US-BrianMultilingualNeural",
        duration: int = 600,
        use_pinterest: bool = True,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Trigger video generation via repository_dispatch
        
        Args:
            title: Video title
            script: Video script/narration
            keywords: List of keywords for visual search
            voice: TTS voice to use
            duration: Video duration in seconds
            use_pinterest: Use Pinterest scraper instead of Pexels/Pixabay
            metadata: Additional metadata
        
        Returns:
            Response from GitHub API
        """
        payload = {
            "event_type": "generate_video",
            "client_payload": {
                "title": title,
                "script": script,
                "keywords": keywords,
                "metadata": {
                    "voice": voice,
                    "duration": duration,
                    "use_pinterest": use_pinterest,
                    **(metadata or {})
                }
            }
        }
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.github_token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.post(self.api_url, json=payload, headers=headers)
        
        if response.status_code == 204:
            return {
                "success": True,
                "message": "Video generation triggered successfully",
                "payload": payload
            }
        else:
            return {
                "success": False,
                "message": f"Failed to trigger: {response.status_code}",
                "error": response.text
            }


# Example usage for ActivePieces Code Step
def activepieces_trigger_video(inputs: Dict) -> Dict:
    """
    Use this function in an ActivePieces Code step
    
    Expected inputs from previous steps:
    - title: Video title
    - script: Generated script
    - keywords: Array of keywords
    - voice: (optional) TTS voice
    - duration: (optional) Duration in seconds
    """
    
    # Get from ActivePieces environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_REPO_OWNER")  # e.g., "yourusername"
    repo_name = os.getenv("GITHUB_REPO_NAME")    # e.g., "video-automation"
    
    trigger = GitHubActionsVideoTrigger(github_token, repo_owner, repo_name)
    
    result = trigger.trigger_video_generation(
        title=inputs.get("title"),
        script=inputs.get("script"),
        keywords=inputs.get("keywords", []),
        voice=inputs.get("voice", "en-US-AriaNeural"),
        duration=inputs.get("duration", 600),
        use_pinterest=inputs.get("use_pinterest", True)
    )
    
    return result


# Standalone test script
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Configuration
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
    REPO_NAME = os.getenv("GITHUB_REPO_NAME")
    
    if not all([GITHUB_TOKEN, REPO_OWNER, REPO_NAME]):
        print("❌ Missing environment variables!")
        print("Required: GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME")
        sys.exit(1)
    
    trigger = GitHubActionsVideoTrigger(GITHUB_TOKEN, REPO_OWNER, REPO_NAME)
    
    # Test video
    result = trigger.trigger_video_generation(
        title="Test Video from ActivePieces Integration",
        script="""
        This is a test video demonstrating the integration between ActivePieces 
        and GitHub Actions. The video is automatically generated using VUZA's 
        Pinterest scraper to fetch relevant visuals based on the provided keywords.
        This eliminates the need for API keys from Pexels or Pixabay.
        """,
        keywords=["technology", "automation", "innovation", "future"],
        voice="en-US-BrianMultilingualNeural",
        duration=600,
        use_pinterest=True
    )
    
    print(json.dumps(result, indent=2))
    
    if result["success"]:
        print("\n✅ Video generation triggered!")
        print(f"Check your GitHub Actions: https://github.com/{REPO_OWNER}/{REPO_NAME}/actions")
    else:
        print("\n❌ Failed to trigger video generation")
