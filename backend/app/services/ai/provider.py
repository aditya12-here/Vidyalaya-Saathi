import os
import re
import base64
import json
import io
import httpx
from typing import List, Optional, Any, Dict

from PIL import Image
from pydantic import BaseModel, Field
from openai import AsyncOpenAI


# ============================================================
# CANONICAL INFRASTRUCTURE CATEGORIES
# ============================================================

ALLOWED_CATEGORIES = {
    "classroom": "Classroom",
    "school building": "School Building",
    "toilets": "Toilets",
    "drinking water": "Drinking Water",
    "electricity": "Electricity",
    "furniture": "Furniture",
    "playground": "Playground",
    "boundary/school": "Boundary/School",
}


def normalize_category(value: Optional[str]) -> str:
    """Convert AI category variations into canonical category names."""
    if not value:
        return "Uncertain"

    normalized = " ".join(value.strip().lower().split())
    return ALLOWED_CATEGORIES.get(normalized, "Uncertain")


# ============================================================
# PYDANTIC MODELS
# ============================================================

class StudentImpact(BaseModel):
    level: str = "Medium"
    areas: List[str] = Field(default_factory=list)
    reasoning: str = ""


class TeacherImpact(BaseModel):
    level: str = "Medium"
    areas: List[str] = Field(default_factory=list)
    reasoning: str = ""


class IdentifiedProblem(BaseModel):
    problem: str
    category: str = "General"
    location: str = "Classroom"
    observation: str = ""
    evidence: List[str] = Field(default_factory=list)
    condition: str = "Poor"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    severity_estimate: str = "Medium"
    student_impact: StudentImpact
    teacher_impact: TeacherImpact
    requires_inspection: bool = True
    scale_estimate: Optional[str] = None


class ImageQuality(BaseModel):
    status: str = "sufficient"
    reason: Optional[str] = None
    analysis_recommended: bool = True


class ImageAnalysisResult(BaseModel):
    image_quality: ImageQuality
    image_category: str
    problems: List[IdentifiedProblem] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# ============================================================
# DATA NORMALIZATION HELPERS
# ============================================================

def _normalize_confidence(val: Any) -> float:
    if isinstance(val, (int, float)):
        return max(0.0, min(1.0, float(val)))
    if isinstance(val, str):
        val_lower = val.strip().lower()
        if val_lower == "high":
            return 0.85
        elif val_lower == "medium":
            return 0.60
        elif val_lower == "low":
            return 0.30
        try:
            return max(0.0, min(1.0, float(val)))
        except ValueError:
            pass
    return 0.70


def _normalize_impact(val: Any, default_area: str) -> Dict[str, Any]:
    if isinstance(val, dict):
        areas = val.get("areas", [])
        if isinstance(areas, str):
            areas = [areas]
        elif not isinstance(areas, list):
            areas = []
        return {
            "level": str(val.get("level", "Medium")),
            "areas": areas,
            "reasoning": str(val.get("reasoning", "")),
        }
    if isinstance(val, str):
        return {
            "level": "Medium",
            "areas": [default_area],
            "reasoning": val,
        }
    return {
        "level": "Medium",
        "areas": [default_area],
        "reasoning": "Potential impact identified based on visual evidence.",
    }

def normalize_ai_response(data: dict) -> dict:
    # 1. Normalize quality
    raw_quality = data.get("image_quality", {})
    if isinstance(raw_quality, str):
        raw_quality = {
            "status": "sufficient" if "sufficient" in raw_quality.lower() else "insufficient",
            "reason": None if "sufficient" in raw_quality.lower() else raw_quality,
            "analysis_recommended": "sufficient" in raw_quality.lower(),
        }
    elif not isinstance(raw_quality, dict):
        raw_quality = {"status": "sufficient", "reason": None, "analysis_recommended": True}

    data["image_quality"] = {
        "status": str(raw_quality.get("status", "sufficient")),
        "reason": raw_quality.get("reason"),
        "analysis_recommended": bool(raw_quality.get("analysis_recommended", True)),
    }

    # 2. Normalize category
    data["image_category"] = normalize_category(data.get("image_category"))

    # 3. Normalize problems
    raw_problems = data.get("problems", [])
    if not isinstance(raw_problems, list):
        raw_problems = []

    normalized_problems = []
    for prob in raw_problems:
        if not isinstance(prob, dict):
            continue

        problem_title = prob.get("problem") or prob.get("title") or prob.get("name") or "Identified Issue"
        
        # Convert string confidence ("high"/"medium") to float
        conf = prob.get("confidence", 0.7)
        if isinstance(conf, str):
            c_map = {"high": 0.85, "medium": 0.60, "low": 0.30}
            conf = c_map.get(conf.lower(), 0.70)
        elif not isinstance(conf, (int, float)):
            conf = 0.70

        # Fix student/teacher impact if string instead of object
        def fix_impact(val, area):
            if isinstance(val, dict):
                return val
            return {"level": "Medium", "areas": [area], "reasoning": str(val or "")}

        normalized_prob = {
            "problem": str(problem_title),
            "category": str(prob.get("category") or data["image_category"]),
            "location": str(prob.get("location") or "Classroom"),
            "observation": str(prob.get("observation") or prob.get("description") or ""),
            "evidence": prob.get("evidence", []) if isinstance(prob.get("evidence"), list) else [],
            "condition": str(prob.get("condition") or "Poor"),
            "confidence": float(conf),
            "severity_estimate": str(prob.get("severity_estimate") or prob.get("severity") or "Medium"),
            "student_impact": fix_impact(prob.get("student_impact"), "learning_environment"),
            "teacher_impact": fix_impact(prob.get("teacher_impact"), "ability_to_conduct_classes"),
            "requires_inspection": bool(prob.get("requires_inspection", True)),
            "scale_estimate": prob.get("scale_estimate"),
        }
        normalized_problems.append(normalized_prob)

    data["problems"] = normalized_problems
    return data


