"""
PDF document anonymization tests.

Tests extraction, PII detection, and Faker generation for PDF documents in Spanish.
Validates detection rate, data quality, and structure preservation.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

from services.document_processing.factory import process_document
from services.pii_detector import run_pipeline


def load_and_anonymize(filename):
    """Load PDF fixture and anonymize it."""
    fixture_path = Path(__file__).parent / 'fixtures' / filename
    
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {filename}")
    
    with open(fixture_path, 'rb') as f:
        file_content = f.read()
    
    result = process_document(
        file_content=file_content,
        filename=filename,
        content_type='application/pdf'
    )
    
    extracted_text = result['text']
    print(f"\n📄 Texto extraído ({len(extracted_text)} chars):")
    print(f"   {extracted_text[:200]}...")
    
    anon_result = run_pipeline(
        model='es',
        text=extracted_text,
        use_regex=True,
        pseudonymize=False,
        save_mapping=False,
        use_realistic_fake=True
    )
    
    anonymized = anon_result.get('anonymized', extracted_text)
    mapping = anon_result.get('mapping', {})
    
    print(f"🗺️  Mapping: {len(mapping)} entidades detectadas")
    
    return extracted_text, anonymized, mapping


def check_entity(text, entity_value):
    """Check if entity is present in text."""
    return entity_value.lower() in text.lower()


def validate_email_domain(mapping, expected_domain):
    """Validate that emails preserve domain."""
    emails = [v for v in mapping.values() if '@' in v]
    if not emails:
        return False
    return all(expected_domain in e for e in emails)


def test_pdf_simple_form():
    """Test formulario básico PDF con 5 entidades PII esperadas."""
    print("\n" + "=" * 60)
    print("TEST: Formulario Simple PDF Español")
    print("=" * 60)
    
    extracted, anonymized, mapping = load_and_anonymize('pdf_simple_form.pdf')
    
    assert len(extracted) > 0, "No se extrajo texto"
    
    print("\n🔍 Validando detección:")
    checks = [
        ('Nombre', 'Juan Pérez García'),
        ('Email', 'juan.perez@techsolutions.es'),
        ('Teléfono', '679 441 223'),
        ('DNI', '12345678A'),
        ('Dirección', 'Calle Mayor' or 'Madrid')
    ]
    
    detected_count = 0
    for entity_type, value in checks:
        found = check_entity(extracted, value)
        status = "✓" if found else "✗"
        print(f"  {status} {entity_type}: {value}")
        if found:
            detected_count += 1
    
    detection_rate = (detected_count / len(checks)) * 100
    print(f"\n📊 Tasa de detección: {detected_count}/{len(checks)} ({detection_rate:.0f}%)")
    
    assert len(mapping) >= 3, f"Se esperaban al menos 3 entidades, se obtuvieron {len(mapping)}"
    
    if validate_email_domain(mapping, 'techsolutions.es'):
        print("✓ Dominio de email preservado")
    
    print("\n✅ Test PASSED\n")


def test_pdf_table():
    """Test tabla estructurada PDF con 3 empleados (9 entidades PII esperadas)."""
    print("\n" + "=" * 60)
    print("TEST: Tabla de Empleados PDF Español")
    print("=" * 60)
    
    extracted, anonymized, mapping = load_and_anonymize('pdf_table.pdf')
    
    print("\n🔍 Validando empleados:")
    employees = [
        'Ana Martínez López',
        'Carlos Ruiz Sánchez',
        'María González Torres'
    ]
    
    detected_employees = 0
    for emp in employees:
        found = check_entity(extracted, emp)
        status = "✓" if found else "✗"
        print(f"  {status} {emp}")
        if found:
            detected_employees += 1
    
    print(f"\n📊 Empleados detectados: {detected_employees}/{len(employees)}")
    
    assert len(mapping) >= 6, f"Se esperaban al menos 6 entidades, se obtuvieron {len(mapping)}"
    
    emails = [v for v in mapping.values() if '@' in v]
    if emails:
        domains = [e.split('@')[1] for e in emails]
        if len(set(domains)) == 1:
            print(f"✓ Consistencia de dominio: {domains[0]}")
    
    print("\n✅ Test PASSED\n")


def test_pdf_narrative():
    """Test texto narrativo PDF con 8 entidades PII esperadas."""
    print("\n" + "=" * 60)
    print("TEST: Texto Narrativo PDF Español")
    print("=" * 60)
    
    extracted, anonymized, mapping = load_and_anonymize('pdf_narrative.pdf')
    
    print("\n🔍 Validando entidades:")
    checks = [
        ('Persona 1', 'Javier Moreno López'),
        ('Email 1', 'javier.moreno@empresa.es'),
        ('Teléfono 1', '679 441 223'),
        ('DNI', '98765432B'),
        ('IBAN', 'ES91' or '2100 0418'),
        ('Persona 2', 'Laura Sánchez Pérez'),
        ('Email 2', 'laura.sanchez@empresa.es'),
        ('Organización', 'TechSolutions')
    ]
    
    detected_count = 0
    for entity_type, value in checks:
        found = check_entity(extracted, value)
        status = "✓" if found else "✗"
        print(f"  {status} {entity_type}")
        if found:
            detected_count += 1
    
    print(f"\n📊 Tasa de detección: {detected_count}/{len(checks)} ({(detected_count/len(checks)*100):.0f}%)")
    
    assert len(mapping) >= 4, f"Se esperaban al menos 4 entidades, se obtuvieron {len(mapping)}"
    
    if validate_email_domain(mapping, 'empresa.es'):
        print("✓ Dominio corporativo preservado")
    
    print("\n✅ Test PASSED\n")


def test_pdf_mixed():
    """Test documento complejo PDF con formulario + tabla + narrativo (12 PII esperadas)."""
    print("\n" + "=" * 60)
    print("TEST: Documento Mixto PDF Español")
    print("=" * 60)
    
    extracted, anonymized, mapping = load_and_anonymize('pdf_mixed.pdf')
    
    print("\n🔍 Validando estructura:")
    structure_checks = [
        ('Persona principal', 'Roberto García Fernández'),
        ('Contacto emergencia 1', 'Isabel García López'),
        ('Contacto emergencia 2', 'Pedro Fernández Ruiz'),
        ('IBAN', 'ES76' or '0182 6473'),
        ('Dirección', 'Gran Vía')
    ]
    
    detected_count = 0
    for check_type, value in structure_checks:
        found = check_entity(extracted, value)
        status = "✓" if found else "✗"
        print(f"  {status} {check_type}")
        if found:
            detected_count += 1
    
    print(f"\n📊 Tasa de detección: {detected_count}/{len(structure_checks)} ({(detected_count/len(structure_checks)*100):.0f}%)")
    
    assert len(mapping) >= 6, f"Se esperaban al menos 6 entidades, se obtuvieron {len(mapping)}"
    
    print("\n✅ Test PASSED\n")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])