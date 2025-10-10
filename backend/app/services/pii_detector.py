"""PII detector service (renamed from pipeline.py)

This module is a near-copy of the original `pipeline.py` from SHIELD3 with the
same public function `run_pipeline(model, text, use_regex=False, pseudonymize=False, save_mapping=True)`
so the API router can call it.

MEJORAS IMPLEMENTADAS:
- Detección flexible de teléfonos incompletos o con formatos variables
- Detección de IBANs parciales o con errores tipográficos
- Mejor detección de organizaciones/empresas en contexto
- Validación más tolerante que marca como "sospechoso" en lugar de descartar
- Sistema de confianza por niveles (alta/media/baja)
"""

import argparse
import json
import sys
import os
import re
import hmac
import hashlib
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional improved validators
try:
    from dateutil import parser as date_parser  # type: ignore
    DATEUTIL_AVAILABLE = True
except Exception:
    DATEUTIL_AVAILABLE = False

try:
    import phonenumbers  # type: ignore
    PHONENUMBERS_AVAILABLE = True
except Exception:
    PHONENUMBERS_AVAILABLE = False

# Import synthetic data generator
try:
    from services.synthetic_data_generator import EnhancedSyntheticDataGenerator
    SYNTHETIC_GENERATOR_AVAILABLE = True
except Exception:
    SYNTHETIC_GENERATOR_AVAILABLE = False

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from transformers import pipeline as hf_pipeline
    HF_AVAILABLE = True
except Exception as exc:
    HF_AVAILABLE = False
    HF_IMPORT_ERROR = exc


# Cache para mejorar performance
_MODEL_CACHE = {}

# Lista de empresas/organizaciones conocidas para mejor detección
KNOWN_ORGANIZATIONS = {
    'microsoft', 'google', 'amazon', 'apple', 'facebook', 'meta', 'netflix',
    'ibm', 'oracle', 'salesforce', 'adobe', 'cisco', 'intel', 'nvidia',
    'telefonica', 'movistar', 'vodafone', 'orange', 'bbva', 'santander',
    'caixabank', 'bankia', 'sabadell', 'iberia', 'renfe', 'endesa',
    'repsol', 'inditex', 'zara', 'mercadona', 'carrefour', 'el corte ingles'
}

def hf_get_entities(text: str, hf_model: str):
    """Improved: Añadido cache de modelos y mejor manejo de errores"""
    global _MODEL_CACHE
    
    if hf_model not in _MODEL_CACHE:
        try:
            _MODEL_CACHE[hf_model] = hf_pipeline("ner", model=hf_model, grouped_entities=True)
            logger.info(f"Model {hf_model} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model {hf_model}: {e}")
            raise
    
    ner = _MODEL_CACHE[hf_model]
    
    # Limitar longitud del texto para evitar errores de memoria
    max_length = 5000
    if len(text) > max_length:
        logger.warning(f"Text too long ({len(text)} chars), truncating to {max_length}")
        text = text[:max_length]
    
    return ner(text)


def anonymize_with_hf(text: str, hf_model: str):
    """Improved: Mejor filtrado de entidades de baja confianza"""
    if not HF_AVAILABLE:
        raise RuntimeError(f"transformers is required for HF-only mode: {HF_IMPORT_ERROR}")

    ents = hf_get_entities(text, hf_model)
    mapping: Dict[str, str] = {}
    anonymized = text
    
    # Filtrar entidades de baja confianza ANTES de procesar
    min_confidence = 0.75
    ents_filtered = [e for e in ents if e.get('score', 0) >= min_confidence]
    
    ents_sorted = sorted(ents_filtered, key=lambda e: e.get('start', 0), reverse=True)
    counter = {}
    
    for e in ents_sorted:
        raw_label = e.get('entity_group') or e.get('entity') or 'MISC'
        lab = raw_label.upper()
        
        if lab.startswith('PER') or lab == 'PERSON':
            label = 'PERSON'
        elif lab.startswith('LOC') or lab == 'LOCATION':
            label = 'LOCATION'
        elif lab.startswith('ORG'):
            label = 'ORG'
        else:
            label = 'MISC'

        counter[label] = counter.get(label, 0) + 1
        token = f"[{label}_{counter[label]}]"
        start = e.get('start')
        end = e.get('end')
        
        if start is None or end is None:
            continue
            
        # Validación adicional: no procesar si es muy corto o solo puntuación
        orig = anonymized[start:end]
        if len(orig.strip()) < 2 or orig.strip() in ['+', '-', '_', '.', ',', ';', ':']:
            continue
            
        mapping[token] = orig
        anonymized = anonymized[:start] + token + anonymized[end:]
    
    logger.info(f"HF detected {len(mapping)} entities with confidence >= {min_confidence}")
    return anonymized, mapping


def _regex_patterns() -> Dict[str, str]:
    """
    Patrones regex tolerantes: permiten detectar datos PII con errores menores
    (faltan dígitos, separadores extra, etc.)
    """
    return {
        'CREDIT_CARD': r"\b(?:\d{4}[\s\-]?){2,4}\d{2,4}\b",
        'IBAN': r"(?:^|\s)([A-Z]{2}\d{2}[\s\-]?[A-Z0-9\s\-]{8,30})(?:\s|$|[,;.])",
        'EMAIL': r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        'PHONE': r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{1,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{2,4}[\s\-]?\d{0,4}",
        'DNI': r"(?:^|\s)(\d{8}[A-Z])(?:\s|$|[,;.])",
        'NIE': r"(?:^|\s)([XYZ]\d{7}[A-Z])(?:\s|$|[,;.])",
        'POSTAL_CODE': r"\b\d{3,5}\b",
        'IP': r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    }



def _validate_spanish_dni(dni: str) -> Tuple[bool, str]:
    """Valida DNI español - devuelve (es_valido, nivel_confianza)"""
    letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    dni_clean = dni.upper().strip()
    
    # Eliminar caracteres no alfanuméricos comunes
    dni_clean = re.sub(r'[^\dA-Z]', '', dni_clean)
    
    if not re.match(r'^\d{8}[A-Z]$', dni_clean):
        return False, 'invalid_format'
    
    try:
        num = int(dni_clean[:8])
        letter = dni_clean[8]
        if letters[num % 23] == letter:
            return True, 'high'
        else:
            # Formato correcto pero letra errónea - podría ser error tipográfico
            return False, 'medium'
    except (ValueError, IndexError):
        return False, 'invalid'


def _validate_spanish_nie(nie: str) -> Tuple[bool, str]:
    """Valida NIE español - devuelve (es_valido, nivel_confianza)"""
    letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    nie_clean = nie.upper().strip()
    
    # Eliminar caracteres no alfanuméricos comunes
    nie_clean = re.sub(r'[^\dA-Z]', '', nie_clean)
    
    if not re.match(r'^[XYZ]\d{7}[A-Z]$', nie_clean):
        return False, 'invalid_format'
    
    try:
        # Convertir primera letra a número
        replacements = {'X': '0', 'Y': '1', 'Z': '2'}
        num_str = replacements[nie_clean[0]] + nie_clean[1:8]
        if letters[int(num_str) % 23] == nie_clean[8]:
            return True, 'high'
        else:
            return False, 'medium'
    except (ValueError, IndexError, KeyError):
        return False, 'invalid'


def pseudonymize_value(value: str, key: str) -> str:
    """Improved: Manejo de errores y validación"""
    if not key:
        raise RuntimeError('PSEUDO_KEY is required for pseudonymization')
    
    if not value or not value.strip():
        return ''
    
    try:
        digest = hmac.new(key.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).hexdigest()
        return digest[:12]
    except Exception as e:
        logger.error(f"Error in pseudonymization: {e}")
        # Fallback a hash simple
        return hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]


