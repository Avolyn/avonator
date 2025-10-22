"""
Avonator Animal Style
A lightweight, standalone service for content safety validation.
"""

import asyncio
import torch
import logging
from typing import Dict, Any, List, Optional, Tuple
from transformers import AutoTokenizer, AutoModelForCausalLM
from pydantic import BaseModel
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"


class ValidationRequest(BaseModel):
    text: str
    context: Optional[str] = None


class ValidationResponse(BaseModel):
    is_safe: bool
    safety_level: SafetyLevel
    confidence: float
    violations: List[str]
    model_info: Dict[str, Any]


class AvonatorAnimalStyleService:
    """Minimal LlamaGuard-7b service for content validation"""
    
    def __init__(self, model_name: str = "meta-llama/LlamaGuard-7b", device: str = "auto"):
        self.model_name = model_name
        self.device = self._get_device(device)
        self.model = None
        self.tokenizer = None
        self._loaded = False
        
        # Model configuration
        self.max_length = 2048
        self.temperature = 0.0
        self.top_p = 1.0
        
    def _get_device(self, device: str) -> str:
        """Determine the best device for inference"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    async def load_model(self):
        """Load LlamaGuard-7b model and tokenizer"""
        if self._loaded:
            return
            
        try:
            logger.info(f"Loading LlamaGuard-7b model on {self.device}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Load model
            model_kwargs = {
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "trust_remote_code": True
            }
            
            if self.device == "cuda":
                model_kwargs["device_map"] = "auto"
                
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
                
            self.model.eval()
            self._loaded = True
            
            logger.info("LlamaGuard-7b model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    async def validate(self, request: ValidationRequest) -> ValidationResponse:
        """Validate content for safety"""
        if not self._loaded:
            await self.load_model()
        
        try:
            # Prepare input
            input_text = self._prepare_input(request.text, request.context)
            
            # Run inference
            safety_result = await self._inference(input_text)
            
            # Parse result
            is_safe, violations, confidence = self._parse_result(safety_result)
            
            return ValidationResponse(
                is_safe=is_safe,
                safety_level=SafetyLevel.SAFE if is_safe else SafetyLevel.UNSAFE,
                confidence=confidence,
                violations=violations,
                model_info={
                    "model": self.model_name,
                    "device": self.device,
                    "input_length": len(input_text)
                }
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return ValidationResponse(
                is_safe=False,
                safety_level=SafetyLevel.UNSAFE,
                confidence=0.0,
                violations=[f"Validation error: {str(e)}"],
                model_info={"error": True}
            )
    
    async def validate_batch(self, requests: List[ValidationRequest]) -> List[ValidationResponse]:
        """Validate multiple texts in batch"""
        results = []
        for request in requests:
            result = await self.validate(request)
            results.append(result)
        return results
    
    def _prepare_input(self, text: str, context: Optional[str] = None) -> str:
        """Prepare input for LlamaGuard-7b"""
        if context:
            return f"Context: {context}\n\nText: {text}"
        return text
    
    async def _inference(self, input_text: str) -> str:
        """Run LlamaGuard-7b inference"""
        # Tokenize
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=True
        ).to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        input_length = len(self.tokenizer.decode(inputs['input_ids'][0], skip_special_tokens=True))
        return response[input_length:].strip()
    
    def _parse_result(self, result: str) -> Tuple[bool, List[str], float]:
        """Parse LlamaGuard-7b output"""
        result = result.lower().strip()
        
        if "safe" in result and "unsafe" not in result:
            return True, [], 0.95
        elif "unsafe" in result:
            violations = self._extract_violations(result)
            return False, violations, 0.9
        else:
            return False, ["Content classification unclear"], 0.5
    
    def _extract_violations(self, result: str) -> List[str]:
        """Extract violation categories"""
        violations = []
        
        categories = {
            "violence": ["violence", "violent", "harm"],
            "hate_speech": ["hate", "discrimination", "racist"],
            "harassment": ["harassment", "bullying"],
            "self_harm": ["self-harm", "suicide"],
            "sexual": ["sexual", "explicit"],
            "illegal": ["illegal", "criminal"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in result for keyword in keywords):
                violations.append(f"Detected {category} content")
        
        if not violations:
            violations.append("Content violates safety guidelines")
            
        return violations
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            if not self._loaded:
                await self.load_model()
            
            # Test with safe content
            test_request = ValidationRequest(text="Hello, how are you?")
            result = await self.validate(test_request)
            return result.is_safe and not result.model_info.get("error", False)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        self._loaded = False
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# Global service instance
_service_instance = None


async def get_service() -> AvonatorAnimalStyleService:
    """Get or create service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = AvonatorAnimalStyle()
    return _service_instance


async def validate_text(text: str, context: Optional[str] = None) -> ValidationResponse:
    """Convenience function for text validation"""
    service = await get_service()
    request = ValidationRequest(text=text, context=context)
    return await service.validate(request)


async def validate_batch(texts: List[str], contexts: Optional[List[str]] = None) -> List[ValidationResponse]:
    """Convenience function for batch validation"""
    service = await get_service()
    
    if contexts is None:
        contexts = [None] * len(texts)
    
    requests = [ValidationRequest(text=text, context=context) 
                for text, context in zip(texts, contexts)]
    
    return await service.validate_batch(requests)



