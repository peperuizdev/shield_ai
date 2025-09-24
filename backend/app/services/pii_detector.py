"""PII detector service (renamed from pipeline.py)

This module is a near-copy of the original `pipeline.py` from SHIELD3 with the
same public function `run_pipeline(model, text, use_regex=False, pseudonymize=False, save_mapping=True)`
so the API router can call it.
"""

import argparse
import json
import sys
import os
import re
import hmac
import hashlib
from typing import List, Dict, Tuple
from datetime import datetime

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

# Faker para datos sintéticos realistas
try:
    from faker import Faker
    FAKER_AVAILABLE = True
    fake = Faker('es_ES')  # Español para datos más realistas
except Exception:
    FAKER_AVAILABLE = False
    fake = None

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


def hf_get_entities(text: str, hf_model: str):
    ner = hf_pipeline("ner", model=hf_model, grouped_entities=True)
    return ner(text)


def anonymize_with_hf(text: str, hf_model: str):
    if not HF_AVAILABLE:
        raise RuntimeError(f"transformers is required for HF-only mode: {HF_IMPORT_ERROR}")

    ents = hf_get_entities(text, hf_model)
    mapping: Dict[str, str] = {}
    anonymized = text
    ents_sorted = sorted(ents, key=lambda e: e.get('start', 0), reverse=True)
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
        orig = anonymized[start:end]
        mapping[token] = orig
        anonymized = anonymized[:start] + token + anonymized[end:]
    return anonymized, mapping


def _regex_patterns() -> Dict[str, str]:
    return {
        'CARD': r"\b(?:\d[ -]*?){13,19}\b",
        'IBAN': r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b",
        'EMAIL': r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        'PHONE': r"\+?\d[\d\s\-()]{6,}\d",
    }


def pseudonymize_value(value: str, key: str) -> str:
    if not key:
        raise RuntimeError('PSEUDO_KEY is required for pseudonymization')
    digest = hmac.new(key.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).hexdigest()
    return digest[:12]


def apply_regex_masking(text: str, use_pseudo: bool = False, pseudo_key: str = None) -> Tuple[str, Dict[str, str]]:
    patterns = _regex_patterns()
    mapping: Dict[str, str] = {}
    masked = text
    counters: Dict[str, int] = {}

    for label, pat in patterns.items():
        matches = list(re.finditer(pat, masked))
        for m in reversed(matches):
            start, end = m.start(), m.end()
            orig = masked[start:end]
            counters[label] = counters.get(label, 0) + 1
            if use_pseudo:
                if '@' in orig:
                    prefix = re.sub(r"\W+", '_', orig.split('@', 1)[0])[:20]
                else:
                    prefix = label.lower()
                digest = pseudonymize_value(orig, pseudo_key)
                pseudo_val = f"{prefix}_{digest[:8]}"
                token = pseudo_val
            else:
                token = f"[{label}_{counters[label]}]"

            mapping[token] = orig
            masked = masked[:start] + token + masked[end:]
    return masked, mapping


def _is_valid_email(val: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", val))


def _is_valid_phone(val: str) -> bool:
    if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", val) or re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", val):
        return False
    if PHONENUMBERS_AVAILABLE:
        try:
            num = phonenumbers.parse(val, "ES")
            return phonenumbers.is_valid_number(num)
        except Exception:
            try:
                num = phonenumbers.parse(val, None)
                return phonenumbers.is_valid_number(num)
            except Exception:
                return False
    digits = re.sub(r"\D", '', val)
    return 7 <= len(digits) <= 15


def _luhn_check(number: str) -> bool:
    s = re.sub(r"\D", '', number)
    if not s or not s.isdigit():
        return False
    total = 0
    reverse = s[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _is_valid_iban(val: str) -> bool:
    s = re.sub(r"\s+", '', val).upper()
    if len(s) < 5 or not re.match(r"^[A-Z0-9]+$", s):
        return False
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,}$", s):
        return False
    rearr = s[4:] + s[:4]
    converted = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rearr)
    remainder = 0
    for i in range(0, len(converted), 9):
        chunk = str(remainder) + converted[i:i+9]
        remainder = int(chunk) % 97
    return remainder == 1