def apply_regex_masking(text: str, use_pseudo: bool = False, pseudo_key: str = None) -> Tuple[str, Dict[str, str]]:
    """Improved: Mejor ordenamiento y validación de matches"""
    patterns = _regex_patterns()
    mapping: Dict[str, str] = {}
    masked = text
    counters: Dict[str, int] = {}
    
    # Recolectar todos los matches primero
    all_matches = []
    for label, pat in patterns.items():
        for m in re.finditer(pat, text):
            # Para patrones con grupos de captura, usar el grupo 1
            if label in ('DNI', 'NIE', 'IBAN') and m.lastindex and m.lastindex >= 1:
                orig = m.group(1).strip()
                start = m.start(1)
                end = m.end(1)
            else:
                orig = text[m.start():m.end()].strip()
                start = m.start()
                end = m.end()
            
            all_matches.append({
                'label': label,
                'start': start,
                'end': end,
                'orig': orig
            })
    
    # Ordenar por posición (reverse) para reemplazar de atrás hacia adelante
    all_matches.sort(key=lambda x: x['start'], reverse=True)
    
    for match in all_matches:
        label = match['label']
        start = match['start']
        end = match['end']
        orig = match['orig']
        
        # Validaciones específicas MEJORADAS - ahora con niveles de confianza
        confidence = 'high'
        should_include = False
        
        if label == 'DNI':
            is_valid, conf = _validate_spanish_dni(orig)
            if is_valid or conf == 'medium':
                should_include = True
                confidence = conf
        elif label == 'NIE':
            is_valid, conf = _validate_spanish_nie(orig)
            if is_valid or conf == 'medium':
                should_include = True
                confidence = conf
        elif label == 'EMAIL':
            if _is_valid_email(orig):
                should_include = True
                confidence = 'high'
        elif label == 'PHONE':
            is_valid, conf = _is_valid_phone(orig)
            if is_valid:
                should_include = True
                confidence = conf
        elif label == 'IBAN':
            is_valid, conf = _is_valid_iban(orig)
            if is_valid:
                should_include = True
                confidence = conf
        elif label == 'CARD':
            is_valid, conf = _luhn_check(orig)
            if is_valid:
                should_include = True
                confidence = conf
        elif label == 'IP':
            if _is_valid_ip(orig):
                should_include = True
                confidence = 'high'
        else:
            # Otros tipos
            should_include = True
            confidence = 'medium'
        
        if not should_include:
            continue
        
        counters[label] = counters.get(label, 0) + 1
        
        if use_pseudo:
            if '@' in orig:
                prefix = re.sub(r"\W+", '_', orig.split('@', 1)[0])[:20]
            else:
                prefix = label.lower()
            digest = pseudonymize_value(orig, pseudo_key) if pseudo_key else hashlib.sha256(orig.encode()).hexdigest()[:12]
            token = f"{prefix}_{digest[:8]}"
        else:
            token = f"[{label}_{counters[label]}]"
        
        # Añadir metadata de confianza al mapping
        mapping[token] = orig
        
        masked = masked[:start] + token + masked[end:]
    
    logger.info(f"Regex detected {len(mapping)} valid entities")
    return masked, mapping


def _is_valid_email(val: str) -> bool:
    """Improved: Validación más estricta"""
    if not val or len(val) < 5:
        return False
    
    # Formato básico
    if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", val):
        return False
    
    # No permitir múltiples @ o dominios inválidos
    if val.count('@') != 1:
        return False
    
    local, domain = val.split('@')
    
    # Validaciones adicionales
    if len(local) > 64 or len(domain) > 255:
        return False
    
    if domain.startswith('.') or domain.endswith('.') or '..' in domain:
        return False
    
    return True


def _is_valid_ip(val: str) -> bool:
    """Valida direcciones IPv4"""
    parts = val.split('.')
    if len(parts) != 4:
        return False
    
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False


def _is_valid_phone(val: str) -> Tuple[bool, str]:
    """MEJORADO: Detección flexible de teléfonos - devuelve (es_valido, nivel_confianza)"""
    # Detectar patrones de fecha comunes (descartar)
    if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", val) or re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", val):
        return False, 'date_pattern'
    
    # Detectar patrones de hora (descartar)
    if re.match(r"^\d{2}:\d{2}:\d{2}$", val):
        return False, 'time_pattern'
    
    # Extraer solo dígitos
    digits = re.sub(r"\D", '', val)
    
    # Teléfonos incompletos pero probables (7-8 dígitos sin prefijo)
    if len(digits) >= 7 and len(digits) <= 8:
        # Verificar que comience con 6, 7, 8 o 9 (móviles españoles)
        if digits[0] in '6789':
            return True, 'medium'  # Confianza media porque podría estar incompleto
    
    # Teléfonos completos españoles (9 dígitos)
    if len(digits) == 9:
        if digits[0] in '6789':
            return True, 'high'
        else:
            return True, 'medium'  # Podría ser fijo
    
    # Teléfonos con prefijo internacional
    if len(digits) >= 10 and len(digits) <= 15:
        if PHONENUMBERS_AVAILABLE:
            try:
                # Intentar con España primero
                num = phonenumbers.parse(val, "ES")
                if phonenumbers.is_valid_number(num):
                    return True, 'high'
                
                # Intentar sin región
                num = phonenumbers.parse(val, None)
                if phonenumbers.is_valid_number(num):
                    return True, 'high'
            except Exception:
                pass
        
        # Sin librería, aceptar con confianza media si tiene longitud razonable
        return True, 'medium'
    
    # Demasiado corto
    if len(digits) < 7:
        return False, 'too_short'
    
    # Demasiado largo
    if len(digits) > 15:
        return False, 'too_long'
    
    # Si todos los dígitos son iguales, probablemente no es un teléfono real
    if len(set(digits)) == 1:
        return False, 'uniform_digits'
    
    return False, 'unknown'


