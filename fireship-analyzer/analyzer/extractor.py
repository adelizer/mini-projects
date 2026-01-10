"""Extract content patterns from transcripts using LLM."""

from pydantic import BaseModel
from openai import OpenAI

from .loader import Transcript


class VideoAnalysis(BaseModel):
    """Analysis of a single video's content structure."""
    video_id: str
    title_guess: str
    video_type: str  # tutorial, news, comparison, etc.
    duration: str

    # Hook Analysis
    hook_text: str
    hook_technique: str  # curiosity gap, bold claim, problem statement, etc.
    hook_duration_seconds: float

    # Structure
    intro_technique: str
    main_sections: list[str]
    outro_technique: str

    # Pacing
    words_per_minute: float
    pacing_notes: str

    # Engagement Techniques
    humor_examples: list[str]
    analogies_used: list[str]
    call_to_actions: list[str]

    # Technical Patterns
    code_explanation_style: str
    complexity_management: str  # how they simplify complex topics


class ContentGuidelines(BaseModel):
    """Aggregated guidelines from multiple videos."""

    # Hook Patterns
    hook_patterns: list[str]
    avg_hook_duration: float

    # Structure Patterns
    common_intro_techniques: list[str]
    common_outro_techniques: list[str]
    typical_section_count: int

    # Pacing
    avg_words_per_minute: float
    pacing_guidelines: list[str]

    # Engagement
    humor_techniques: list[str]
    analogy_patterns: list[str]

    # Voice & Tone
    tone_characteristics: list[str]
    vocabulary_notes: list[str]

    # Technical Content
    code_explanation_patterns: list[str]
    simplification_techniques: list[str]

    # General Guidelines
    key_takeaways: list[str]


SINGLE_VIDEO_PROMPT = """Analyze this Fireship YouTube video transcript and extract content creation patterns.

Video Duration: {duration}
Words Per Minute: {wpm:.1f}

TRANSCRIPT:
{text}

Analyze the video and provide structured data about:

1. **Hook Analysis**: What technique is used in the first 10-15 seconds to grab attention?
   - Identify the exact hook text
   - Classify the technique (curiosity gap, bold claim, problem-solution, humor, etc.)
   - Note how long the hook lasts

2. **Video Structure**:
   - How does the intro work after the hook?
   - What are the main sections/topics covered?
   - How does it end?

3. **Pacing Notes**: Is it fast-paced? Are there pauses? How does pacing vary?

4. **Engagement Techniques**:
   - Find examples of humor or wit
   - Find analogies used to explain concepts
   - Identify any calls to action

5. **Technical Content Style**:
   - How is code explained?
   - How are complex topics simplified?

6. **Guess the Title**: Based on the content, what would be a good Fireship-style title?

7. **Video Type**: Is this a tutorial, news update, comparison, "100 seconds" explainer, etc.?

Return your analysis as valid JSON matching this schema:
{{
    "video_id": "{video_id}",
    "title_guess": "string",
    "video_type": "string",
    "duration": "{duration}",
    "hook_text": "first 1-2 sentences of the video",
    "hook_technique": "technique name",
    "hook_duration_seconds": number,
    "intro_technique": "description of intro approach",
    "main_sections": ["section 1", "section 2", ...],
    "outro_technique": "description of outro approach",
    "words_per_minute": {wpm:.1f},
    "pacing_notes": "description of pacing style",
    "humor_examples": ["example 1", "example 2"],
    "analogies_used": ["analogy 1", "analogy 2"],
    "call_to_actions": ["cta 1", "cta 2"],
    "code_explanation_style": "description",
    "complexity_management": "how complex topics are simplified"
}}

Return ONLY the JSON, no markdown formatting."""


AGGREGATE_PROMPT = """You are analyzing multiple Fireship YouTube video analyses to create a comprehensive content creation guideline.

Here are the individual video analyses:

{analyses}

Based on these analyses, create a unified content creation guideline that captures Fireship's style.

Focus on:
1. **Hook Patterns**: What hook techniques work best? What's the ideal hook duration?
2. **Structure**: Common intro/outro patterns, how videos are organized
3. **Pacing**: Target words per minute, pacing guidelines
4. **Engagement**: Humor techniques, analogy patterns that make content memorable
5. **Voice & Tone**: Characteristics of Fireship's voice, vocabulary choices
6. **Technical Content**: How to explain code, simplify complexity
7. **Key Takeaways**: The most important lessons for creating similar content

Return your guidelines as valid JSON matching this schema:
{{
    "hook_patterns": ["pattern 1", "pattern 2", ...],
    "avg_hook_duration": number,
    "common_intro_techniques": ["technique 1", ...],
    "common_outro_techniques": ["technique 1", ...],
    "typical_section_count": number,
    "avg_words_per_minute": number,
    "pacing_guidelines": ["guideline 1", ...],
    "humor_techniques": ["technique 1", ...],
    "analogy_patterns": ["pattern 1", ...],
    "tone_characteristics": ["characteristic 1", ...],
    "vocabulary_notes": ["note 1", ...],
    "code_explanation_patterns": ["pattern 1", ...],
    "simplification_techniques": ["technique 1", ...],
    "key_takeaways": ["takeaway 1", ...]
}}

Return ONLY the JSON, no markdown formatting."""


class ContentExtractor:
    """Extract content patterns using OpenAI."""

    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key)

    def analyze_video(self, transcript: Transcript) -> VideoAnalysis:
        """Analyze a single video transcript."""
        prompt = SINGLE_VIDEO_PROMPT.format(
            duration=transcript.duration_formatted,
            wpm=transcript.words_per_minute,
            text=transcript.text[:15000],  # Limit to avoid token limits
            video_id=transcript.video_id,
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert content analyst specializing in YouTube video structure and engagement patterns."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        # Clean up potential markdown formatting
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        import json
        data = json.loads(content)
        return VideoAnalysis(**data)

    def generate_guidelines(self, analyses: list[VideoAnalysis]) -> ContentGuidelines:
        """Generate aggregated guidelines from multiple video analyses."""
        analyses_text = "\n\n---\n\n".join([
            f"Video: {a.title_guess}\nType: {a.video_type}\nDuration: {a.duration}\n"
            f"Hook: {a.hook_text}\nHook Technique: {a.hook_technique}\n"
            f"Sections: {', '.join(a.main_sections)}\n"
            f"WPM: {a.words_per_minute}\n"
            f"Humor: {', '.join(a.humor_examples[:3])}\n"
            f"Analogies: {', '.join(a.analogies_used[:3])}\n"
            f"Code Style: {a.code_explanation_style}"
            for a in analyses
        ])

        prompt = AGGREGATE_PROMPT.format(analyses=analyses_text)

        response = self.client.chat.completions.create(
            model="gpt-4o",  # Use larger model for synthesis
            messages=[
                {"role": "system", "content": "You are an expert content strategist helping creators develop their YouTube style."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )

        content = response.choices[0].message.content
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        import json
        data = json.loads(content)
        return ContentGuidelines(**data)
