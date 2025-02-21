from llm_processing import get_llm_intent
from groq_api import call_groq_llm
from database import list_medications

class LLMService:
    def __init__(self, model: str):
        self.model = model
        
    def get_intent(self, text: str) -> str:
        return get_llm_intent(text)
        
    def get_medication_recommendation(self, user_id: int, symptoms: str) -> str:
        medications = list_medications(user_id)  # Получаем только лекарства пользователя
        symptom_prompt = self._build_symptom_prompt(symptoms, medications)
        return call_groq_llm(symptom_prompt) 