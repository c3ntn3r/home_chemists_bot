from typing import List
from repositories.database_repository import Medication, Course
from constants import MESSAGES

class MessageFormatter:
    @staticmethod
    def format_medications_list(medications: List[Medication]) -> str:
        if not medications:
            return MESSAGES["empty_cabinet"]
        
        meds_formatted = "\n".join(
            f"{med.name} - срок годности: {med.expiry_date}, количество: {med.quantity}" for med in medications
        )
        return f"Ваша аптечка:\n{meds_formatted}"

    @staticmethod
    def format_courses_list(courses: List[Course]) -> str:
        if not courses:
            return "У вас пока нет курсов приема лекарств."
        
        text = "Ваши курсы приема лекарств:\n"
        for course in courses:
            text += f"{course.medicine_name} - дозировка {course.dosage}, расписание: {course.schedule}, метод: {course.method}\n"
        return text 