def validate_mapping(mapping: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    valid = {}
    suspects = {}
    for tok, orig in mapping.items():
        lower = tok.lower()
        try:
            if lower.startswith('phone_') or lower.startswith('[phone') or lower.startswith('phone') or lower.startswith('[tel'):
                is_date = False
                if DATEUTIL_AVAILABLE:
                    try:
                        d = date_parser.parse(orig, fuzzy=False)
                        if 1900 <= d.year <= 2025:
                            is_date = True
                    except Exception:
                        is_date = False
                else:
                    if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", orig) or re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", orig):
                        is_date = True

                if is_date:
                    suspects[tok] = orig
                else:
                    if _is_valid_phone(orig):
                        valid[tok] = orig
                    else:
                        suspects[tok] = orig
            elif lower.startswith('card_') or lower.startswith('[card'):
                if _luhn_check(orig):
                    valid[tok] = orig
                else:
                    suspects[tok] = orig
            elif lower.startswith('iban_') or lower.startswith('[iban') or lower.startswith('iban'):
                if _is_valid_iban(orig):
                    valid[tok] = orig
                else:
                    suspects[tok] = orig
            else:
                if '@' in orig:
                    if _is_valid_email(orig):
                        valid[tok] = orig
                    else:
                        suspects[tok] = orig
                else:
                    valid[tok] = orig
        except Exception:
            suspects[tok] = orig
    return valid, suspects


def _parse_key_values(text: str) -> Dict[str, str]:
    res: Dict[str, str] = {}
    for line in text.splitlines():
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            if key and val:
                res[key] = val
    return res


def print_report(anonymized: str, mapping: Dict[str, str], original_text: str):
    print('\nInforme de anonimización:')
    if not mapping:
        print('  No se detectaron entidades por el modelo.')
        return
    kv = _parse_key_values(original_text)

    print('  Se han sustituido con éxito los siguientes elementos:')
    for token, original in mapping.items():
        if token.startswith('[') and ']' in token:
            typ = token.strip('[]').split('_')[0]
        else:
            if '_' in token:
                typ = token.split('_', 1)[0].upper()
            else:
                typ = 'MISC'
        matched_field = None
        for k, v in kv.items():
            if v == original or original in v or v in original:
                matched_field = k
                break
        if matched_field:
            print(f"   - {matched_field}: reemplazado por {token} (valor original: '{original}', tipo detectado: {typ})")
        else:
            print(f"   - Valor: reemplazado por {token} (valor original: '{original}', tipo detectado: {typ})")

    print('\n  Texto anonimizado (extracto):')
    excerpt = anonymized if len(anonymized) <= 500 else anonymized[:500] + '...'
    print(excerpt)


def preprocess_titlecase_name(text: str) -> str:
    import re

    def _titlecase_match(m: re.Match) -> str:
        prefix = m.group(1)
        name = m.group(2).strip()
        return f"{prefix}{name.title()}"

    text = re.sub(r"(?i)(Nombre y apellidos:\s*)(.+)", _titlecase_match, text)
    return text


def anonymize_with_local(text: str):
    raise RuntimeError("Local anonymizer is disabled in HF-only mode")


def anonymize_combined(text: str, hf_model: str):
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
    lab = (raw or '').upper()
    if lab.startswith('PER') or lab == 'PERSON':
        return 'PERSON'
    if lab.startswith('LOC') or lab == 'LOCATION':
        return 'LOCATION'
    if lab.startswith('ORG'):
        return 'ORG'
    return 'MISC'


def collect_hf_matches(text: str, hf_model: str):
    if not HF_AVAILABLE:
        return []
    ents = hf_get_entities(text, hf_model)
    matches = []
    for e in ents:
        start = e.get('start')
        end = e.get('end')
        if start is None or end is None:
            continue
        label = _normalize_hf_label(e.get('entity_group') or e.get('entity'))
        matches.append({'start': start, 'end': end, 'label': label, 'orig': text[start:end], 'source': 'hf'})
    return matches


