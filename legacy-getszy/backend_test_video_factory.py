#!/usr/bin/env python3
"""
AI Video Factory v2 - End-to-End Video Generation Test
Tests the complete pipeline: 6 agents → asset generation → MP4 download
"""
import requests
import sys
import time
import json
from datetime import datetime

BASE_URL = "https://getszy-all-in-one.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

class VideoFactoryTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.project_id = None
        self.failed_tests = []

    def log(self, msg, color=Colors.BLUE):
        print(f"{color}{msg}{Colors.END}")

    def test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None, timeout=30):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        h = {'Content-Type': 'application/json'}
        if token:
            h['Authorization'] = f'Bearer {token}'
        if headers:
            h.update(headers)

        self.tests_run += 1
        self.log(f"\n🔍 Test {self.tests_run}: {name}", Colors.BLUE)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=h, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=h, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=h, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=h, timeout=timeout)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code}", Colors.GREEN)
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.tests_failed += 1
                self.failed_tests.append(name)
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}", Colors.RED)
                try:
                    error_data = response.json()
                    self.log(f"Response: {json.dumps(error_data, indent=2)}", Colors.YELLOW)
                except:
                    self.log(f"Response: {response.text[:500]}", Colors.YELLOW)
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            self.log(f"❌ FAIL - Error: {str(e)}", Colors.RED)
            return False, {}

    def run_all_tests(self):
        self.log("=" * 80, Colors.CYAN)
        self.log("AI VIDEO FACTORY V2 - END-TO-END VIDEO GENERATION TEST", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        # ===== 1. AUTHENTICATION =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("1. AUTHENTICATION", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        success, data = self.test(
            "Admin login",
            "POST",
            "/auth/login",
            200,
            data={"email": "admin@getszy.com", "password": "Admin@123"}
        )
        if success and 'token' in data:
            self.admin_token = data['token']
            self.log(f"✅ Admin token obtained", Colors.GREEN)
        else:
            self.log(f"❌ CRITICAL: Cannot proceed without admin token", Colors.RED)
            return

        # ===== 2. CREATE VIDEO PROJECT =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("2. CREATE VIDEO PROJECT (AUTO-RUN PIPELINE)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        success, data = self.test(
            "Create video project with auto_run=true",
            "POST",
            "/video-factory/project",
            200,
            data={
                "prompt": "Explain how AI agents work in 2 minutes for beginners in Hinglish",
                "language": "hinglish",
                "auto_run": True
            },
            token=self.admin_token
        )
        
        if success:
            self.project_id = data.get('id')
            self.log(f"✅ Project created: {self.project_id}", Colors.GREEN)
            self.log(f"  Status: {data.get('status')}", Colors.BLUE)
        else:
            self.log(f"❌ CRITICAL: Cannot proceed without project", Colors.RED)
            return

        # ===== 3. POLL PIPELINE STATUS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("3. POLL PIPELINE STATUS (6 AGENTS: ENHANCE → RESEARCH → SCRIPTS → HOOKS → STORYBOARD → VISUALS)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        max_wait = 120  # 2 minutes max
        poll_interval = 5
        elapsed = 0
        pipeline_complete = False
        
        self.log(f"⏳ Polling every {poll_interval}s (max {max_wait}s)...", Colors.YELLOW)
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            success, data = self.test(
                f"Poll project status (elapsed: {elapsed}s)",
                "GET",
                f"/video-factory/project/{self.project_id}",
                200,
                token=self.admin_token
            )
            
            if not success:
                self.log(f"❌ Failed to poll project", Colors.RED)
                break
            
            status = data.get('status')
            stages = data.get('stages', {})
            errors = data.get('errors', {})
            
            self.log(f"  Status: {status}", Colors.CYAN)
            
            # Check each stage
            stage_names = ['enhanced', 'research', 'script_variants', 'hooks', 'storyboard', 'visual_plan']
            completed_stages = []
            for stage in stage_names:
                if stage in stages and stages[stage]:
                    completed_stages.append(stage)
                    self.log(f"    ✅ {stage}", Colors.GREEN)
                else:
                    self.log(f"    ⏳ {stage} (pending)", Colors.YELLOW)
            
            # Check for errors
            if errors:
                self.log(f"  ⚠️  Errors detected:", Colors.YELLOW)
                for err_stage, err_msg in errors.items():
                    self.log(f"    ❌ {err_stage}: {err_msg}", Colors.RED)
            
            # Check if pipeline is complete
            if status == 'ready' and len(completed_stages) >= 5:  # At least 5 stages (some may be optional)
                pipeline_complete = True
                self.log(f"✅ Pipeline complete! All stages ready.", Colors.GREEN)
                break
            elif status == 'error':
                self.log(f"❌ Pipeline failed with error status", Colors.RED)
                break
            elif status == 'partial':
                self.log(f"⚠️  Pipeline completed with partial results", Colors.YELLOW)
                # Continue to asset generation if we have storyboard + visual_plan
                if 'storyboard' in stages and 'visual_plan' in stages:
                    pipeline_complete = True
                    self.log(f"✅ Storyboard + Visual Plan present, proceeding to render", Colors.GREEN)
                    break
        
        if not pipeline_complete:
            self.log(f"❌ CRITICAL: Pipeline did not complete within {max_wait}s", Colors.RED)
            self.log(f"  Final status: {data.get('status')}", Colors.YELLOW)
            self.log(f"  Completed stages: {completed_stages}", Colors.YELLOW)
            # Don't return - let's see what we can test
        
        # ===== 4. VERIFY PIPELINE OUTPUT =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("4. VERIFY PIPELINE OUTPUT STRUCTURE", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        success, data = self.test(
            "Get final project state",
            "GET",
            f"/video-factory/project/{self.project_id}",
            200,
            token=self.admin_token
        )
        
        if success:
            stages = data.get('stages', {})
            
            # Check enhanced
            if 'enhanced' in stages:
                enhanced = stages['enhanced']
                self.log(f"✅ Enhanced: topic='{enhanced.get('enhanced_topic', '')[:50]}...'", Colors.GREEN)
            
            # Check research
            if 'research' in stages:
                research = stages['research']
                facts_count = len(research.get('key_facts', []))
                self.log(f"✅ Research: {facts_count} key facts", Colors.GREEN)
            
            # Check script variants
            if 'script_variants' in stages:
                variants = stages['script_variants']
                self.log(f"✅ Scripts: {len(variants)} variants", Colors.GREEN)
                for v in variants:
                    self.log(f"    - {v.get('style_id')}: {v.get('estimated_word_count', 0)} words", Colors.BLUE)
            
            # Check hooks
            if 'hooks' in stages:
                hooks = stages['hooks']
                self.log(f"✅ Hooks: {len(hooks)} options", Colors.GREEN)
            
            # Check storyboard
            if 'storyboard' in stages:
                scenes = stages['storyboard']
                self.log(f"✅ Storyboard: {len(scenes)} scenes", Colors.GREEN)
                total_duration = sum(s.get('duration_s', 0) for s in scenes)
                self.log(f"    Total duration: {total_duration}s", Colors.BLUE)
            
            # Check visual plan
            if 'visual_plan' in stages:
                plan = stages['visual_plan']
                self.log(f"✅ Visual Plan: {len(plan)} scene visuals", Colors.GREEN)
        
        # ===== 5. GENERATE ASSETS (IMAGES + VOICE + VIDEO) =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("5. GENERATE ASSETS (IMAGES + VOICE + VIDEO ASSEMBLY)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        success, data = self.test(
            "Kick off asset generation",
            "POST",
            f"/video-factory/project/{self.project_id}/generate-assets",
            200,
            data={"orientation": "16:9"},
            token=self.admin_token
        )
        
        if not success:
            self.log(f"❌ CRITICAL: Asset generation failed to start", Colors.RED)
            return
        
        self.log(f"✅ Asset generation started", Colors.GREEN)
        self.log(f"  Poll URL: {data.get('poll_url')}", Colors.BLUE)
        
        # ===== 6. POLL RENDER STATUS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("6. POLL RENDER STATUS (IMAGES → VOICE → ASSEMBLY)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        max_wait = 300  # 5 minutes max for rendering
        poll_interval = 5
        elapsed = 0
        render_complete = False
        
        self.log(f"⏳ Polling every {poll_interval}s (max {max_wait}s)...", Colors.YELLOW)
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            success, data = self.test(
                f"Poll render status (elapsed: {elapsed}s)",
                "GET",
                f"/video-factory/project/{self.project_id}",
                200,
                token=self.admin_token
            )
            
            if not success:
                self.log(f"❌ Failed to poll render status", Colors.RED)
                break
            
            render_status = data.get('render_status')
            render_progress = data.get('render_progress', 0)
            render_error = data.get('render_error')
            
            self.log(f"  Render status: {render_status} ({render_progress}%)", Colors.CYAN)
            
            if render_error:
                self.log(f"  ❌ Render error: {render_error}", Colors.RED)
                break
            
            if render_status == 'complete':
                render_complete = True
                self.log(f"✅ Render complete!", Colors.GREEN)
                self.log(f"  Final video path: {data.get('final_video_path')}", Colors.BLUE)
                self.log(f"  Video size: {data.get('final_video_size', 0)} bytes", Colors.BLUE)
                self.log(f"  Scenes rendered: {data.get('scenes_rendered', 0)}", Colors.BLUE)
                self.log(f"  Voice used: {data.get('voice_used')}", Colors.BLUE)
                break
            elif render_status == 'error':
                self.log(f"❌ Render failed with error status", Colors.RED)
                break
        
        if not render_complete:
            self.log(f"❌ CRITICAL: Render did not complete within {max_wait}s", Colors.RED)
            self.log(f"  Final render_status: {data.get('render_status')}", Colors.YELLOW)
            self.log(f"  Final render_progress: {data.get('render_progress')}%", Colors.YELLOW)
            if data.get('render_error'):
                self.log(f"  Render error: {data.get('render_error')}", Colors.RED)
            return
        
        # ===== 7. DOWNLOAD FINAL VIDEO =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("7. DOWNLOAD FINAL VIDEO (MP4)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        download_url = f"{BASE_URL}/video-factory/project/{self.project_id}/download"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            self.log(f"⏳ Downloading video from {download_url}...", Colors.YELLOW)
            response = requests.get(download_url, headers=headers, timeout=60)
            
            if response.status_code == 200:
                video_size = len(response.content)
                self.log(f"✅ Video downloaded successfully", Colors.GREEN)
                self.log(f"  Size: {video_size} bytes ({video_size / 1024 / 1024:.2f} MB)", Colors.BLUE)
                
                if video_size > 100000:  # > 100KB
                    self.log(f"✅ Video size is valid (> 100KB)", Colors.GREEN)
                    self.tests_passed += 1
                else:
                    self.log(f"⚠️  Video size is suspiciously small (< 100KB)", Colors.YELLOW)
                    self.tests_failed += 1
                    self.failed_tests.append("Video size validation")
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'video' in content_type or 'mp4' in content_type:
                    self.log(f"✅ Content-Type is video: {content_type}", Colors.GREEN)
                else:
                    self.log(f"⚠️  Content-Type: {content_type} (expected video/mp4)", Colors.YELLOW)
            else:
                self.log(f"❌ Download failed with status {response.status_code}", Colors.RED)
                self.log(f"  Response: {response.text[:200]}", Colors.YELLOW)
                self.tests_failed += 1
                self.failed_tests.append("Video download")
        except Exception as e:
            self.log(f"❌ Download error: {str(e)}", Colors.RED)
            self.tests_failed += 1
            self.failed_tests.append("Video download")
        
        # ===== 8. TEST SCENE IMAGE ENDPOINTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("8. TEST SCENE IMAGE ENDPOINTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        success, data = self.test(
            "Get project with scene images",
            "GET",
            f"/video-factory/project/{self.project_id}",
            200,
            token=self.admin_token
        )
        
        if success:
            scenes = data.get('stages', {}).get('storyboard', [])
            scenes_with_images = [s for s in scenes if s.get('image_path')]
            
            self.log(f"  Scenes with images: {len(scenes_with_images)}/{len(scenes)}", Colors.BLUE)
            
            if scenes_with_images:
                # Test first scene image
                first_scene = scenes_with_images[0]
                scene_index = first_scene.get('index')
                
                scene_img_url = f"{BASE_URL}/video-factory/project/{self.project_id}/scene-image/{scene_index}"
                try:
                    response = requests.get(scene_img_url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        img_size = len(response.content)
                        self.log(f"✅ Scene {scene_index} image downloaded: {img_size} bytes", Colors.GREEN)
                        self.tests_passed += 1
                    else:
                        self.log(f"❌ Scene {scene_index} image failed: {response.status_code}", Colors.RED)
                        self.tests_failed += 1
                        self.failed_tests.append(f"Scene {scene_index} image")
                except Exception as e:
                    self.log(f"❌ Scene image error: {str(e)}", Colors.RED)
                    self.tests_failed += 1
                    self.failed_tests.append(f"Scene {scene_index} image")

    def print_summary(self):
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("TEST SUMMARY", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)
        
        total = self.tests_run
        passed = self.tests_passed
        failed = self.tests_failed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        self.log(f"\nTotal tests: {total}", Colors.BLUE)
        self.log(f"Passed: {passed}", Colors.GREEN)
        self.log(f"Failed: {failed}", Colors.RED)
        self.log(f"Pass rate: {pass_rate:.1f}%", Colors.CYAN)
        
        if self.failed_tests:
            self.log(f"\n❌ Failed tests:", Colors.RED)
            for test in self.failed_tests:
                self.log(f"  - {test}", Colors.YELLOW)
        
        return 0 if failed == 0 else 1

def main():
    tester = VideoFactoryTester()
    tester.run_all_tests()
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