def _luhn_check(number: str) -> Tuple[bool, str]:
    """Valida números de tarjeta, permitiendo 10–19 dígitos y devolviendo niveles de confianza."""
    s = re.sub(r"\D", '', number)

    if not s:
        return False, 'invalid_format'

    if len(s) < 10:
        return False, 'too_short'
    if len(s) > 19:
        return False, 'too_long'

    total = 0
    reverse = s[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d

    # Si pasa Luhn → alta confianza
    if total % 10 == 0:
        return True, 'high'

    # Si no pasa pero es plausible → media confianza
    if 10 <= len(s) <= 19:
        return True, 'medium'

    return False, 'failed_luhn'



def _is_valid_iban(val: str) -> Tuple[bool, str]:
    """Valida IBANs de forma flexible. No descarta los incompletos; los marca como medium."""
    s = re.sub(r'[\s\-]', '', val).upper()

    if len(s) < 8:
        return False, 'too_short'
    if len(s) > 34:
        return False, 'too_long'

    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", s):
        return False, 'invalid_format'

    country_lengths = {
        'ES': 24, 'FR': 27, 'DE': 22, 'IT': 27, 'GB': 22,
        'PT': 25, 'NL': 18, 'BE': 16, 'CH': 21, 'AT': 20
    }

    country = s[:2]
    expected_length = country_lengths.get(country)

    if expected_length:
        if len(s) < expected_length:
            # IBAN incompleto pero plausible
            return True, 'medium'

        if abs(len(s) - expected_length) <= 2:
            # Validación por módulo 97 — tolerante a 1-2 dígitos de diferencia
            rearr = s[4:] + s[:4]
            converted = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rearr)
            try:
                remainder = 0
                for i in range(0, len(converted), 9):
                    chunk = str(remainder) + converted[i:i+9]
                    remainder = int(chunk) % 97
                if remainder == 1:
                    return True, 'high'
                else:
                    return True, 'medium'
            except Exception:
                return True, 'medium'

    # País desconocido o formato no estándar pero plausible
    if len(s) >= 10:
        return True, 'medium'

    return False, 'unknown'



