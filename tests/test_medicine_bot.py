from main import MedicineBot

def test_parse_medication_message():
    bot = MedicineBot()
    result = bot._parse_medication_message("лекарство Аспирин 05.24 x3")
    assert result["name"] == "Аспирин"
    assert result["expiry_date"] == "2024-05-31"
    assert result["quantity"] == 3 