# ============================================================
# VISION AI PROVIDER
# ============================================================

class VisionAIProvider:

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()

        # Local Ollama config switch
        self.use_ollama = os.environ.get("USE_OLLAMA", "false").lower() in ("true", "1", "yes")
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "moondream:latest")

        # NVIDIA API Setup
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.api_key = os.environ.get("API_KEY")

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

        self.model = os.environ.get("NVIDIA_MODEL", "minimaxai/minimax-m3")

    def _prepare_image(self, file_path: str, max_dimension: int = 768, quality: int = 65) -> str:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def _analyze_with_ollama(
        self,
        base64_image: str,
        prompt: str,
    ) -> str:
        url = f"{self.ollama_host.rstrip('/')}/api/generate"
        
        # Simplified prompt for small vision models like Moondream
        simple_prompt = (
            "Describe the infrastructure category (Classroom, School Building, Toilets, "
            "Drinking Water, Electricity, Furniture, Playground, or Boundary/School) and any visible "
            "damage/issues in this school photo. Respond in valid JSON with keys: image_category, problems."
        )
        
        payload = {
            "model": self.ollama_model,
            "prompt": simple_prompt,
            "images": [base64_image],
            "stream": False,
            "format": "json",
            "options": {
                "num_gpu": 0,         # Force CPU if GPU VRAM is full
                "num_ctx": 1024       # Reduced context window to save RAM
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("response", "")

    async def analyze_image(self, file_path: str, description: Optional[str] = None) -> ImageAnalysisResult:
        base64_image = self._prepare_image(file_path, max_dimension=768, quality=65)

        prompt = """
You are the Infrastructure Vision AI for Vidyalaya Saathi.

Analyze the uploaded government school image.

Allowed categories:
- Classroom
- School Building
- Toilets
- Drinking Water
- Electricity
- Furniture
- Playground
- Boundary/School

CRITICAL: Return strictly a JSON object matching this schema format:
{
  "image_quality": {
    "status": "sufficient",
    "reason": null,
    "analysis_recommended": true
  },
  "image_category": "School Building",
  "problems": [
    {
      "problem": "Damaged desks",
      "category": "Furniture",
      "location": "Classroom 1",
      "observation": "Broken desktop surface",
      "evidence": ["Wood splintered"],
      "condition": "Poor",
      "confidence": 0.85,
      "severity_estimate": "High",
      "student_impact": {
        "level": "High",
        "areas": ["safety"],
        "reasoning": "Splinters can injure students"
      },
      "teacher_impact": {
        "level": "Low",
        "areas": ["ability_to_conduct_classes"],
        "reasoning": "Disrupts seating"
      },
      "requires_inspection": true,
      "scale_estimate": "3 desks"
    }
  ],
  "limitations": []
}
"""
        if description:
            prompt += f"\nAdditional user description: {description}\n"

        try:
            if self.use_ollama:
                raw_content = await self._analyze_with_ollama(base64_image, prompt)
            else:
                if not self.client:
                    api_key = os.environ.get("API_KEY")
                    if api_key:
                        self.client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
                    else:
                        raise RuntimeError("Vision AI error: API_KEY environment variable is not configured. Please add API_KEY to your .env file or environment.")
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }],
                    max_tokens=3000,  # <-- Increased from 1000 to prevent JSON truncation
                    temperature=0.0,
                )
                if not response.choices:
                    raise RuntimeError("Vision AI returned no choices.")
                raw_content = response.choices[0].message.content

            if not raw_content:
                raise RuntimeError("Vision AI returned an empty response.")

            raw_content = raw_content.strip()

            # 1. Extract content inside markdown fences if present
            import re
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_content)
            if fence_match:
                raw_content = fence_match.group(1).strip()

            # 2. Extract strictly between the first '{' and last '}'
            first_brace = raw_content.find("{")
            last_brace = raw_content.rfind("}")

            if first_brace != -1 and last_brace != -1 and last_brace >= first_brace:
                raw_content = raw_content[first_brace : last_brace + 1].strip()

            # 3. Parse JSON safely with fallback
            try:
                parsed_data = json.loads(raw_content)
            except Exception as parse_error:
                print(f"[VisionAI] JSON parse failed on response: {raw_content[:200]}")
                # Safe fallback default so upload succeeds without breaking
                parsed_data = {
                    "image_quality": {
                        "status": "sufficient",
                        "reason": None,
                        "analysis_recommended": True
                    },
                    "image_category": "School Building",
                    "problems": [],
                    "limitations": ["Model did not produce structured JSON output"]
                }

            # 4. Normalize dictionary values before feeding into Pydantic
            normalized_data = normalize_ai_response(parsed_data)

            return ImageAnalysisResult(**normalized_data)

        except Exception as e:
            print(f"[VisionAI] Analysis failed: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to analyze infrastructure image: {str(e)}") from e


vision_ai = VisionAIProvider()