def validate_mapping(mapping: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Improved: Validación más exhaustiva y logging"""
    valid = {}
    suspects = {}
    stats = {'total': len(mapping), 'valid': 0, 'suspect': 0}
    
    for tok, orig in mapping.items():
        lower = tok.lower()
        is_valid = False
        reason = ''
        
        try:
            # Detectar fechas primero (falsos positivos comunes)
            is_date = False
            if DATEUTIL_AVAILABLE:
                try:
                    d = date_parser.parse(orig, fuzzy=False)
                    if 1900 <= d.year <= 2025:
                        is_date = True
                        reason = 'detected_as_date'
                except Exception:
                    pass
            else:
                if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", orig) or re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", orig):
                    is_date = True
                    reason = 'date_pattern'

            # Validar por tipo
            if 'phone' in lower or 'tel' in lower:
                if is_date:
                    suspects[tok] = orig
                    reason = 'phone_but_is_date'
                else:
                    val, conf = _is_valid_phone(orig)
                    if val:
                        valid[tok] = orig
                        is_valid = True
                    else:
                        suspects[tok] = orig
                        reason = f'invalid_phone_{conf}'
                    
            elif 'card' in lower:
                val, conf = _luhn_check(orig)
                if val:
                    valid[tok] = orig
                    is_valid = True
                else:
                    suspects[tok] = orig
                    reason = f'invalid_card_{conf}'
                    
            elif 'iban' in lower:
                val, conf = _is_valid_iban(orig)
                if val:
                    valid[tok] = orig
                    is_valid = True
                else:
                    suspects[tok] = orig
                    reason = f'invalid_iban_{conf}'
                    
            elif 'dni' in lower:
                val, conf = _validate_spanish_dni(orig)
                if val:
                    valid[tok] = orig
                    is_valid = True
                else:
                    suspects[tok] = orig
                    reason = f'invalid_dni_{conf}'
                    
            elif 'nie' in lower:
                val, conf = _validate_spanish_nie(orig)
                if val:
                    valid[tok] = orig
                    is_valid = True
                else:
                    suspects[tok] = orig
                    reason = f'invalid_nie_{conf}'
                    
            elif '@' in orig:
                if _is_valid_email(orig):
                    valid[tok] = orig
                    is_valid = True
                else:
                    suspects[tok] = orig
                    reason = 'invalid_email_format'
            else:
                # Otros tipos sin validación específica
                valid[tok] = orig
                is_valid = True
                
        except Exception as e:
            logger.warning(f"Error validating {tok}: {e}")
            suspects[tok] = orig
            reason = f'validation_error: {str(e)}'
        
        if is_valid:
            stats['valid'] += 1
        else:
            stats['suspect'] += 1
            logger.debug(f"Suspect PII: {tok} -> '{orig}' (reason: {reason})")
    
    logger.info(f"Validation complete: {stats['valid']} valid, {stats['suspect']} suspect out of {stats['total']} total")
    return valid, suspects


def _parse_key_values(text: str) -> Dict[str, str]:
    """Improved: Mejor parsing de key-value pairs"""
    res: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # Soportar múltiples separadores
        separators = [':', '=', '->']
        for sep in separators:
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val:
                        res[key] = val
                break
    return res


def print_report(anonymized: str, mapping: Dict[str, str], original_text: str):
    """Improved: Reporte más informativo y estructurado"""
    print('\n' + '='*60)
    print('INFORME DE ANONIMIZACIÓN')
    print('='*60)
    
    if not mapping:
        print('  ⚠ No se detectaron entidades PII en el texto.')
        return
    
    kv = _parse_key_values(original_text)
    
    # Agrupar por tipo
    by_type = {}
    for token, original in mapping.items():
        if token.startswith('[') and ']' in token:
            typ = token.strip('[]').split('_')[0]
        else:
            if '_' in token:
                typ = token.split('_', 1)[0].upper()
            else:
                typ = 'MISC'
        
        if typ not in by_type:
            by_type[typ] = []
        by_type[typ].append((token, original))
    
    print(f'\n  ✓ Total de entidades detectadas: {len(mapping)}')
    print(f'  ✓ Tipos de PII encontrados: {", ".join(by_type.keys())}')
    print('\n  Detalle por tipo:')
    print('  ' + '-'*56)
    
    for typ, items in sorted(by_type.items()):
        print(f'\n  [{typ}] - {len(items)} elemento(s):')
        for token, original in items:
            # Buscar contexto
            matched_field = None
            for k, v in kv.items():
                if v == original or original in v or v in original:
                    matched_field = k
                    break
            
            # Ocultar parcialmente el valor original por seguridad
            if len(original) > 6:
                masked_orig = original[:2] + '*' * (len(original) - 4) + original[-2:]
            else:
                masked_orig = '*' * len(original)
            
            if matched_field:
                print(f"    • Campo: {matched_field}")
                print(f"      Reemplazado por: {token}")
                print(f"      Valor: {masked_orig}")
            else:
                print(f"    • Reemplazado por: {token} (valor: {masked_orig})")
    
    print('\n  Texto anonimizado (extracto):')
    print('  ' + '-'*56)
    excerpt_length = 500
    if len(anonymized) <= excerpt_length:
        excerpt = anonymized
    else:
        excerpt = anonymized[:excerpt_length] + '...\n  [texto truncado]'
    
    # Indentar el extracto
    for line in excerpt.split('\n'):
        print(f"  {line}")
    
    print('\n' + '='*60)


def preprocess_titlecase_name(text: str) -> str:
    """Improved: Manejo de más patrones de nombres"""
    import re

    def _titlecase_match(m: re.Match) -> str:
        prefix = m.group(1)
        name = m.group(2).strip()
        # Preservar conectores en minúscula
        words = name.split()
        result = []
        for w in words:
            if w.lower() in ['de', 'del', 'la', 'los', 'las', 'y', 'e']:
                result.append(w.lower())
            else:
                result.append(w.title())
        return f"{prefix}{' '.join(result)}"

    patterns = [
        r"(?i)(Nombre y apellidos:\s*)(.+)",
        r"(?i)(Nombre completo:\s*)(.+)",
        r"(?i)(Name:\s*)(.+)",
        r"(?i)(Full name:\s*)(.+)",
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, _titlecase_match, text)
    
    return text


def anonymize_with_local(text: str):
    """Mantener compatibilidad pero deshabilitado"""
    raise RuntimeError("Local anonymizer is disabled in HF-only mode")


def anonymize_combined(text: str, hf_model: str):
    """Mantener compatibilidad - no usado en el flujo principal"""
    ents = hf_get_entities(text, hf_model)
    hf_mapping: Dict[str, str] = {}
    text_with_hf = text
    ents_sorted = sorted(ents, key=lambda e: e.get('start', 0), reverse=True)
    counter = {}
    for e in ents_sorted:
        label = e.get('entity_group') or e.get('entity') or 'MISC'
        counter[label] = counter.get(label, 0) + 1
        token = f"[{label.upper()}_{counter[label]}]"
        start = e.get('start')
        end = e.get('end')
        if start is None or end is None:
            continue
        orig = text_with_hf[start:end]
        hf_mapping[token] = orig
        text_with_hf = text_with_hf[:start] + token + text_with_hf[end:]

    local_anonymized, local_map = anonymize_with_local(text_with_hf)

    merged = {}
    merged.update(hf_mapping)
    for k, v in local_map.items():
        if k in merged:
            newk = k + "_L"
            merged[newk] = v
        else:
            merged[k] = v

    return local_anonymized, merged


def _normalize_hf_label(raw: str) -> str:
    """Improved: Normalización más completa de labels"""
    lab = (raw or '').upper().strip()
    
    # Mapeo de labels comunes
    person_labels = ['PER', 'PERSON', 'PERS', 'PERSONA']
    location_labels = ['LOC', 'LOCATION', 'LUGAR', 'GPE']
    org_labels = ['ORG', 'ORGANIZATION', 'ORGANIZACION', 'COMPANY']
    
    for plabel in person_labels:
        if lab.startswith(plabel):
            return 'PERSON'
    
    for llabel in location_labels:
        if lab.startswith(llabel):
            return 'LOCATION'
    
    for olabel in org_labels:
        if lab.startswith(olabel):
            return 'ORG'
    
    return 'MISC'


def _detect_organization_context(text: str, start: int, end: int) -> bool:
    """NUEVO: Detecta si una entidad aparece en contexto de organización/empresa"""
    # Extraer contexto ampliado (50 caracteres antes y después)
    context_start = max(0, start - 50)
    context_end = min(len(text), end + 50)
    context = text[context_start:context_end].lower()
    
    # Palabras clave que indican contexto laboral
    work_keywords = [
        'trabajo en', 'trabaja en', 'trabajar en', 'empleado en', 
        'empresa', 'compañía', 'corporación', 'organización',
        'mi trabajo', 'la empresa', 'oficina', 'departamento'
    ]
    
    for keyword in work_keywords:
        if keyword in context:
            return True
    
    # Verificar si la entidad está en la lista de organizaciones conocidas
    entity_text = text[start:end].lower().strip()
    if entity_text in KNOWN_ORGANIZATIONS:
        return True
    
    return False


def collect_hf_matches(text: str, hf_model: str):
    """MEJORADO: Filtrado mejorado + detección de contexto organizacional"""
    if not HF_AVAILABLE:
        return []
    
    try:
        ents = hf_get_entities(text, hf_model)
    except Exception as e:
        logger.error(f"Error getting HF entities: {e}")
        return []
    
    matches = []
    min_score = float(os.environ.get('HF_MIN_CONFIDENCE', '0.70'))  # Bajado de 0.80 a 0.70
    
    for e in ents:
        start = e.get('start')
        end = e.get('end')
        if start is None or end is None:
            continue
        
        orig_text = text[start:end].strip()
        
        # Filtros de calidad básicos
        if len(orig_text) < 2:
            continue
        
        # Ignorar puntuación aislada
        if orig_text in ['+', '-', '_', '.', ',', ';', ':', '!', '?', '(', ')', '[', ']']:
            continue
        
        # Ignorar números simples sin contexto (pero permitir si es parte de DNI/NIE/etc)
        if orig_text.isdigit() and len(orig_text) < 4:
            continue
        
        # Obtener score
        score = e.get('score', 0)
        
        # Normalizar label
        raw_label = e.get('entity_group') or e.get('entity')
        label = _normalize_hf_label(raw_label)
        
        # NUEVO: Detectar organizaciones en contexto
        if label == 'ORG' or _detect_organization_context(text, start, end):
            # Para organizaciones, ser más permisivo con el score
            if score >= max(0.60, min_score - 0.10):
                matches.append({
                    'start': start,
                    'end': end,
                    'label': 'ORG',
                    'orig': orig_text,
                    'source': 'hf',
                    'score': score
                })
                continue
        
        # Filtrar por score de confianza estándar
        if score < min_score:
            continue
        
        # Ignorar contexto de email ampliado
        context_start = max(0, start - 30)
        context_end = min(len(text), end + 30)
        context = text[context_start:context_end]
        
        # Detectar si está dentro de un email
        if '@' in context:
            email_parts = context.split('@')
            for part in email_parts:
                if '.' in part and orig_text in part:
                    continue  # Skip si está en dominio de email
        
        # Ignorar palabras comunes que no son PII
        common_words = {'email', 'phone', 'nombre', 'name', 'address', 'ciudad', 'city', 
                       'país', 'country', 'fecha', 'date', 'empresa', 'company'}
        if orig_text.lower() in common_words:
            continue
        
        matches.append({
            'start': start,
            'end': end,
            'label': label,
            'orig': orig_text,
            'source': 'hf',
            'score': score
        })
    
    logger.info(f"HF collected {len(matches)} matches (min_score={min_score})")
    return matches


def collect_regex_matches(text: str):
    """MEJORADO: Mejor calidad de matches regex con validación flexible"""
    patterns = _regex_patterns()
    matches = []
    
    for label, pat in patterns.items():
        for m in re.finditer(pat, text):
            # Para patrones con grupos de captura (DNI, NIE, IBAN), usar el grupo 1
            if label in ('DNI', 'NIE', 'IBAN') and m.lastindex and m.lastindex >= 1:
                orig = m.group(1).strip()
                # Limpiar espacios/guiones del IBAN capturado
                if label == 'IBAN':
                    orig = re.sub(r'[\s\-]', '', orig)
                start = m.start(1)
                end = m.end(1)
            else:
                orig = text[m.start():m.end()].strip()
                start = m.start()
                end = m.end()
            
            # Filtros básicos
            if len(orig) < 2:
                continue
            
            if orig in ['+', '-', '_', '.', ',', ';', ':', '!', '?', '@']:
                continue
            
            # Validaciones específicas por tipo CON FLEXIBILIDAD
            skip = False
            confidence = 'high'
            
            if label == 'EMAIL':
                if '@' not in orig or '.' not in orig.split('@')[-1]:
                    skip = True
            
            elif label == 'PHONE':
                is_valid, conf = _is_valid_phone(orig)
                if not is_valid:
                    skip = True
                else:
                    confidence = conf
            
            elif label == 'CARD':
                is_valid, conf = _luhn_check(orig)
                if not is_valid:
                    skip = True
                else:
                    confidence = conf
            
            elif label == 'DNI':
                is_valid, conf = _validate_spanish_dni(orig)
                if not is_valid and conf not in ('medium',):
                    skip = True
                else:
                    confidence = conf if is_valid else 'medium'
            
            elif label == 'NIE':
                is_valid, conf = _validate_spanish_nie(orig)
                if not is_valid and conf not in ('medium',):
                    skip = True
                else:
                    confidence = conf if is_valid else 'medium'
            
            elif label == 'IBAN':
                is_valid, conf = _is_valid_iban(orig)
                if not is_valid:
                    skip = True
                else:
                    confidence = conf
            
            elif label == 'POSTAL_CODE':
                digits = re.sub(r'\D', '', orig)
                if 3 <= len(digits) <= 5:
                    confidence = 'high' if len(digits) == 5 else 'medium'
                else:
                    skip = True

            elif label == 'IP':
                # Validar formato IPv4
                if not _is_valid_ip(orig):
                    skip = True
            
            if skip:
                continue
            
            matches.append({
                'start': start,
                'end': end,
                'label': label,
                'orig': orig,
                'source': 'regex',
                'confidence': confidence
            })
    
    logger.info(f"Regex collected {len(matches)} matches")
    return matches


def resolve_matches(hf_matches, regex_matches):
    """MEJORADO: Mejor resolución con prioridad a regex estructurado"""
    REGEX_ALWAYS = {'EMAIL', 'PHONE', 'CARD', 'IBAN', 'IP', 'BIOMETRIC', 'CREDENTIALS', 'COMBO', 'DNI', 'NIE', 'POSTAL_CODE'}
    SYNERGY = {'ID', 'DOB'}

    # Pre-filtrado de matches de baja calidad
    filtered_hf = []
    for h in hf_matches:
        orig = h.get('orig', '').strip()
        if len(orig) < 2:
            continue
        if orig in ['+', '-', '_', '.', ',', ';', ':', '!', '?']:
            continue
        if len(orig) == 1:
            continue
        filtered_hf.append(h)
    
    filtered_regex = []
    for r in regex_matches:
        orig = r.get('orig', '').strip()
        if len(orig) < 2:
            continue
        if orig in ['+', '-', '_', '.', ',', ';', ':', '!', '?']:
            continue
        filtered_regex.append(r)

    # Crear índice espacial de intervalos HF para búsqueda rápida
    hf_intervals = []
    for h in filtered_hf:
        hf_intervals.append((h['start'], h['end'], h))

    def overlaps_with_hf(r):
        """Encuentra overlap con match HF"""
        for s, e, h in hf_intervals:
            if not (r['end'] <= s or r['start'] >= e):
                return h
        return None
    
    def overlap_percentage(a, b):
        """Calcula porcentaje de overlap entre dos matches"""
        overlap_start = max(a['start'], b['start'])
        overlap_end = min(a['end'], b['end'])
        
        if overlap_start >= overlap_end:
            return 0.0
        
        overlap_len = overlap_end - overlap_start
        a_len = a['end'] - a['start']
        b_len = b['end'] - b['start']
        
        return overlap_len / min(a_len, b_len)

    chosen = []
    removed_hf = set()
    
    # PRIMERO: Añadir matches regex prioritarios
    for r in filtered_regex:
        rlab = r['label'].upper()
        r['label'] = rlab
        
        # Siempre preferir regex para tipos estructurados
        if rlab in REGEX_ALWAYS:
            h = overlaps_with_hf(r)
            if h is not None:
                overlap_pct = overlap_percentage(r, h)
                # Si el overlap es > 50%, reemplazar el HF con el regex
                if overlap_pct > 0.5:
                    removed_hf.add(id(h))
            chosen.append(r)
    
    # SEGUNDO: Añadir matches HF que no fueron removidos
    for h in filtered_hf:
        if id(h) not in removed_hf:
            chosen.append(h)

    # Deduplicar matches que se solapan entre sí
    final_matches = []
    chosen_sorted = sorted(chosen, key=lambda x: (x['end'] - x['start']), reverse=True)
    
    def overlaps(a, b):
        """Verifica si dos ranges se solapan"""
        return not (a['end'] <= b['start'] or a['start'] >= b['end'])

    for match in chosen_sorted:
        # Verificar si ya hay un match que solapa significativamente
        has_overlap = False
        for existing in final_matches:
            if overlaps(match, existing):
                overlap_pct = overlap_percentage(match, existing)
                if overlap_pct > 0.7:
                    # Decidir cuál mantener basado en prioridad
                    match_priority = 100 if match.get('source') == 'regex' and match['label'] in REGEX_ALWAYS else 50
                    existing_priority = 100 if existing.get('source') == 'regex' and existing['label'] in REGEX_ALWAYS else 50
                    
                    if match_priority > existing_priority:
                        final_matches.remove(existing)
                        has_overlap = False
                    else:
                        has_overlap = True
                    break
        
        if not has_overlap:
            final_matches.append(match)
    
    # Ordenar por posición (reverse) para reemplazos
    final_sorted = sorted(final_matches, key=lambda x: x['start'], reverse=True)
    
    hf_count = len([m for m in final_sorted if m.get('source') == 'hf'])
    regex_count = len([m for m in final_sorted if m.get('source') == 'regex'])
    
    logger.info(f"Resolved matches: {hf_count} HF + {regex_count} regex = {len(final_sorted)} total")
    return final_sorted


def apply_replacements_from_matches(original_text: str, matches: List[Dict], use_pseudo: bool = False, pseudo_key: str = None, use_realistic_fake: bool = False):
    """MEJORADO: Mejor generación de tokens y manejo de colisiones"""
    anonymized = original_text
    mapping: Dict[str, str] = {}
    counters = {}
    
    # Inicializar generador si está disponible
    if use_realistic_fake and SYNTHETIC_GENERATOR_AVAILABLE:
        try:
            generator = EnhancedSyntheticDataGenerator()
            logger.info("Using realistic fake data generator")
        except Exception as e:
            logger.warning(f"Failed to init synthetic generator: {e}, falling back")
            generator = None
    else:
        generator = None
    
    replaced_count = 0
    skipped_count = 0
    
    for m in matches:
        start, end = m['start'], m['end']
        label = m['label']
        src = m.get('source', 'regex')
        orig = original_text[start:end].strip()
        
        # Filtros finales de calidad MÁS PERMISIVOS
        if len(orig) < 2:
            skipped_count += 1
            continue
        
        if orig in ['+', '-', '_', '.', ',', ';', ':', '!', '?', '(', ')', '[', ']', '{', '}']:
            skipped_count += 1
            continue
        
        # Para matches HF, permitir textos más cortos si son ORG
        if src == 'hf' and len(orig) < 3 and label != 'ORG':
            skipped_count += 1
            continue
        
        # Detectar si parece una fecha (falso positivo común para teléfonos)
        is_date_like = False
        if DATEUTIL_AVAILABLE:
            try:
                d = date_parser.parse(orig, fuzzy=False)
                if 1900 <= d.year <= 2025:
                    is_date_like = True
            except Exception:
                pass
        else:
            if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", orig) or re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", orig):
                is_date_like = True

        # Reclasificar si es necesario
        if label.upper() in ('PHONE', 'PHONE_R', 'PHONE_HF') and is_date_like:
            label = 'DOB'
            logger.debug(f"Reclassified {orig} from PHONE to DOB")
        
        # Determinar namespace para contadores
        keylabel = label
        if src == 'hf':
            ns = 'HF'
        else:
            ns = 'R'
        
        counter_key = keylabel + ns
        counters[counter_key] = counters.get(counter_key, 0) + 1
        
        # Generar token de reemplazo
        if use_realistic_fake and generator:
            try:
                fake_value = generator.generate_synthetic_replacement(keylabel, orig)

                # 🔒 Protección: no permitir que el generador modifique palabras de contexto
                # (por ejemplo, que reemplace "IBAN", "DNI", "teléfono" o similares)
                # Pero mantenemos cualquier valor, aunque sea parcial o con errores.
                context_keywords = {"iban", "dni", "nie", "teléfono", "telefono", "email", "correo", "nombre"}
                if any(kw in fake_value.lower() for kw in context_keywords):
                    logger.debug(f"Context word found in fake output for {keylabel}, keeping only value part")
                    # Intentar quedarse con el fragmento más "dato" (por ejemplo, el número)
                    possible_values = re.findall(r"[A-Z0-9+@._-]+", fake_value)
                    if possible_values:
                        fake_value = max(possible_values, key=len)

                token = fake_value.strip()
                logger.debug(f"Generated realistic fake for {keylabel}: {token}")

            except Exception as e:
                logger.warning(f"Synthetic generation failed for {keylabel}: {e}, using placeholder")
                token = f"[{keylabel}_{counters[counter_key]}]"


        
        elif use_pseudo and src == 'regex':
            # Pseudonimización determinística
            try:
                digest = pseudonymize_value(orig, pseudo_key) if pseudo_key else hashlib.sha256(orig.encode()).hexdigest()[:12]
                
                if '@' in orig:
                    # Para emails, preservar estructura
                    local_part = orig.split('@', 1)[0]
                    prefix = re.sub(r"\W+", '_', local_part)[:20]
                else:
                    prefix = keylabel.lower()
                
                token = f"{prefix}_{digest[:8]}"
            except Exception as e:
                logger.error(f"Pseudonymization failed: {e}, using placeholder")
                token = f"[{keylabel}_{counters[counter_key]}]"
        else:
            # Token placeholder estándar
            token = f"[{keylabel}_{counters[counter_key]}]"
        
        # Evitar colisiones en el mapping
        original_token = token
        collision_counter = 1
        while token in mapping and mapping[token] != orig:
            token = f"{original_token}_dup{collision_counter}"
            collision_counter += 1
            if collision_counter > 10:
                logger.error(f"Too many collisions for token {original_token}")
                break
        
        mapping[token] = orig
        anonymized = anonymized[:start] + token + anonymized[end:]
        replaced_count += 1
    
    logger.info(f"Applied {replaced_count} replacements, skipped {skipped_count} low-quality matches")
    return anonymized, mapping


def run_pipeline(model: str, text: str, use_regex: bool = False, pseudonymize: bool = False, save_mapping: bool = True, use_realistic_fake: bool = False):
    """MEJORADO: Mejor orquestación con detección más flexible
    
    Mantiene la misma firma pública para compatibilidad con API.
    """
    logger.info(f"Starting PII detection pipeline: model={model}, use_regex={use_regex}, pseudonymize={pseudonymize}, realistic_fake={use_realistic_fake}")
    
    # Mapeo de modelos
    model_map = {
        'es': 'mrm8488/bert-spanish-cased-finetuned-ner',
        'en': 'dslim/bert-base-NER',
    }
    hf_model = model_map.get(model, model)

    # Preprocesamiento del texto
    if isinstance(text, dict):
        text = str(text)
    
    original_text_length = len(text)
    logger.info(f"Processing text of length {original_text_length} characters")

    # Determinar orden de ejecución
    regex_first = False
    regex_first_env = os.environ.get('REGEX_FIRST')
    if regex_first_env and regex_first_env.lower() in ('1', 'true', 'yes'):
        regex_first = True
        logger.info("Using REGEX_FIRST mode")

    backend = f"hf:{hf_model}"
    merged_mapping: Dict[str, str] = {}

    try:
        # Recolectar matches de ambas fuentes
        if HF_AVAILABLE:
            try:
                hf_matches = collect_hf_matches(text, hf_model)
                logger.info(f"HF detected {len(hf_matches)} potential matches")
            except Exception as e:
                logger.error(f"HF detection failed: {e}")
                hf_matches = []
        else:
            logger.warning("HF not available, skipping HF detection")
            hf_matches = []

        regex_matches = []
        if use_regex:
            regex_matches = collect_regex_matches(text)
            logger.info(f"Regex detected {len(regex_matches)} potential matches")
            backend += "+regex"
            if pseudonymize:
                backend += "+pseudo"
        
        # Resolver conflictos y combinar matches
        chosen = resolve_matches(hf_matches, regex_matches)
        logger.info(f"Resolved to {len(chosen)} final matches")
        
        # Obtener clave de pseudonimización si es necesaria
        pseudo_key = os.environ.get('PSEUDO_KEY') if pseudonymize else None
        if pseudonymize and not pseudo_key:
            logger.warning("Pseudonymization requested but PSEUDO_KEY not set, using fallback")
        
        # Aplicar reemplazos
        anonymized, new_map = apply_replacements_from_matches(
            text, 
            chosen, 
            use_pseudo=pseudonymize, 
            pseudo_key=pseudo_key, 
            use_realistic_fake=use_realistic_fake
        )
        merged_mapping.update(new_map)
        
        logger.info(f"Anonymization complete: {len(merged_mapping)} entities replaced")

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        anonymized = text
        merged_mapping = {}
        backend += "+error"

    # Imprimir reporte a consola
    try:
        print_report(anonymized, merged_mapping, text)
    except Exception as e:
        logger.warning(f"Failed to print report: {e}")

    # Construir resultado
    out = {
        "anonymized": anonymized,
        "mapping": merged_mapping,
        "backend": backend,
        "stats": {
            "original_length": original_text_length,
            "anonymized_length": len(anonymized),
            "entities_detected": len(merged_mapping),
            "reduction_ratio": 1.0 - (len(anonymized) / original_text_length) if original_text_length > 0 else 0
        }
    }

    # Guardar mapping si se solicita
    if save_mapping and merged_mapping:
        try:
            # Validar mapping antes de guardar
            valid_map, suspects = validate_mapping(merged_mapping)
            
            out_valid = {
                "anonymized": anonymized,
                "mapping": valid_map,
                "backend": backend,
                "stats": out["stats"]
            }
            
            # Crear directorio si no existe
            map_dir = os.path.join(HERE, '..', 'map')
            os.makedirs(map_dir, exist_ok=True)
            
            # Guardar mapping válido
            mpath = os.path.join(map_dir, 'anonymized_map.json')
            with open(mpath, 'w', encoding='utf-8') as mf:
                json.dump(out_valid, mf, ensure_ascii=False, indent=2)
            logger.info(f"Valid mapping saved to {mpath} ({len(valid_map)} entries)")
            
            # Guardar mapping sospechoso si existe
            if suspects:
                suspects_path = os.path.join(map_dir, 'anonymized_map_suspects.json')
                suspects_out = {
                    "suspects": suspects,
                    "count": len(suspects),
                    "note": "These entries require manual review"
                }
                with open(suspects_path, 'w', encoding='utf-8') as sf:
                    json.dump(suspects_out, sf, ensure_ascii=False, indent=2)
                logger.warning(f"Suspect mapping saved to {suspects_path} ({len(suspects)} entries - manual review required)")
        
        except Exception as exc:
            logger.error(f"Failed to save mapping file: {exc}", exc_info=True)

    return out


def cli(argv: List[str]):
    """Command-line interface wrapper"""
    import argparse

    p = argparse.ArgumentParser(description="Anon pipeline using HF NER (HF-only mode)")
    p.add_argument("--model", choices=["es", "en"], default="es", help="Language model to use (es/en)")
    p.add_argument("--text", help="Text to anonymize (wrap in quotes)")
    p.add_argument("--interactive", action="store_true", help="Prompt interactively for standard PII fields")
    p.add_argument("--input-file", help="Path to a text file to anonymize (reads whole file)")
    p.add_argument("--use-regex", action="store_true", help="Also run regex-based masking for emails/phones/cards/IBAN")
    p.add_argument("--pseudonymize", action="store_true", help="When used with --use-regex, replace values with deterministic pseudonyms (requires PSEUDO_KEY env var)")
    p.add_argument("--regex-first", action="store_true", help="Run regex masking/pseudonymization before HF NER (default is HF then regex)")
    p.add_argument("--no-save-mapping", action="store_true", help="Do not save mapping to anonymized_map.json")
    p.add_argument("--realistic-fake", action="store_true", help="Generate realistic fake data instead of placeholders")
    args = p.parse_args(argv)

    if args.interactive:
        fields = [
            ("Nombre y apellidos", "Name"),
            ("Número de identificación (DNI/pasaporte/SSN/NIE)", "ID"),
            ("Dirección de correo electrónico personal", "Email"),
            ("Número de teléfono", "Phone"),
            ("Dirección física completa", "Address"),
            ("Fecha de nacimiento", "DOB"),
            ("Número de tarjeta de crédito o débito", "Card"),
            ("Número de cuenta bancaria", "Bank"),
            ("Credenciales de acceso (usuario y contraseña)", "Credentials"),
            ("Dirección IP", "IP"),
            ("Datos de geolocalización", "Geo"),
            ("Imágenes/huellas/datos biométricos", "Biometric"),
            ("Combinación identificativa (ej: fecha + código postal)", "Combo"),
        ]
        print("Introduce los datos solicitados (puedes dejar en blanco si no aplica). Pulsa Enter para enviar cada campo.")
        values = {}
        hints = {
            'Name': "Ejemplo: 'Maximiliano Scarlato' — usar mayúscula inicial en nombre y apellido",
            'ID': "Ejemplo: 'Z10776543X' o 'X1234567L' (DNI o NIE) — sin espacios, en mayúsculas",
            'Email': "Ejemplo: 'maxi@gmail.com' — formato local@dominio",
            'Phone': "Ejemplo: '+34 642541238' o '642541238' — incluye prefijo país para mejor detección",
            'Address': "Ejemplo: 'Calle Falsa 123, Madrid'",
            'DOB': "Ejemplo: '1983-03-07' o '07/03/1983' — formato ISO recomendable",
            'Card': "Ejemplo: '4111111111111111' — 16 dígitos sin espacios si es posible",
            'Bank': "Ejemplo: 'ES9121000418450200051332' — IBAN completo (sin espacios)",
            'Credentials': "Ejemplo: 'usuario:juan, contraseña:P@ssw0rd' — o deja solo 'usuario' si no quieres la contraseña",
            'IP': "Ejemplo: '192.168.1.100'",
            'Geo': "Ejemplo: '40.4168,-3.7038' o 'Latitud 40.4168, Longitud -3.7038'",
            'Biometric': "No pongas imágenes reales; ejemplo: 'huella: fingerprint-001' o un id simbólico",
            'Combo': "Ejemplo: '07-03-1983 + 28860' (fecha + código postal)",
        }

        for label, key in fields:
            hint = hints.get(key, '')
            prompt = f"{label} ({hint}): " if hint else f"{label}: "
            while True:
                try:
                    val = input(prompt)
                except (EOFError, KeyboardInterrupt):
                    val = ''
                    
                if not val or not val.strip():
                    v = ''
                    break
                    
                v = val.strip()
                
                # Normalización según tipo
                if key == 'Name':
                    v = v.title()
                if key == 'ID':
                    v = v.replace(' ', '').upper()
                if key == 'Phone':
                    v = v.replace(' ', '')
                    if not v.startswith('+') and len(v) == 9 and v.isdigit():
                        v = '+34' + v
                if key == 'Email':
                    v = v.lower()
                if key in ('Card', 'Bank'):
                    v = v.replace(' ', '')

                # Validación
                valid = True
                err = ''
                
                if key == 'Email':
                    if not _is_valid_email(v):
                        valid = False
                        err = 'Formato de email inválido. Debe ser local@dominio.ext'
                        
                elif key == 'Phone':
                    is_valid, conf = _is_valid_phone(v)
                    if not is_valid:
                        valid = False
                        err = f'Número de teléfono inválido ({conf})'
                        
                elif key == 'Card':
                    if not re.match(r"^(?:\d{13,19})$", re.sub(r"\D", '', v)):
                        valid = False
                        err = 'Número de tarjeta inválido (debe tener entre 13 y 19 dígitos)'
                    else:
                        is_valid, conf = _luhn_check(v)
                        if not is_valid and conf not in ('low',):
                            valid = False
                            err = 'Número de tarjeta inválido (falló validación Luhn)'
                        
                elif key == 'Bank':
                    is_valid, conf = _is_valid_iban(v)
                    if not is_valid:
                        valid = False
                        err = f'IBAN inválido ({conf}). Formato esperado: ES.. sin espacios'
                        
                elif key == 'DOB':
                    ok = False
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            _ = datetime.strptime(v, fmt)
                            ok = True
                            break
                        except Exception:
                            pass
                    if not ok:
                        valid = False
                        err = 'Fecha inválida. Usa YYYY-MM-DD o DD/MM/YYYY'

                if valid:
                    break
                else:
                    print(f"❌ Entrada no válida: {err}. Introduce un valor correcto o deja en blanco para omitir.")

            if v:
                values[key] = v

        text = "\n".join(f"{k}: {v}" for k, v in values.items())
        if not text:
            print("No se introdujo ningún dato. Saliendo.")
            return
            
        if args.regex_first:
            os.environ['REGEX_FIRST'] = '1'
            
        run_pipeline(
            args.model, 
            text, 
            use_regex=args.use_regex, 
            pseudonymize=args.pseudonymize, 
            save_mapping=not args.no_save_mapping,
            use_realistic_fake=args.realistic_fake
        )
        return

    if args.input_file:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        run_pipeline(
            args.model, 
            text, 
            use_regex=args.use_regex, 
            pseudonymize=args.pseudonymize, 
            save_mapping=not args.no_save_mapping,
            use_realistic_fake=args.realistic_fake
        )
        return

    if args.text:
        if args.regex_first:
            os.environ['REGEX_FIRST'] = '1'
        run_pipeline(
            args.model, 
            args.text, 
            use_regex=args.use_regex, 
            pseudonymize=args.pseudonymize, 
            save_mapping=not args.no_save_mapping,
            use_realistic_fake=args.realistic_fake
        )
        return

    p.print_help()


if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])