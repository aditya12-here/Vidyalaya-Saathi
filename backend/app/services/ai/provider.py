import os
import base64
import json
from pydantic import BaseModel, Field
from typing import List, Optional
import openai

class StudentImpact(BaseModel):
    level: str = Field(..., description="High, Medium, Low, or Unknown")
    areas: List[str] = Field(..., description="e.g., safety, accessibility, learning_environment, hygiene")
    reasoning: str

class TeacherImpact(BaseModel):
    level: str = Field(..., description="High, Medium, Low, or Unknown")
    areas: List[str] = Field(..., description="e.g., ability_to_conduct_classes, teacher_safety, administrative_burden")
    reasoning: str

class IdentifiedProblem(BaseModel):
    problem: str = Field(..., description="A short title for the problem, e.g. 'Damaged classroom desks'")
    category: str
    location: str = Field(..., description="Where in the school this problem is located")
    observation: str
    evidence: List[str] = Field(..., description="Specific visual cues from the image supporting this finding")
    condition: str = Field(..., description="Good, Fair, Poor, Critical, or Unknown")
    confidence: float
    severity_estimate: str = Field(..., description="Critical, High, Medium, Low, Unknown / requires inspection")
    student_impact: StudentImpact
    teacher_impact: TeacherImpact
    requires_inspection: bool = Field(..., description="True if a human professional must verify this physically")
    scale_estimate: Optional[str] = Field(None, description="e.g. 'Approximately 4 damaged desks'")

class ImageQuality(BaseModel):
    status: str = Field(..., description="'sufficient' or 'insufficient'")
    reason: Optional[str] = Field(None, description="Reason if insufficient (e.g. 'Too blurry', 'Too dark', 'Obstructed')")
    analysis_recommended: bool

class ImageAnalysisResult(BaseModel):
    image_quality: ImageQuality
    image_category: str
    problems: List[IdentifiedProblem]
    limitations: List[str] = Field(..., description="What the AI cannot confidently determine from this image")

class VisionAIProvider:
    def __init__(self):
        # We enforce using the NVIDIA API
        base_url = "https://integrate.api.nvidia.com/v1"
        api_key = os.environ.get("API_KEY")
        self.model = "meta/llama-3.2-90b-vision-instruct" 
        
        if not api_key:
             raise ValueError("API_KEY environment variable is not set. Please configure it to use NVIDIA API.")
        
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def analyze_image(self, file_path: str, category: str, description: Optional[str] = None) -> ImageAnalysisResult:
        with open(file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        prompt = f"""
You are the vision analysis module for the Vidyalaya Saathi diagnostic engine.
Your task is to analyze an image of a government school and extract structured evidence about potential infrastructure problems.

Image Category provided by user: {category}
User Description (if any): {description or 'None'}

Goal: Identify ALL reasonably visible potential problems in the image that might affect students or teachers.
Distinguish explicit OBSERVATION from INFERENCE. If a problem cannot be confidently determined, mark requires_inspection as true.
Estimate the condition (Good, Fair, Poor, Critical, Unknown) and scale where possible.

First, assess whether the image is suitable for analysis. If it is too blurry, too dark, obstructed, or invalid, set image_quality.status to "insufficient", analysis_recommended to false, provide the reason, and leave problems empty.

Do NOT invent problems. If the image looks fine, the problems list should be empty.

You MUST respond strictly with a JSON object matching this JSON schema:

{{
  "image_quality": {{
      "status": "string (sufficient or insufficient)",
      "reason": "string or null",
      "analysis_recommended": boolean
  }},
  "image_category": "string",
  "problems": [
    {{
      "problem": "string (short title)",
      "category": "string",
      "location": "string",
      "observation": "string",
      "evidence": ["string"],
      "condition": "string (Good, Fair, Poor, Critical, Unknown)",
      "confidence": float (0.0 to 1.0),
      "severity_estimate": "string",
      "student_impact": {{
        "level": "string",
        "areas": ["string"],
        "reasoning": "string"
      }},
      "teacher_impact": {{
        "level": "string",
        "areas": ["string"],
        "reasoning": "string"
      }},
      "requires_inspection": boolean,
      "scale_estimate": "string or null"
    }}
  ],
  "limitations": ["string"]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": f'{prompt} <img src="data:image/jpeg;base64,{base64_image}" />'
                    }
                ],
                max_tokens=1500,
                # Note: Llama models usually prefer JSON output instructions in prompt rather than strict response_format
                # depending on the provider wrapper, but we rely on prompt instruction for now.
            )
            
            raw_content = response.choices[0].message.content
            
            # Basic cleanup in case markdown ticks are returned
            if raw_content.startswith("```json"):
                raw_content = raw_content.replace("```json\n", "").replace("\n```", "")
            elif raw_content.startswith("```"):
                raw_content = raw_content.replace("```\n", "").replace("\n```", "")
                
            parsed_data = json.loads(raw_content)
            
            return ImageAnalysisResult(**parsed_data)
            
        except Exception as e:
            print(f"Error during AI analysis: {e}")
            raise Exception(f"Failed to analyze image with Vision AI: {str(e)}")

vision_ai = VisionAIProvider()