def collect_regex_matches(text: str):
    patterns = _regex_patterns()
    matches = []
    for label, pat in patterns.items():
        for m in re.finditer(pat, text):
            matches.append({'start': m.start(), 'end': m.end(), 'label': label, 'orig': text[m.start():m.end()], 'source': 'regex'})
    return matches


def resolve_matches(hf_matches, regex_matches):
    REGEX_ALWAYS = {'EMAIL', 'PHONE', 'CARD', 'IBAN', 'IP', 'BIOMETRIC', 'CREDENTIALS', 'COMBO'}
    SYNERGY = {'ID', 'DOB'}

    hf_intervals = []
    for h in hf_matches:
        hf_intervals.append((h['start'], h['end'], h))

    def overlaps_with_hf(r):
        for s, e, h in hf_intervals:
            if not (r['end'] <= s or r['start'] >= e):
                return h
        return None

    chosen = []
    for h in hf_matches:
        chosen.append(h)

    for r in regex_matches:
        rlab = r['label'].upper()
        r['label'] = rlab
        h = overlaps_with_hf(r)
        if rlab in REGEX_ALWAYS:
            chosen.append(r)
            continue
        if h is None:
            chosen.append(r)
            continue
        if rlab in SYNERGY and h.get('label') == 'MISC':
            chosen.append(r)
            continue

    hf_only = [c for c in chosen if c.get('source') == 'hf']
    regex_only = [c for c in chosen if c.get('source') == 'regex']

    regex_only_sorted = sorted(regex_only, key=lambda r: (r['end'] - r['start']), reverse=True)
    kept_regex = []
    def overlaps(a, b):
        return not (a['end'] <= b['start'] or a['start'] >= b['end'])

    for r in regex_only_sorted:
        if any(overlaps(r, k) for k in kept_regex):
            continue
        h = overlaps_with_hf(r)
        if h is not None and not (r['label'] in SYNERGY and h.get('label') == 'MISC'):
            continue
        kept_regex.append(r)

    final = hf_only + kept_regex
    chosen_sorted = sorted(final, key=lambda x: x['start'], reverse=True)
    return chosen_sorted


def generate_realistic_fake_data(label: str, original_value: str) -> str:
    """
    Generar datos falsos realistas usando Faker basado en el tipo de dato.
    
    Args:
        label: Etiqueta del tipo de dato (PERSON, LOCATION, EMAIL, etc.)
        original_value: Valor original para contexto
        
    Returns:
        Dato falso realista
    """
    if not FAKER_AVAILABLE or not fake:
        # Fallback a placeholders si Faker no está disponible
        return f"[{label}_FAKE]"
    
    try:
        label_upper = label.upper()
        
        if label_upper in ('PERSON', 'PER'):
            return fake.name()
        elif label_upper in ('LOCATION', 'LOC'):
            return fake.city()
        elif label_upper == 'ORG':
            return fake.company()
        elif '@' in original_value:  # Email detectado por regex
            return fake.email()
        elif any(char.isdigit() for char in original_value) and ('+' in original_value or len(original_value.replace(' ', '')) >= 9):  # Teléfono
            return fake.phone_number()
        elif label_upper in ('PHONE', 'TEL'):
            return fake.phone_number()
        elif label_upper in ('CARD', 'CREDIT'):
            return fake.credit_card_number()
        elif label_upper == 'IBAN':
            return fake.iban()
        elif label_upper in ('DOB', 'DATE'):
            return fake.date_of_birth().strftime('%d/%m/%Y')
        elif label_upper == 'ID':
            return fake.bothify(text='########?').upper()
        else:
            # Para otros tipos, generar nombre genérico
            return f"{fake.first_name()}_{fake.random_int(10, 99)}"
            
    except Exception:
        # En caso de error, usar fallback
        return f"[{label}_FAKE]"


