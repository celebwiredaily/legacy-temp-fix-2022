#!/usr/bin/env python3
"""
Long-Form Video Automation Workflow
===================================
This script orchestrates the complete video production pipeline:
1. Receives script & keywords from ActivePieces
2. Processes assets (images, audio, b-roll)
3. Generates video using the video editor
4. Handles errors gracefully with retries
5. Logs everything for debugging

Author: Claude
Date: 2026-03-26
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import requests
from dataclasses import dataclass, asdict
import traceback


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class WorkflowConfig:
    """Centralized configuration for the workflow"""
    
    # Paths
    work_dir: Path = Path("./workflow_workspace")
    scripts_dir: Path = Path("./scripts")
    assets_dir: Path = Path("./assets")
    output_dir: Path = Path("./output")
    logs_dir: Path = Path("./logs")
    temp_dir: Path = Path("./temp")
    
    # ActivePieces integration
    activepieces_webhook_url: str = os.getenv("ACTIVEPIECES_WEBHOOK_URL", "")
    activepieces_api_key: str = os.getenv("ACTIVEPIECES_API_KEY", "")
    
    # Video editor settings
    video_editor_path: Path = Path("./vuza")  # Adjust to your cloned repo path
    video_editor_script: str = "main.py"  # Adjust to actual entry point
    
    # Video specifications
    video_duration: int = 600  # 10 minutes in seconds
    video_width: int = 1920
    video_height: int = 1080
    video_fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    
    # Processing settings
    concurrent_workers: int = 2
    timeout: int = 3600  # 1 hour timeout for video rendering
    
    def __post_init__(self):
        """Create necessary directories"""
        for dir_path in [self.work_dir, self.scripts_dir, self.assets_dir, 
                         self.output_dir, self.logs_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(config: WorkflowConfig) -> logging.Logger:
    """Setup comprehensive logging"""
    log_file = config.logs_dir / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger('VideoAutomation')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# VIDEO PROJECT DATA STRUCTURE
# ============================================================================

@dataclass
class VideoProject:
    """Represents a single video project"""
    project_id: str
    title: str
    script: str
    keywords: List[str]
    metadata: Dict[str, Any]
    timestamp: str = datetime.now().isoformat()
    status: str = "pending"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def save(self, config: WorkflowConfig):
        """Save project metadata to disk"""
        project_file = config.scripts_dir / f"{self.project_id}.json"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# ============================================================================
# ACTIVEPIECES INTEGRATION
# ============================================================================

class ActivePiecesClient:
    """Handles communication with ActivePieces"""
    
    def __init__(self, config: WorkflowConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def fetch_pending_projects(self) -> List[VideoProject]:
        """
        Fetch pending video projects from ActivePieces.
        In production, this would call your ActivePieces API/webhook.
        """
        self.logger.info("Fetching pending projects from ActivePieces...")
        
        # Placeholder - replace with actual API call
        # Example:
        # response = requests.get(
        #     f"{self.config.activepieces_webhook_url}/projects",
        #     headers={"Authorization": f"Bearer {self.config.activepieces_api_key}"}
        # )
        # data = response.json()
        
        # For now, return empty list (replace with actual implementation)
        return []
    
    def update_project_status(self, project_id: str, status: str, 
                             video_url: Optional[str] = None):
        """Update project status in ActivePieces"""
        self.logger.info(f"Updating project {project_id} status to: {status}")
        
        # Placeholder - replace with actual API call
        # requests.post(
        #     f"{self.config.activepieces_webhook_url}/update",
        #     json={"project_id": project_id, "status": status, "video_url": video_url},
        #     headers={"Authorization": f"Bearer {self.config.activepieces_api_key}"}
        # )


# ============================================================================
# VIDEO EDITOR INTERFACE
# ============================================================================

class VideoEditorInterface:
    """
    Interface to the video editor (vuza or any other editor).
    This is a generic wrapper that you'll customize based on your actual editor.
    """
    
    def __init__(self, config: WorkflowConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def generate_config_file(self, project: VideoProject) -> Path:
        """
        Generate the video editor configuration file.
        This creates a JSON config (not YAML to avoid formatting errors).
        
        Adjust this based on your video editor's requirements.
        """
        self.logger.info(f"Generating config for project {project.project_id}")
        
        config_data = {
            "project": {
                "id": project.project_id,
                "title": project.title,
                "duration": self.config.video_duration,
                "resolution": {
                    "width": self.config.video_width,
                    "height": self.config.video_height
                },
                "fps": self.config.video_fps
            },
            "content": {
                "script": project.script,
                "keywords": project.keywords,
                "metadata": project.metadata
            },
            "output": {
                "path": str(self.config.output_dir / f"{project.project_id}.mp4"),
                "codec": self.config.video_codec,
                "audio_codec": self.config.audio_codec
            },
            "assets": {
                "images_dir": str(self.config.assets_dir / "images"),
                "audio_dir": str(self.config.assets_dir / "audio"),
                "video_dir": str(self.config.assets_dir / "video")
            }
        }
        
        # Save as JSON (more reliable than YAML for automation)
        config_file = self.config.temp_dir / f"config_{project.project_id}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Config saved to: {config_file}")
        return config_file
    
    def render_video(self, project: VideoProject, config_file: Path) -> bool:
        """
        Execute the video editor to render the video.
        Returns True on success, False on failure.
        """
        self.logger.info(f"Starting video render for project {project.project_id}")
        
        try:
            # Construct command based on your video editor
            # Example command structure - adjust to your editor:
            cmd = [
                sys.executable,  # Use current Python interpreter
                str(self.config.video_editor_path / self.config.video_editor_script),
                "--config", str(config_file),
                "--output", str(self.config.output_dir / f"{project.project_id}.mp4")
            ]
            
            self.logger.debug(f"Executing command: {' '.join(cmd)}")
            
            # Execute with timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.config.video_editor_path)
            )
            
            try:
                stdout, stderr = process.communicate(timeout=self.config.timeout)
                
                # Log output
                if stdout:
                    self.logger.debug(f"STDOUT:\n{stdout}")
                if stderr:
                    self.logger.warning(f"STDERR:\n{stderr}")
                
                if process.returncode == 0:
                    self.logger.info(f"Video rendered successfully: {project.project_id}")
                    return True
                else:
                    self.logger.error(f"Video render failed with code {process.returncode}")
                    return False
                    
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error(f"Video render timed out after {self.config.timeout}s")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during video render: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def verify_output(self, project: VideoProject) -> bool:
        """Verify that the output video was created and is valid"""
        output_file = self.config.output_dir / f"{project.project_id}.mp4"
        
        if not output_file.exists():
            self.logger.error(f"Output file not found: {output_file}")
            return False
        
        # Check file size (should be > 1MB for a 10-minute video)
        file_size = output_file.stat().st_size
        if file_size < 1_000_000:  # Less than 1MB
            self.logger.error(f"Output file suspiciously small: {file_size} bytes")
            return False
        
        self.logger.info(f"Output verified: {output_file} ({file_size / 1_000_000:.2f} MB)")
        return True


# ============================================================================
# WORKFLOW ORCHESTRATOR
# ============================================================================

class WorkflowOrchestrator:
    """Main workflow orchestration engine"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = setup_logging(config)
        self.activepieces = ActivePiecesClient(config, self.logger)
        self.video_editor = VideoEditorInterface(config, self.logger)
    
    def process_project(self, project: VideoProject) -> bool:
        """
        Process a single video project through the entire pipeline.
        Returns True on success, False on failure.
        """
        self.logger.info(f"="*80)
        self.logger.info(f"Processing project: {project.project_id}")
        self.logger.info(f"Title: {project.title}")
        self.logger.info(f"="*80)
        
        try:
            # Update status to processing
            project.status = "processing"
            project.save(self.config)
            self.activepieces.update_project_status(project.project_id, "processing")
            
            # Generate config file
            config_file = self.video_editor.generate_config_file(project)
            
            # Attempt video rendering with retries
            success = False
            for attempt in range(1, self.config.max_retries + 1):
                self.logger.info(f"Render attempt {attempt}/{self.config.max_retries}")
                
                success = self.video_editor.render_video(project, config_file)
                
                if success:
                    break
                else:
                    if attempt < self.config.max_retries:
                        self.logger.warning(f"Render failed, retrying in {self.config.retry_delay}s...")
                        time.sleep(self.config.retry_delay)
            
            if not success:
                raise Exception(f"Video rendering failed after {self.config.max_retries} attempts")
            
            # Verify output
            if not self.video_editor.verify_output(project):
                raise Exception("Output verification failed")
            
            # Update status to completed
            project.status = "completed"
            project.save(self.config)
            
            output_path = self.config.output_dir / f"{project.project_id}.mp4"
            video_url = f"file://{output_path.absolute()}"  # Replace with actual upload URL
            
            self.activepieces.update_project_status(project.project_id, "completed", video_url)
            
            self.logger.info(f"✓ Project {project.project_id} completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Project {project.project_id} failed: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            project.status = "failed"
            project.save(self.config)
            self.activepieces.update_project_status(project.project_id, "failed")
            
            return False
    
    def run(self):
        """Main workflow execution loop"""
        self.logger.info("Starting video automation workflow...")
        
        try:
            # Fetch pending projects
            projects = self.activepieces.fetch_pending_projects()
            
            if not projects:
                self.logger.info("No pending projects found")
                return
            
            self.logger.info(f"Found {len(projects)} pending project(s)")
            
            # Process each project
            results = []
            for project in projects:
                success = self.process_project(project)
                results.append((project.project_id, success))
            
            # Summary
            successful = sum(1 for _, success in results if success)
            failed = len(results) - successful
            
            self.logger.info("="*80)
            self.logger.info("WORKFLOW SUMMARY")
            self.logger.info(f"Total projects: {len(results)}")
            self.logger.info(f"Successful: {successful}")
            self.logger.info(f"Failed: {failed}")
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.critical(f"Workflow failed with error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            sys.exit(1)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def create_sample_project() -> VideoProject:
    """Create a sample project for testing"""
    return VideoProject(
        project_id=f"test_{int(time.time())}",
        title="Sample Video: Top 10 AI Tools",
        script="""
        Welcome to our video about the top 10 AI tools in 2026.
        
        Number 10: ChatGPT - The conversational AI that started it all.
        Number 9: Claude - Advanced reasoning and analysis capabilities.
        Number 8: Midjourney - Create stunning AI art in seconds.
        
        [Continue with more content...]
        
        Thanks for watching! Don't forget to like and subscribe.
        """,
        keywords=["AI", "technology", "artificial intelligence", "tools", "2026"],
        metadata={
            "target_duration": 600,
            "style": "professional",
            "voice": "en-US-AriaNeural",
            "background_music": True
        }
    )


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Long-Form Video Automation Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--mode",
        choices=["run", "test", "validate"],
        default="run",
        help="Execution mode: run (process real projects), test (use sample project), validate (check setup)"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to custom configuration file (JSON)"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config and args.config.exists():
        with open(args.config) as f:
            config_data = json.load(f)
        config = WorkflowConfig(**config_data)
    else:
        config = WorkflowConfig()
    
    # Create orchestrator
    orchestrator = WorkflowOrchestrator(config)
    
    if args.mode == "validate":
        orchestrator.logger.info("Validating setup...")
        orchestrator.logger.info(f"Work directory: {config.work_dir}")
        orchestrator.logger.info(f"Video editor path: {config.video_editor_path}")
        orchestrator.logger.info("✓ Validation complete")
        
    elif args.mode == "test":
        orchestrator.logger.info("Running in TEST mode with sample project")
        sample_project = create_sample_project()
        orchestrator.process_project(sample_project)
        
    else:
        orchestrator.run()


if __name__ == "__main__":
    main()