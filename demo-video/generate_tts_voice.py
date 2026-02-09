#!/usr/bin/env python3
"""
Generate voiceover narration using Gemini TTS.
Requires GOOGLE_API_KEY environment variable.
"""

import wave
from pathlib import Path
from google import genai
from google.genai import types

client = genai.Client()
output_dir = Path("audio")
output_dir.mkdir(exist_ok=True)


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM audio data to WAV file."""
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def generate_voice(text: str, output_path: str, voice: str = "Kore"):
    """Generate TTS audio using Gemini."""
    print(f"  Generating: {output_path}")

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                )
            ),
        ),
    )

    data = response.candidates[0].content.parts[0].inline_data.data
    wave_file(output_path, data)
    print(f"  ✓ Saved: {output_path}")


# ============ VOICEOVER SCRIPTS ============

SCRIPTS = {
    "intro": {
        "text": (
            "Say in a dramatic, mysterious movie trailer voice with pauses: "
            "What if I told you... your food has secrets? "
            "Hidden data. Nutrition. Allergens. Recipes. "
            "All encoded... in the food matrix."
        ),
        "file": "audio/vo_intro.wav",
    },
    "food_scanner": {
        "text": (
            "Say in a confident, dramatic tone: "
            "Level one. Food Scanner. "
            "See the food for what it really is. "
            "I know this steak doesn't exist... but the AI knows exactly what's in it."
        ),
        "file": "audio/vo_food_scanner.wav",
    },
    "recipe_quest": {
        "text": (
            "Say with dramatic flair, then a comedic beat: "
            "There is no spoon. Use a fork. "
            "Follow the recipe. "
            "The Protocol knows ten thousand dishes."
        ),
        "file": "audio/vo_recipe_quest.wav",
    },
    "meal_log": {
        "text": (
            "Say upbeat and encouraging: "
            "Feed your mind. Feed your phone. "
            "Log everything. Track your journey. "
            "Every meal tells a story."
        ),
        "file": "audio/vo_meal_log.wav",
    },
    "allergen_alert": {
        "text": (
            "Say slowly and dramatically, like Morpheus: "
            "You take the blueberry... the story ends. You wake up and eat safely. "
            "You take the tomato... and I show you how deep the allergen goes."
        ),
        "file": "audio/vo_allergen_alert.wav",
    },
    "mcp_toolbox": {
        "text": (
            "Say with gravitas and weight: "
            "It is The Protocol. "
            "One protocol to connect them all. "
            "Analyze. Search. Track. Protect. "
            "The tools are ready."
        ),
        "file": "audio/vo_mcp_toolbox.wav",
    },
    "gemini_brain": {
        "text": (
            "Say with awe and wonder: "
            "Powered by Gemini. "
            "The AI sees what you cannot. "
            "Nutrition hidden in every pixel. Allergens lurking in every bite. "
            "Now you can see the code too."
        ),
        "file": "audio/vo_gemini_brain.wav",
    },
    "outro": {
        "text": (
            "Say triumphantly and with energy: "
            "Free your food data. "
            "Food Context Protocol. "
            "The food matrix awaits."
        ),
        "file": "audio/vo_outro.wav",
    },
}


if __name__ == "__main__":
    print("\n🎙️  Generating Gemini TTS Voiceover...")
    print(f"   Model: gemini-2.5-flash-preview-tts\n")

    for name, script in SCRIPTS.items():
        try:
            generate_voice(script["text"], script["file"])
        except Exception as e:
            print(f"  ✗ Failed {name}: {e}")

    print("\n✅ Voiceover generation complete!")
    print(f"   Files saved in: {output_dir}/")
