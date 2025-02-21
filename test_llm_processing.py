from llm_processing import parse_medication_message

def test_parse_medication_message():
    # Тест корректного формата
    result = parse_medication_message("лекарство Аспирин 05.24 x3")
    assert result["name"] == "Аспирин"
    assert result["quantity"] == 3
    
    # Тест некорректного формата
    result = parse_medication_message("неправильный формат")
    assert result is None 

def test_parse_medication_message_valid():
    result = parse_medication_message("лекарство Аспирин 05.24 x3")
    assert result["name"] == "Аспирин"
    assert result["expiry_date"] == "2024-05-31"
    assert result["quantity"] == 3

def test_parse_medication_message_invalid():
    result = parse_medication_message("неправильный формат")
    assert result is None

def test_parse_medication_message_edge_case():
    result = parse_medication_message("лекарство Анальгин 12.99 x0")
    assert result["quantity"] == 0 