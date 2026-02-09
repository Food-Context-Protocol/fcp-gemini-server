#!/usr/bin/env python3
"""
Test Script for Gemini 3 Asset Generation
Tests API access and generates sample assets

Usage:
    python test_generation.py                    # Test all APIs
    python test_generation.py --asset logo       # Generate logo only
    python test_generation.py --asset video      # Generate video only
"""

import os
import sys
import argparse
import time
from pathlib import Path

import google.generativeai as genai
from google.cloud import texttospeech
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def test_api_access():
    """Test that all Gemini APIs are accessible"""
    console.print("\n[bold cyan]🔍 Testing API Access...[/bold cyan]\n")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]❌ GEMINI_API_KEY not set[/red]")
        console.print("\nSet it with:")
        console.print("  export GEMINI_API_KEY=your_api_key_here")
        return False

    genai.configure(api_key=api_key)

    # Test Imagen
    try:
        console.print("Testing Imagen 3... ", end="")
        test_image = genai.generate_image(
            model="imagen-3",
            prompt="A simple blue circle on white background",
            aspect_ratio="1:1",
            quality="high"
        )
        console.print("[green]✓ Working[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed: {str(e)}[/red]")
        return False

    # Test Veo (more expensive, skip in quick test)
    try:
        console.print("Testing Veo 3.1 Fast... ", end="")
        test_video = genai.generate_video(
            model="veo-3.1-fast",
            prompt="Simple test: camera slowly rotating around a red apple, 3 seconds",
            duration=3,
            resolution="720p"
        )
        console.print("[green]✓ Working[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed: {str(e)}[/red]")
        console.print("[yellow]Note: Veo may have rate limits or require approval[/yellow]")

    # Test TTS
    try:
        console.print("Testing Gemini TTS... ", end="")
        client = texttospeech.TextToSpeechClient()
        console.print("[green]✓ Working[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed: {str(e)}[/red]")
        console.print("[yellow]Note: Requires Google Cloud TTS API enabled[/yellow]")

    console.print("\n[green]✅ API access test complete![/green]\n")
    return True


def generate_test_logo():
    """Generate FCP logo as test"""
    console.print("\n[bold cyan]🎨 Generating FCP Logo...[/bold cyan]\n")

    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    output_dir = Path("test_assets")
    output_dir.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating with Imagen 3...", total=1)

        try:
            image = genai.generate_image(
                model="imagen-3",
                prompt="""
                Professional technology logo for 'Food Context Protocol' (FCP).

                Design: Minimalist fusion of a fork icon and data/protocol symbol
                (interconnected nodes). Clean lines, modern sans-serif typography.

                Colors: Gradient from fresh green (#4CAF50) to tech blue (#2196F3).

                Style: Flat design, suitable for tech brand, scalable.
                Background: Transparent or white.
                Format: High contrast, works on light and dark backgrounds.

                Similar to: Stripe, Vercel, GitHub logos - clean, professional, modern tech startup.
                """,
                aspect_ratio="1:1",
                quality="high"
            )

            output_path = output_dir / "fcp_logo_test.png"
            image.save(str(output_path))

            progress.update(task, completed=1)
            console.print(f"\n[green]✓ Logo saved to: {output_path}[/green]")
            console.print("\nOpen the file to view your generated logo!")

            return str(output_path)

        except Exception as e:
            console.print(f"\n[red]✗ Generation failed: {str(e)}[/red]")
            return None


def generate_test_video():
    """Generate short test video"""
    console.print("\n[bold cyan]🎬 Generating Test Video...[/bold cyan]\n")

    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    output_dir = Path("test_assets")
    output_dir.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating with Veo 3.1 Fast...", total=1)

        try:
            video = genai.generate_video(
                model="veo-3.1-fast",
                prompt="""
                Professional title card animation for a tech product.

                Scene: Clean white background with subtle gradient (white to light blue).
                Text: "FCP" appears in center, modern sans-serif font.
                Animation: Text fades in with gentle scale (0.95x to 1.0x).
                Below text: Subtle tagline "Food Context Protocol" fades in after.

                Style: Minimal, professional, tech brand reveal.
                Duration: 5 seconds, smooth animation.
                """,
                duration=5,
                resolution="720p",  # Use 720p for faster test
                audio_enabled=False
            )

            output_path = output_dir / "title_test.mp4"
            video.save(str(output_path))

            progress.update(task, completed=1)
            console.print(f"\n[green]✓ Video saved to: {output_path}[/green]")
            console.print("\nPlay the file to view your generated video!")

            # Show video info
            import ffmpeg
            try:
                probe = ffmpeg.probe(str(output_path))
                duration = float(probe['format']['duration'])
                video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                width = int(video_stream['width'])
                height = int(video_stream['height'])

                console.print(f"\nVideo info:")
                console.print(f"  Duration: {duration:.1f}s")
                console.print(f"  Resolution: {width}×{height}")
                console.print(f"  Size: {Path(output_path).stat().st_size / 1024:.1f} KB")
            except:
                pass

            return str(output_path)

        except Exception as e:
            console.print(f"\n[red]✗ Generation failed: {str(e)}[/red]")

            if "quota" in str(e).lower() or "rate_limit" in str(e).lower():
                console.print("\n[yellow]💡 Tip: You may have hit API rate limits.[/yellow]")
                console.print("Wait a few minutes and try again.")

            return None