def apply_replacements_from_matches(original_text: str, matches: List[Dict], use_pseudo: bool = False, pseudo_key: str = None, use_realistic_fake: bool = False):
    anonymized = original_text
    mapping: Dict[str, str] = {}
    counters = {}
    for m in matches:
        start, end = m['start'], m['end']
        label = m['label']
        src = m.get('source', 'regex')
        orig = original_text[start:end]
        is_date_like = False
        if DATEUTIL_AVAILABLE:
            try:
                d = date_parser.parse(orig, fuzzy=False)
                if 1900 <= d.year <= 2025:
                    is_date_like = True
            except Exception:
                is_date_like = False
        else:
            if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", orig) or re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", orig):
                is_date_like = True

        if label.upper() in ('PHONE', 'PHONE_R', 'PHONE_HF') and is_date_like:
            label = 'DOB'
        keylabel = label
        if src == 'hf':
            ns = 'HF'
        else:
            ns = 'R'
        counters[keylabel + ns] = counters.get(keylabel + ns, 0) + 1
        
        # Generar reemplazo basado en el modo seleccionado
        if use_realistic_fake:
            # Modo datos falsos realistas con Faker
            token = generate_realistic_fake_data(keylabel, orig)
        elif use_pseudo and src == 'regex':
            # Modo pseudonymización con hash
            digest = pseudonymize_value(orig, pseudo_key) if pseudo_key else hashlib.sha256(orig.encode()).hexdigest()[:12]
            if '@' in orig:
                prefix = re.sub(r"\W+", '_', orig.split('@', 1)[0])[:20]
            else:
                prefix = keylabel.lower()
            token = f"{prefix}_{digest[:8]}"
        else:
            # Modo placeholder tradicional
            token = f"[{keylabel}_{counters[keylabel + ns]}]"
            
        mapping[token] = orig
        anonymized = anonymized[:start] + token + anonymized[end:]
    return anonymized, mapping


def run_pipeline(model: str, text: str, use_regex: bool = False, pseudonymize: bool = False, save_mapping: bool = True, use_realistic_fake: bool = False):
    model_map = {
        'es': 'mrm8488/bert-spanish-cased-finetuned-ner',
        'en': 'dslim/bert-base-NER',
    }
    hf_model = model_map.get(model, model)

    regex_first = False
    if isinstance(text, dict):
        pass

    regex_first_env = os.environ.get('REGEX_FIRST')
    if regex_first_env and regex_first_env.lower() in ('1', 'true', 'yes'):
        regex_first = True

    backend = f"hf:{hf_model}"
    merged_mapping: Dict[str, str] = {}

    if regex_first:
        text_for_hf = text
        regex_matches = collect_regex_matches(text) if use_regex else []
        if HF_AVAILABLE:
            try:
                hf_matches = collect_hf_matches(text_for_hf, hf_model)
            except Exception:
                hf_matches = []
        else:
            hf_matches = []
        chosen = resolve_matches(hf_matches, regex_matches)
        pseudo_key = os.environ.get('PSEUDO_KEY') if pseudonymize else None
        anonymized, new_map = apply_replacements_from_matches(text, chosen, use_pseudo=pseudonymize, pseudo_key=pseudo_key, use_realistic_fake=use_realistic_fake)
        merged_mapping.update(new_map)

    else:
        if HF_AVAILABLE:
            try:
                hf_matches = collect_hf_matches(text, hf_model)
            except Exception:
                hf_matches = []
        else:
            hf_matches = []

        regex_matches = collect_regex_matches(text) if use_regex else []
        chosen = resolve_matches(hf_matches, regex_matches)
        pseudo_key = os.environ.get('PSEUDO_KEY') if pseudonymize else None
        anonymized, new_map = apply_replacements_from_matches(text, chosen, use_pseudo=pseudonymize, pseudo_key=pseudo_key, use_realistic_fake=use_realistic_fake)
        merged_mapping.update(new_map)
        if use_regex:
            backend += "+regex"
            if pseudonymize:
                backend += "+pseudo"

    try:
        print_report(anonymized, merged_mapping, text)
    except Exception:
        pass

    out = {"anonymized": anonymized, "mapping": merged_mapping, "backend": backend}

    if save_mapping:
        try:
            valid_map, suspects = validate_mapping(merged_mapping)
            out_valid = {"anonymized": anonymized, "mapping": valid_map, "backend": backend}
            map_dir = os.path.join(HERE, '..', 'map')
            os.makedirs(map_dir, exist_ok=True)
            mpath = os.path.join(map_dir, 'anonymized_map.json')
            with open(mpath, 'w', encoding='utf-8') as mf:
                json.dump(out_valid, mf, ensure_ascii=False, indent=2)
            print(f"Valid mapping saved to {mpath}")
            if suspects:
                suspects_path = os.path.join(map_dir, 'anonymized_map_suspects.json')
                with open(suspects_path, 'w', encoding='utf-8') as sf:
                    json.dump({"suspects": suspects}, sf, ensure_ascii=False, indent=2)
                print(f"Suspect mapping entries saved to {suspects_path} (manual review required)")
        except Exception as exc:
            print(f"Warning: failed to save mapping file: {exc}")

    return out


