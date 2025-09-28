#!/usr/bin/env python3
"""
Test script para debuggear la deanonymización
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pii_detector import run_pipeline
from services.deanonymization_service import create_reverse_map, deanonymize_text

def test_deanonymization_flow():
    """Test completo del flujo de anonimización/deanonymización"""
    
    # 1. Texto original
    original_text = "Mi nombre es María García de Barcelona"
    print(f"1. Texto original: {repr(original_text)}")
    
    # 2. Anonimizar usando el pipeline
    result = run_pipeline(
        model='es', 
        text=original_text, 
        use_regex=True, 
        pseudonymize=True, 
        save_mapping=False
    )
    
    anonymized_text = result.get('anonymized', original_text)
    mapping = result.get('mapping', {})
    
    print(f"2. Texto anonimizado: {repr(anonymized_text)}")
    print(f"3. Mapping generado: {mapping}")
    
    # 3. Crear reverse map
    reverse_map = create_reverse_map(mapping)
    print(f"4. Reverse map: {reverse_map}")
    
    # 4. Simular respuesta del LLM que usa los nombres anonimizados
    llm_response = f"Hola {list(mapping.keys())[0]} de {list(mapping.keys())[1] if len(mapping.keys()) > 1 else 'tu ciudad'}, ¿cómo puedo ayudarte?"
    print(f"5. Respuesta LLM (simulada): {repr(llm_response)}")
    
    # 5. Deanonymizar
    deanonymized_response = deanonymize_text(llm_response, reverse_map)
    print(f"6. Respuesta deanonymizada: {repr(deanonymized_response)}")
    
    # 6. Verificar si funcionó
    contains_original_names = any(original_name in deanonymized_response for original_name in mapping.values())
    print(f"7. ¿Contiene nombres originales? {contains_original_names}")
    
    return {
        'original': original_text,
        'anonymized': anonymized_text, 
        'mapping': mapping,
        'reverse_map': reverse_map,
        'llm_response': llm_response,
        'deanonymized': deanonymized_response,
        'success': contains_original_names
    }

if __name__ == "__main__":
    print("=== DEBUG DEANONYMIZATION FLOW ===\n")
    result = test_deanonymization_flow()
    print(f"\n=== RESULTADO: {'✅ SUCCESS' if result['success'] else '❌ FAILED'} ===")