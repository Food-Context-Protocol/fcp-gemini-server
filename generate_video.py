#!/usr/bin/env python3
"""
FCP Demo Video Generator
Automates video creation using Gemini 3 technologies

Usage:
    python generate_video.py --mode full     # Generate everything with AI
    python generate_video.py --mode hybrid   # Use screenshots + AI
    python generate_video.py --mode test     # Test single asset generation
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import argparse
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
import google.generativeai as genai
from google.cloud import texttospeech
import ffmpeg
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class AssetConfig:
    """Configuration for a single asset generation"""
    name: str
    type: str  # 'video', 'image', 'audio'
    model: str
    prompt: str
    duration: Optional[int] = None
    resolution: Optional[str] = "1080p"
    aspect_ratio: Optional[str] = "16:9"
    quality: Optional[str] = "high"
    audio_enabled: bool = False


class FCPVideoGenerator:
    """
    Automated video generator for Food Context Protocol demo
    """

    def __init__(self, api_key: str, output_dir: str = "assets"):
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Configure Gemini
        genai.configure(api_key=api_key)

        # TTS client
        self.tts_client = texttospeech.TextToSpeechClient()

        console.print("[bold green]FCP Video Generator initialized[/bold green]")

    def get_cache_key(self, **kwargs) -> str:
        """Create unique cache key from generation parameters"""
        cache_str = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    def generate_video_with_retry(self, **kwargs):
        """Generate video with automatic retry on rate limits"""
        try:
            return genai.generate_video(**kwargs)
        except Exception as e:
            if "rate_limit" in str(e).lower():
                console.print("[yellow]Rate limited, waiting before retry...[/yellow]")
                time.sleep(30)
                raise  # Trigger retry
            else:
                raise  # Don't retry other errors

    def generate_title_sequence(self) -> str:
        """Generate opening title animation"""
        console.print("\n[bold cyan]🎬 Generating title sequence...[/bold cyan]")

        cache_key = self.get_cache_key(
            type="title_sequence",
            model="veo-3.1",
            duration=8
        )
        cache_file = self.cache_dir / f"{cache_key}.mp4"

        if cache_file.exists():
            console.print("✓ Using cached title sequence")
            return str(cache_file)

        video = self.generate_video_with_retry(
            model="veo-3.1",
            prompt="""
            Cinematic title sequence for a tech protocol launch.

            Scene: A rotating holographic display of fresh food ingredients
            (colorful vegetables, fruits, grains, proteins) slowly materializing
            from digital particles. As they rotate, they begin transforming into
            flowing data streams and network connections, all converging into a
            central glowing protocol symbol (abstract geometric design).

            Style: Modern tech aesthetic, clean and professional
            Lighting: Soft volumetric lighting with blue-green gradients
            Camera: Slow orbital rotation, starting wide and pushing in
            Effects: Subtle particle systems, holographic shimmer
            Color palette: Deep blues, vibrant greens, warm food tones

            Duration: 8 seconds
            Resolution: 1080p
            Aspect ratio: 16:9
            """,
            duration=8,
            resolution="1080p",
            audio_enabled=True
        )

        video.save(str(cache_file))
        output_path = self.output_dir / "01_title_sequence.mp4"
        video.save(str(output_path))

        console.print(f"✓ Saved to {output_path}")
        return str(output_path)

    def generate_backgrounds(self) -> Dict[str, str]:
        """Generate all background videos"""
        console.print("\n[bold cyan]🎨 Generating background videos...[/bold cyan]")

        backgrounds = {
            "problem": {
                "prompt": """
                Slow camera pan across a modern home kitchen counter in natural daylight.

                Scene setup:
                - Clean, minimalist kitchen with white/light gray countertops
                - Fresh ingredients scattered naturally: colorful vegetables, fruits
                - Wooden cutting board with knife
                - Smartphone laying face-up on counter (modern iPhone or Android)
                - Natural window lighting from left side, soft shadows

                Camera movement:
                - Starts wide on left showing window and ingredient array
                - Slow horizontal pan right (dolly movement, NOT handheld)
                - Ends focused on smartphone in foreground
                - Smooth, cinematic camera movement (no shake)

                Color grading:
                - Slightly desaturated (0.8x saturation)
                - Warm color temperature suggesting morning light
                - Shallow depth of field (f/2.8), background soft blur

                Mood: Thoughtful, contemplative, suggesting a problem to solve
                Duration: 10 seconds, 1080p, 16:9
                """,
                "duration": 10
            },

            "solution": {
                "prompt": """
                Abstract visualization of a distributed network system forming connections.

                Visual elements:
                - Starts with isolated geometric nodes (spheres) scattered in 3D space
                - Nodes begin connecting with animated lines (network edges)
                - Lines flow with subtle particle animation showing data transfer
                - Nodes pulse gently when connections form
                - Network gradually becomes interconnected (not fully, ~60% connected)

                Technical style:
                - Dark background (#0A192F, deep blue-black)
                - Nodes: Glowing cyan (#00D4AA) with soft glow
                - Connection lines: Bright cyan with subtle white core
                - Particles: White with cyan trail
                - Depth of field: Foreground nodes sharp, background slightly blurred

                Camera:
                - Slow orbital rotation around the network (15-degree arc)
                - Subtle push-in (dolly forward) throughout
                - Smooth, professional motion graphics style

                Mood: Innovative, connective, problem solved, technical elegance
                Duration: 15 seconds, 1080p, 16:9
                """,
                "duration": 15
            },

            "demo": {
                "prompt": """
                Over-the-shoulder POV of hands using smartphone to photograph a meal.

                Scene:
                - Modern restaurant table setting, natural wood table
                - Colorful, appetizing meal in center: grilled salmon with vegetables
                - Hands holding modern smartphone, positioned to photograph meal
                - Restaurant ambient lighting: warm, slightly dimmed (evening ambiance)
                - Subtle bokeh from restaurant lights in far background

                Action:
                - Hands position phone above meal
                - Camera (our view) shows phone screen capturing the meal
                - Phone screen shows UI overlay: "Analyzing..." text appears
                - Professional product photography style

                Camera:
                - Steady, over-shoulder angle (~45 degrees from vertical)
                - Focus on phone and meal (sharp), background soft
                - No camera movement (locked tripod shot)
                - Depth of field: f/2.0

                Duration: 12 seconds, 1080p, 16:9
                """,
                "duration": 12
            }
        }

        generated = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for name, config in backgrounds.items():
                task = progress.add_task(f"Generating {name} background...", total=1)

                cache_key = self.get_cache_key(
                    type=f"bg_{name}",
                    model="veo-3.1",
                    prompt=config["prompt"][:100]  # Use first 100 chars for cache
                )
                cache_file = self.cache_dir / f"{cache_key}.mp4"

                if cache_file.exists():
                    console.print(f"✓ Using cached {name} background")
                    output_path = self.output_dir / f"bg_{name}.mp4"
                    # Copy from cache
                    import shutil
                    shutil.copy(cache_file, output_path)
                    generated[name] = str(output_path)
                    progress.update(task, completed=1)
                    continue

                video = self.generate_video_with_retry(
                    model="veo-3.1",
                    prompt=config["prompt"],
                    duration=config["duration"],
                    resolution="1080p",
                    audio_enabled=True
                )

                video.save(str(cache_file))
                output_path = self.output_dir / f"bg_{name}.mp4"
                video.save(str(output_path))
                generated[name] = str(output_path)

                console.print(f"✓ Saved {name} background")
                progress.update(task, completed=1)
                time.sleep(5)  # Rate limiting

        return generated

    def generate_static_assets(self) -> Dict[str, str]:
        """Generate logos, icons, diagrams with Imagen 3"""
        console.print("\n[bold cyan]🖼️  Generating static assets...[/bold cyan]")

        assets = {
            "fcp_logo": {
                "prompt": """
                Professional technology logo for 'Food Context Protocol' (FCP).

                Design elements:
                - Central icon: Abstract fusion of a fork silhouette and data flow lines
                - Fork transforms into flowing network connections at the tips
                - Geometric, modern, minimalist aesthetic
                - Forms an abstract 'F' shape

                Typography:
                - 'FCP' in bold, modern sans-serif (like Inter or Poppins)
                - 'Food Context Protocol' underneath in lighter weight
                - Clean, professional tech brand feel

                Color scheme:
                - Primary: Fresh green (#4CAF50) transitioning to tech blue (#2196F3)
                - Use gradient for the fork/data icon
                - Text in dark gray (#212121)

                Layout:
                - Icon above text, centered
                - Scalable design, works at any size
                - Plenty of whitespace
                - Square format with transparent background

                Style: Flat design, modern tech startup aesthetic, reminiscent of
                Stripe, Vercel, or GitHub logos. Clean, professional, scalable.
                """,
                "aspect_ratio": "1:1",
                "quality": "high"
            },

            "gemini_badge": {
                "prompt": """
                'Powered by Gemini 3' badge for video overlay.

                Design:
                - Horizontal rectangular badge with rounded corners (30px radius)
                - Width: 300px, Height: 80px
                - Semi-transparent dark background: rgba(26, 35, 126, 0.9)
                - Subtle glow effect around edges: soft blue (#4285F4) glow

                Content:
                - Left side: Google Gemini sparkle icon (colorful, recognizable)
                - Right side: Text in two lines
                  - Line 1: "POWERED BY" (small, uppercase, light gray)
                  - Line 2: "Gemini 3" (larger, white, bold)

                Style:
                - Google brand colors (blue #4285F4, red #EA4335, yellow #FBBC04, green #34A853)
                - Modern, professional, suitable for video corner overlay
                - High contrast for visibility over various backgrounds
                """,
                "aspect_ratio": "4:1",
                "quality": "high"
            },

            "architecture_diagram": {
                "prompt": """
                Technical architecture diagram for Food Context Protocol (FCP).

                Layout (horizontal, left-to-right flow):

                TOP TIER - Client Applications:
                - Mobile app icon (smartphone symbol)
                - Web browser icon (browser window symbol)
                - CLI terminal icon (command line symbol)
                - Claude Desktop icon (stylized AI assistant)
                Arranged horizontally with equal spacing

                MIDDLE TIER - FCP Server:
                - Large central rounded rectangle labeled "FCP SERVER"
                - Two bidirectional arrows coming down from clients:
                  - Left arrow labeled "MCP stdio"
                  - Right arrow labeled "REST HTTP"
                - Internal icons showing: Database, API Router, Tool Registry

                BOTTOM TIER - Gemini 3 Services:
                - Six icons representing features:
                  - Eye icon: "Vision"
                  - Magnifying glass: "Grounding"
                  - Brain icon: "Thinking"
                  - Code brackets: "Code Execution"
                  - Microphone: "Live API"
                  - Layers: "Context Caching"
                - Arrows flowing up to FCP Server

                Style:
                - Clean, professional technical diagram
                - Color coding:
                  - Clients: Blue (#2196F3)
                  - FCP Server: Green (#4CAF50)
                  - Gemini: Orange/Red gradient (#FF9800 to #F44336)
                - White or light gray background (#FAFAFA)
                - Icons: Simple, line-art style, consistent thickness
                - Text: Sans-serif, clear hierarchy (16pt for labels, 12pt for descriptions)
                - Arrows: Solid lines with arrowheads, labeled clearly
                - Subtle drop shadows for depth

                Format: Wide horizontal layout (16:9 aspect ratio), suitable for
                full-screen video presentation. High resolution for clarity when displayed.
                """,
                "aspect_ratio": "16:9",
                "quality": "high"
            }
        }

        generated = {}
        for name, config in assets.items():
            console.print(f"Generating {name}...")

            cache_key = self.get_cache_key(
                type=f"image_{name}",
                model="imagen-3",
                prompt=config["prompt"][:100]
            )
            cache_file = self.cache_dir / f"{cache_key}.png"

            if cache_file.exists():
                console.print(f"✓ Using cached {name}")
                output_path = self.output_dir / f"{name}.png"
                import shutil
                shutil.copy(cache_file, output_path)
                generated[name] = str(output_path)
                continue

            image = genai.generate_image(
                model="imagen-3",
                prompt=config["prompt"],
                aspect_ratio=config["aspect_ratio"],
                quality=config["quality"]
            )

            image.save(str(cache_file))
            output_path = self.output_dir / f"{name}.png"
            image.save(str(output_path))
            generated[name] = str(output_path)

            console.print(f"✓ Saved to {output_path}")
            time.sleep(3)  # Rate limiting

        return generated

    def convert_screenshots_to_video(self, screenshot_dir: str) -> List[str]:
        """Convert UI screenshots to animated demos using Image-to-Video"""
        console.print("\n[bold cyan]📸 Converting screenshots to video...[/bold cyan]")

        screenshot_path = Path(screenshot_dir)
        if not screenshot_path.exists():
            console.print(f"[yellow]Warning: Screenshot directory not found: {screenshot_dir}[/yellow]")
            console.print("[yellow]Run with --help to see screenshot capture guide[/yellow]")
            return []

        screenshot_animations = {
            "meal_analysis_input": {
                "screenshot": "02_meal_analysis_input.png",
                "prompt": """
                Animate this food analysis interface screenshot.

                Animation sequence:
                1. Start static for 1 second
                2. User's finger enters from bottom-right
                3. Finger taps "Upload Photo" button with ripple effect
                4. Button highlights (pressed state)
                5. File picker dialog slides up from bottom
                6. Image thumbnail of chicken salad fades in
                7. "Analyze" button pulses gently (call to action)

                Style:
                - Realistic touch interactions (finger shadow, button press)
                - Smooth UI transitions (ease-in-out curves)
                - Professional app demo aesthetic
                - Keep colors and branding from screenshot

                Camera: Static, no camera movement (pure UI animation)
                Duration: 6 seconds, 1080p
                """,
                "duration": 6
            },

            "meal_analysis_results": {
                "screenshot": "03_meal_analysis_results.png",
                "prompt": """
                Animate this nutrition results display.

                Animation sequence:
                1. Start with blank result area
                2. Meal photo fades in at top
                3. Nutrition cards slide in from right, one by one:
                   - Calories card (0.5s delay)
                   - Protein/carbs/fat card (1.0s delay)
                   - Allergen warning badges (1.5s delay)
                   - Ingredients list (2.0s delay)
                4. Each card has subtle bounce on entry
                5. Allergen badges pulse gently (attention grabbing)
                6. Hold final frame for 2 seconds

                Style:
                - Material Design-style elevation (subtle shadows)
                - Smooth staggered animations
                - Professional data visualization

                Camera: Slow subtle zoom in (1.05x) throughout
                Duration: 8 seconds, 1080p
                """,
                "duration": 8
            }
        }

        demos = []
        for name, config in screenshot_animations.items():
            screenshot_file = screenshot_path / config["screenshot"]

            if not screenshot_file.exists():
                console.print(f"[yellow]Skipping {name}: screenshot not found[/yellow]")
                continue

            console.print(f"Converting {name}...")

            cache_key = self.get_cache_key(
                type=f"demo_{name}",
                model="veo-3.1",
                screenshot=str(screenshot_file),
                prompt=config["prompt"][:100]
            )
            cache_file = self.cache_dir / f"{cache_key}.mp4"

            if cache_file.exists():
                console.print(f"✓ Using cached {name}")
                output_path = self.output_dir / f"demo_{name}.mp4"
                import shutil
                shutil.copy(cache_file, output_path)
                demos.append(str(output_path))
                continue

            video = genai.generate_video_from_image(
                model="veo-3.1",
                source_image=str(screenshot_file),
                prompt=config["prompt"],
                duration=config["duration"],
                resolution="1080p"
            )

            video.save(str(cache_file))
            output_path = self.output_dir / f"demo_{name}.mp4"
            video.save(str(output_path))
            demos.append(str(output_path))

            console.print(f"✓ Saved to {output_path}")
            time.sleep(10)  # Longer wait for Image-to-Video

        return demos

    def generate_voiceover(self) -> List[str]:
        """Generate voiceover narration with Gemini TTS"""
        console.print("\n[bold cyan]🎙️  Generating voiceover...[/bold cyan]")

        voice_config = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-M",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.05,
            pitch=0.0,
            volume_gain_db=0.0,
            effects_profile_id=["large-home-entertainment-class-device"]
        )

        voiceover_segments = [
            {
                "section": "intro",
                "text": """
                <speak>
                What if your phone could understand food
                <emphasis level="moderate">like a nutritionist?</emphasis>
                <break time="500ms"/>
                FCP uses <emphasis level="strong">fifteen-plus Gemini 3 features</emphasis>
                to transform food photos, voice commands, and videos into
                instant nutrition insights.
                </speak>
                """
            },
            {
                "section": "demo_overview",
                "text": """
                <speak>
                In the next three minutes, I'll show you how Gemini's multimodal A-I
                powers every feature of this platform.
                </speak>
                """
            },
            {
                "section": "impact",
                "text": """
                <speak>
                FCP transforms manual food tracking into an intelligent conversation.
                <break time="300ms"/>
                Every feature is production-grade: typed schemas, error handling,
                rate limiting, and <emphasis>one hundred percent test coverage</emphasis>.
                </speak>
                """
            },
            {
                "section": "cta",
                "text": """
                <speak>
                Try it yourself at
                <prosody rate="slow">A-P-I dot F-C-P dot dev</prosody>.
                <break time="300ms"/>
                No login required.
                </speak>
                """
            }
        ]

        voiceovers = []
        for segment in voiceover_segments:
            synthesis_input = texttospeech.SynthesisInput(ssml=segment["text"])

            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )

            filename = self.output_dir / f"vo_{segment['section']}.mp3"
            with open(filename, "wb") as out:
                out.write(response.audio_content)

            voiceovers.append(str(filename))
            console.print(f"✓ Generated {filename.name}")

        return voiceovers

    def validate_asset(
        self,
        asset_path: str,
        expected_duration: Optional[int] = None,
        expected_resolution: Optional[Tuple[int, int]] = None
    ) -> Tuple[bool, str]:
        """Validate generated asset meets requirements"""
        if not Path(asset_path).exists():
            return False, "File not found"

        try:
            probe = ffmpeg.probe(asset_path)

            # Check duration
            if expected_duration:
                actual_duration = float(probe['format']['duration'])
                if abs(actual_duration - expected_duration) > 1.0:
                    return False, f"Duration mismatch: {actual_duration:.1f}s (expected {expected_duration}s)"

            # Check resolution (if video)
            if expected_resolution:
                video_streams = [s for s in probe['streams'] if s['codec_type'] == 'video']
                if video_streams:
                    video_stream = video_streams[0]
                    actual_res = (int(video_stream['width']), int(video_stream['height']))
                    if actual_res != expected_resolution:
                        return False, f"Resolution mismatch: {actual_res} (expected {expected_resolution})"

            return True, "OK"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def generate_complete_video(self, screenshot_dir: str = "screenshots", mode: str = "full"):
        """Run complete video generation pipeline"""
        console.print("\n[bold magenta]🚀 Starting FCP Demo Video Generation Pipeline[/bold magenta]")
        console.print("=" * 60)

        try:
            if mode in ["full", "hybrid"]:
                # Phase 2: Generate assets
                console.print("\n[bold]📦 Phase 1: Asset Generation[/bold]")
                self.generate_title_sequence()
                self.generate_backgrounds()
                self.generate_static_assets()

            if mode in ["full", "hybrid"]:
                # Phase 3: Convert demos
                console.print("\n[bold]🎥 Phase 2: Demo Video Creation[/bold]")
                self.convert_screenshots_to_video(screenshot_dir)

            if mode in ["full", "hybrid"]:
                # Phase 4: Audio
                console.print("\n[bold]🎵 Phase 3: Audio Production[/bold]")
                self.generate_voiceover()

            console.print("\n[bold green]✅ Generation pipeline complete![/bold green]")
            console.print(f"[bold]All assets saved to: {self.output_dir}[/bold]")

            console.print("\n[bold yellow]⚠️  Next steps:[/bold yellow]")
            console.print("1. Review generated assets in the 'assets/' directory")
            console.print("2. Use FFmpeg to assemble final video (see storyboard.md)")
            console.print("3. Add text overlays and color grading")
            console.print("4. Export final video for upload")

        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {str(e)}[/bold red]")
            raise


def test_single_asset():
    """Test generation with a simple asset"""
    console.print("[bold cyan]🧪 Testing asset generation...[/bold cyan]")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not set[/red]")
        sys.exit(1)

    generator = FCPVideoGenerator(api_key, output_dir="test_assets")

    try:
        # Test with a simple image
        console.print("\nGenerating test logo...")

        image = genai.generate_image(
            model="imagen-3",
            prompt="""
            Simple test icon: A blue circle with white checkmark inside.
            Clean, minimal design. 512x512px. Transparent background.
            """,
            aspect_ratio="1:1",
            quality="high"
        )

        output_path = "test_assets/test_logo.png"
        image.save(output_path)

        console.print(f"[green]✓ Test asset generated: {output_path}[/green]")
        console.print("[green]✓ Gemini API is working correctly![/green]")

    except Exception as e:
        console.print(f"[red]✗ Test failed: {str(e)}[/red]")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="FCP Demo Video Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_video.py --mode test           # Test API access
  python generate_video.py --mode full           # Generate everything
  python generate_video.py --mode hybrid         # Use screenshots + AI
  python generate_video.py --screenshots ./ui    # Custom screenshot path
        """
    )

    parser.add_argument(
        "--mode",
        choices=["full", "hybrid", "test"],
        default="hybrid",
        help="Generation mode: full (AI everything), hybrid (screenshots+AI), test (single asset)"
    )

    parser.add_argument(
        "--screenshots",
        default="screenshots",
        help="Directory containing UI screenshots (default: screenshots/)"
    )

    parser.add_argument(
        "--output",
        default="assets",
        help="Output directory for generated assets (default: assets/)"
    )

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY environment variable not set[/red]")
        console.print("\nSet it with:")
        console.print("  export GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)

    if args.mode == "test":
        test_single_asset()
    else:
        generator = FCPVideoGenerator(api_key, output_dir=args.output)
        generator.generate_complete_video(
            screenshot_dir=args.screenshots,
            mode=args.mode
        )


if __name__ == "__main__":
    main()