def generate_test_audio():
    """Generate test voiceover"""
    console.print("\n[bold cyan]🎙️  Generating Test Voiceover...[/bold cyan]\n")

    output_dir = Path("test_assets")
    output_dir.mkdir(exist_ok=True)

    try:
        client = texttospeech.TextToSpeechClient()

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-M",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )

        text = """
        <speak>
        Welcome to the <emphasis level="strong">Food Context Protocol</emphasis>.
        <break time="500ms"/>
        An open standard for food A-I interoperability.
        </speak>
        """

        synthesis_input = texttospeech.SynthesisInput(ssml=text)

        console.print("Generating with Gemini TTS...")

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        output_path = output_dir / "voiceover_test.mp3"
        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        console.print(f"\n[green]✓ Audio saved to: {output_path}[/green]")
        console.print("\nPlay the file to hear your generated voiceover!")

        return str(output_path)

    except Exception as e:
        console.print(f"\n[red]✗ Generation failed: {str(e)}[/red]")

        if "permission" in str(e).lower() or "denied" in str(e).lower():
            console.print("\n[yellow]💡 Tip: Enable Cloud Text-to-Speech API in Google Cloud Console[/yellow]")
            console.print("Visit: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com")

        return None


def generate_architecture_diagram():
    """Generate FCP architecture diagram"""
    console.print("\n[bold cyan]📊 Generating Architecture Diagram...[/bold cyan]\n")

    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    output_dir = Path("test_assets")
    output_dir.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating with Imagen 3...", total=1)

        try:
            image = genai.generate_image(
                model="imagen-3",
                prompt="""
                Technical architecture diagram for Food Context Protocol (FCP).

                Layout: Three-tier horizontal architecture (left to right flow):

                TOP TIER - Clients (Blue):
                - Mobile app icon (smartphone)
                - Web browser icon
                - CLI terminal icon
                - Claude Desktop icon
                Arranged horizontally with equal spacing

                MIDDLE TIER - FCP Server (Green):
                - Large central box labeled "FCP SERVER"
                - Two arrows from clients:
                  - "MCP stdio" label
                  - "REST HTTP" label
                - Shows: Tool Registry, API Router

                BOTTOM TIER - Gemini 3 (Orange/Red):
                - Six capability icons:
                  - Vision (eye)
                  - Grounding (magnifying glass)
                  - Thinking (brain)
                  - Code Execution (brackets)
                  - Live API (microphone)
                  - Caching (layers)
                - Arrows flowing up to FCP Server

                Style:
                - Clean, professional technical diagram
                - Light gray background (#F5F5F5)
                - Simple line-art icons, consistent weight
                - Clear labels, sans-serif font
                - Arrows with arrowheads
                - Subtle drop shadows

                Format: Wide (16:9), high resolution, suitable for presentation
                """,
                aspect_ratio="16:9",
                quality="high"
            )

            output_path = output_dir / "architecture_diagram_test.png"
            image.save(str(output_path))

            progress.update(task, completed=1)
            console.print(f"\n[green]✓ Diagram saved to: {output_path}[/green]")
            console.print("\nOpen the file to view your generated diagram!")

            return str(output_path)

        except Exception as e:
            console.print(f"\n[red]✗ Generation failed: {str(e)}[/red]")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Test Gemini 3 asset generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_generation.py                  # Test API access only
  python test_generation.py --asset logo     # Generate logo
  python test_generation.py --asset video    # Generate video
  python test_generation.py --asset audio    # Generate audio
  python test_generation.py --asset diagram  # Generate architecture diagram
  python test_generation.py --asset all      # Generate all test assets
        """
    )

    parser.add_argument(
        "--asset",
        choices=["logo", "video", "audio", "diagram", "all"],
        help="Asset type to generate (default: just test API access)"
    )

    args = parser.parse_args()

    console.print("[bold magenta]FCP Asset Generation Test[/bold magenta]")
    console.print("=" * 60)

    # Always test API access first
    if not test_api_access():
        console.print("\n[red]API access test failed. Fix issues before generating assets.[/red]")
        sys.exit(1)

    # Generate requested asset
    if args.asset:
        console.print(f"\n[bold]Generating test asset: {args.asset}[/bold]")

        results = []

        if args.asset == "logo" or args.asset == "all":
            result = generate_test_logo()
            if result:
                results.append(result)
            time.sleep(2)

        if args.asset == "video" or args.asset == "all":
            result = generate_test_video()
            if result:
                results.append(result)
            time.sleep(2)

        if args.asset == "audio" or args.asset == "all":
            result = generate_test_audio()
            if result:
                results.append(result)
            time.sleep(2)

        if args.asset == "diagram" or args.asset == "all":
            result = generate_architecture_diagram()
            if result:
                results.append(result)

        # Summary
        console.print("\n" + "=" * 60)
        if results:
            console.print(f"\n[bold green]✅ Generated {len(results)} test asset(s)![/bold green]\n")
            console.print("Files created:")
            for path in results:
                console.print(f"  • {path}")

            console.print("\n[bold]Next steps:[/bold]")
            console.print("1. Review generated assets in test_assets/")
            console.print("2. If quality looks good, run full generation:")
            console.print("   python generate_video.py --mode hybrid")

        else:
            console.print("\n[red]No assets generated. Check errors above.[/red]")

    else:
        console.print("\n[green]✅ API access test complete![/green]")
        console.print("\n[bold]Next step:[/bold] Generate test assets:")
        console.print("  python test_generation.py --asset logo")
        console.print("  python test_generation.py --asset video")
        console.print("  python test_generation.py --asset all")


if __name__ == "__main__":
    main()