def cli(argv: List[str]):
    """Command-line interface wrapper for running the pipeline from this module.

    This mirrors the original pipeline.py CLI so the interactive prompts work
    the same as before.
    """
    import argparse

    p = argparse.ArgumentParser(description="Anon pipeline using HF NER (HF-only mode)")
    p.add_argument("--model", choices=["es", "en"], default="es", help="Language model to use (es/en)")
    p.add_argument("--text", help="Text to anonymize (wrap in quotes)")
    p.add_argument("--interactive", action="store_true", help="Prompt interactively for standard PII fields")
    p.add_argument("--input-file", help="Path to a text file to anonymize (reads whole file)")
    p.add_argument("--use-regex", action="store_true", help="Also run regex-based masking for emails/phones/cards/IBAN")
    p.add_argument("--pseudonymize", action="store_true", help="When used with --use-regex, replace values with deterministic pseudonyms (requires PSEUDO_KEY env var)")
    p.add_argument("--regex-first", action="store_true", help="Run regex masking/pseudonymization before HF NER (default is HF then regex)")
    p.add_argument("--no-save-mapping", action="store_true", help="Do not save mapping to anonymized_map.json (mapping is printed to stdout by default)")
    args = p.parse_args(argv)

    if args.interactive:
        # Prompt the user for the PII fields requested by the user
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
            'ID': "Ejemplo: 'Z10776543X' — sin espacios, en mayúsculas",
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
                except EOFError:
                    val = ''
                if not val or not val.strip():
                    v = ''
                    break
                v = val.strip()
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

                valid = True
                err = ''
                if key == 'Email':
                    if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", v):
                        valid = False
                        err = 'Formato de email inválido. Debe ser local@dominio.ext'
                elif key == 'Phone':
                    digits = re.sub(r"\D", '', v)
                    if len(digits) < 7 or len(digits) > 15:
                        valid = False
                        err = 'Número de teléfono inválido (longitud incorrecta)'
                elif key == 'Card':
                    if not re.match(r"^(?:\d{13,19})$", re.sub(r"\D", '', v)):
                        valid = False
                        err = 'Número de tarjeta inválido (debe tener entre 13 y 19 dígitos)'
                elif key == 'Bank':
                    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$", v.upper()):
                        valid = False
                        err = 'IBAN inválido. Formato esperado: ES.. sin espacios'
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
                    print(f"Entrada no válida: {err}. Introduce un valor correcto o deja en blanco para omitir.")

            if v:
                values[key] = v

        text = "\n".join(f"{k}: {v}" for k, v in values.items())
        if not text:
            print("No se introdujo ningún dato. Saliendo.")
            return
        if args.regex_first:
            os.environ['REGEX_FIRST'] = '1'
        run_pipeline(args.model, text, use_regex=args.use_regex, pseudonymize=args.pseudonymize, save_mapping=not args.no_save_mapping)
        return

    if args.input_file:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        run_pipeline(args.model, text, use_regex=args.use_regex, pseudonymize=args.pseudonymize, save_mapping=not args.no_save_mapping)
        return

    if args.text:
        run_pipeline(args.model, args.text, use_regex=args.use_regex, pseudonymize=args.pseudonymize, save_mapping=not args.no_save_mapping)
        return

    p.print_help()


# Allow CLI usage for backward compatibility when running module directly
if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])
