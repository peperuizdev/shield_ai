"""
Word-by-Word Deanonymizer for Shield AI

Este módulo procesa el streaming palabra por palabra en lugar de retener
caracteres hasta completar nombres completos, resultando en un streaming
más fluido y natural.
"""

import re
import logging
import time
from typing import Dict, List, Tuple, Optional

# Import metrics collection
try:
    from api.routes.metrics import (
        record_deanonymization_request, 
        record_deanonymization_failure
    )
    METRICS_AVAILABLE = True
except Exception:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)

class WordByWordDeanonymizer:
    """
    Deanonimizador que procesa streaming palabra por palabra para mayor fluidez
    """
    
    def __init__(self, mapping: Dict[str, str]):
        """
        Inicializa el deanonimizador
        
        Args:
            mapping: Diccionario de anonimización {token_fake: valor_real}
        """
        self.original_mapping = mapping or {}
        
        # Expandir mapping con variaciones de formato
        self.mapping = self._expand_mapping_variations(self.original_mapping)
        self.inverted_mapping = {real: fake for fake, real in self.mapping.items()}
        
        # Buffer para palabra actual en construcción
        self.partial_word = ""
        
        # Buffer inteligente para valores complejos que pueden dividirse entre chunks
        self.smart_buffer = ""
        self.max_buffer_size = 200  # Tamaño máximo del buffer inteligente
        
        # Métricas de procesamiento
        self.words_processed = 0
        self.names_replaced = 0
        
        # Preparar mapeo optimizado
        self._prepare_word_mapping()
        self._prepare_complex_patterns()
        
        logger.info(f"WordByWordDeanonymizer initialized with {len(self.original_mapping)} original mappings, expanded to {len(self.mapping)} variations")
    
    def add_mapping(self, new_mapping: Dict[str, str]):
        """
        Añade nuevos mappings al deanonimizador existente
        
        Args:
            new_mapping: Diccionario de nuevos mappings {token_fake: valor_real}
        """
        if not new_mapping:
            return
        
        # Actualizar mappings originales
        self.original_mapping.update(new_mapping)
        
        # Expandir con variaciones los nuevos mappings
        expanded_new = self._expand_mapping_variations(new_mapping)
        self.mapping.update(expanded_new)
        
        # Actualizar mapping invertido
        for fake, real in expanded_new.items():
            self.inverted_mapping[real] = fake
        
        # Reconfigurar patrones
        self._prepare_word_mapping()
        self._prepare_complex_patterns()
        
        logger.info(f"Added {len(new_mapping)} new mappings, expanded to {len(expanded_new)} variations. Total mappings: {len(self.mapping)}")
    
    def _expand_mapping_variations(self, original_mapping: Dict[str, str]) -> Dict[str, str]:
        """
        Expande el mapping original con variaciones de formato comunes
        que puede generar el LLM para el mismo dato
        
        Returns:
            Mapping expandido con todas las variaciones
        """
        expanded = original_mapping.copy()
        
        import re
        
        for fake_token, real_value in original_mapping.items():
            variations = []
            
            # 1. VARIACIONES DE TELÉFONOS
            if self._looks_like_phone(fake_token):
                variations.extend(self._generate_phone_variations(fake_token, real_value))
            
            # 2. VARIACIONES DE IBANs
            elif self._looks_like_iban(fake_token):
                variations.extend(self._generate_iban_variations(fake_token, real_value))
                
            # 3. VARIACIONES DE EMAILS (menos comunes pero posibles)
            elif '@' in fake_token:
                variations.extend(self._generate_email_variations(fake_token, real_value))
            
            # Añadir todas las variaciones al mapping expandido
            for variation in variations:
                if variation not in expanded:  # No sobrescribir mappings existentes
                    expanded[variation] = real_value
                    logger.debug(f"Added variation: '{variation}' -> '{real_value}' (from '{fake_token}')")
        
        return expanded
    
    def _looks_like_phone(self, text: str) -> bool:
        """Detecta si un texto parece un teléfono"""
        import re
        phone_patterns = [
            r'\+\d{1,3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}',
            r'\d{3}[\s\-]?\d{3}[\s\-]?\d{3}',
            r'\(\+\d{1,3}\)[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}',
        ]
        return any(re.search(pattern, text) for pattern in phone_patterns)
    
    def _looks_like_iban(self, text: str) -> bool:
        """Detecta si un texto parece un IBAN"""
        import re
        return bool(re.match(r'^[A-Z]{2}\d{2}[\s\d]+$', text))
    
    def _generate_phone_variations(self, original_phone: str, real_value: str) -> list:
        """
        Genera variaciones comunes de formato de teléfono
        que el LLM podría usar
        """
        import re
        variations = []
        
        # Extraer solo dígitos
        digits = ''.join(filter(str.isdigit, original_phone))
        
        if len(digits) >= 9:  # Teléfono válido
            # Formatos comunes que puede generar el LLM:
            
            # Con país +34
            if digits.startswith('34') and len(digits) > 9:
                local_digits = digits[2:]  # Sin el 34
                variations.extend([
                    f"(+34-{local_digits[:3]})-{local_digits[3:6]}-{local_digits[6:]}",
                    f"(+34){local_digits[:3]}-{local_digits[3:6]}-{local_digits[6:]}",
                    f"+34-{local_digits[:3]}-{local_digits[3:6]}-{local_digits[6:]}",
                    f"+34 {local_digits[:3]} {local_digits[3:6]} {local_digits[6:]}",
                    f"({local_digits[:3]}) {local_digits[3:6]}-{local_digits[6:]}",
                ])
            
            # Sin país
            local_digits = digits[-9:]  # Últimos 9 dígitos
            variations.extend([
                f"({local_digits[:3]})-{local_digits[3:6]}-{local_digits[6:]}",
                f"{local_digits[:3]}-{local_digits[3:6]}-{local_digits[6:]}",
                f"{local_digits[:3]} {local_digits[3:6]} {local_digits[6:]}",
                f"({local_digits[:3]}) {local_digits[3:6]} {local_digits[6:]}",
            ])
        
        return variations
    
    def _generate_iban_variations(self, original_iban: str, real_value: str) -> list:
        """
        Genera variaciones de formato de IBAN
        """
        variations = []
        
        # El IBAN puede aparecer con espacios diferentes
        iban_no_spaces = original_iban.replace(' ', '')
        
        if len(iban_no_spaces) >= 15:  # IBAN mínimo válido
            # Formatos comunes:
            variations.extend([
                iban_no_spaces,  # Sin espacios
                f"{iban_no_spaces[:4]} {iban_no_spaces[4:8]} {iban_no_spaces[8:12]} {iban_no_spaces[12:16]} {iban_no_spaces[16:]}",  # Grupos de 4
                f"{iban_no_spaces[:4]} {iban_no_spaces[4:]}",  # Código país separado
            ])
        
        return variations
    
    def _generate_email_variations(self, original_email: str, real_value: str) -> list:
        """
        Genera variaciones de email (menos comunes)
        """
        # Los emails suelen mantener formato, pero por completeness
        return [original_email.lower(), original_email.upper()]
    
    def _prepare_word_mapping(self):
        """Prepara el mapeo optimizado para búsquedas rápidas"""
        self.word_mapping = {}
        self.multiword_mapping = {}
        self.name_prefixes = set()
        
        for fake_token, real_value in self.mapping.items():
            # Usar el token completo con corchetes para mapeo directo
            self.word_mapping[fake_token] = real_value
            
            # También añadir prefijos progresivos para detección temprana
            for i in range(2, len(fake_token) + 1):
                prefix = fake_token[:i]
                self.name_prefixes.add(prefix)
            
            # Para nombres multi-palabra, registrar también
            real_words = real_value.split()
            if len(real_words) > 1:
                self.multiword_mapping[fake_token] = real_value
    
    def _prepare_complex_patterns(self):
        """Prepara patrones para valores complejos que pueden dividirse entre chunks"""
        self.complex_patterns = []
        
        for fake_token, real_value in self.mapping.items():
            # Identificar patrones complejos (con espacios, guiones, etc.)
            if any(char in fake_token for char in [' ', '-', '@', 'ES']):
                # Crear patrón flexible que permita divisiones
                pattern_parts = self._create_flexible_pattern(fake_token)
                self.complex_patterns.append({
                    'original': fake_token,
                    'replacement': real_value,
                    'pattern_parts': pattern_parts,
                    'normalized': self._normalize_for_matching(fake_token)
                })
    
    def _create_flexible_pattern(self, token: str) -> List[str]:
        """Crea partes flexibles de un patrón que pueden aparecer divididas"""
        # Para teléfonos como "794 124 208" -> ["794", "124", "208"]
        # Para emails -> dividir por @ y .
        # Para IBANs -> dividir por espacios
        
        if '@' in token:
            # Email: dividir por @ y por .
            parts = []
            email_parts = token.split('@')
            parts.extend(email_parts[0].split('.'))
            if len(email_parts) > 1:
                parts.append('@')
                parts.extend(email_parts[1].split('.'))
            return [p for p in parts if p]
        
        elif token.startswith('ES') and len(token) > 10:
            # IBAN: dividir por espacios
            return [p for p in token.split() if p]
        
        else:
            # Teléfonos y otros: dividir por espacios y guiones
            import re
            parts = re.split(r'[\s\-]+', token)
            return [p for p in parts if p]
    
    def _normalize_for_matching(self, text: str) -> str:
        """Normaliza texto para matching flexible"""
        import re
        # Quitar espacios, guiones, paréntesis y mantener solo alfanuméricos
        return re.sub(r'[^\w@.]', '', text).lower()
    
    def process_chunk(self, chunk: str) -> str:
        """
        Procesa un chunk de streaming palabra por palabra con buffer inteligente
        
        Args:
            chunk: Fragmento de texto del streaming
            
        Returns:
            Texto procesado con reemplazos aplicados
        """
        if not chunk:
            return ""
        
        start_time = time.time()
        
        try:
            # Añadir al buffer inteligente
            self.smart_buffer += chunk
            
            # Limitar el tamaño del buffer para evitar problemas de memoria
            if len(self.smart_buffer) > self.max_buffer_size:
                # Mantener solo la parte final del buffer
                self.smart_buffer = self.smart_buffer[-self.max_buffer_size:]
            
            # Procesar con el método mejorado
            result, buffer_to_keep = self._process_with_smart_buffer()
            
            # Actualizar el buffer con lo que debemos conservar
            self.smart_buffer = buffer_to_keep
            
            # Record metrics if available
            if METRICS_AVAILABLE and result:
                duration = time.time() - start_time
                record_deanonymization_request(duration)
            
            return result
            
        except Exception as e:
            if METRICS_AVAILABLE:
                record_deanonymization_failure("smart_buffer_error")
            logger.error(f"Error in smart buffer processing: {e}")
            # Fallback al método original
            return self._process_chunk_fallback(chunk)
    
    def _process_with_smart_buffer(self) -> Tuple[str, str]:
        """
        Procesa el buffer inteligente buscando patrones completos y parciales
        
        Returns:
            Tuple[str, str]: (resultado_a_enviar, buffer_a_conservar)
        """
        buffer_text = self.smart_buffer
        
        # 1. Buscar y reemplazar tokens exactos primero
        for fake_token, real_value in self.mapping.items():
            if fake_token in buffer_text:
                buffer_text = buffer_text.replace(fake_token, real_value)
                self.names_replaced += 1
                logger.debug(f"Exact replacement: '{fake_token}' -> '{real_value}'")
        
        # 2. Buscar patrones complejos con matching flexible
        buffer_text = self._smart_complex_replacement(buffer_text)
        
        # 3. Determinar qué parte del buffer podemos enviar
        safe_to_send, keep_in_buffer = self._determine_safe_output(buffer_text)
        
        return safe_to_send, keep_in_buffer
    
    def _smart_complex_replacement(self, text: str) -> str:
        """Aplica reemplazos inteligentes para patrones complejos"""
        
        # Aplicar smart phone replacement existente
        text = self._smart_phone_replacement(text)
        
        # Aplicar reemplazos para otros patrones complejos
        for pattern_info in self.complex_patterns:
            text = self._apply_flexible_pattern_replacement(text, pattern_info)
        
        return text
    
    def _apply_flexible_pattern_replacement(self, text: str, pattern_info: Dict) -> str:
        """Aplica reemplazo flexible para un patrón específico"""
        original = pattern_info['original']
        replacement = pattern_info['replacement']
        normalized_original = pattern_info['normalized']
        
        # Normalizar el texto para buscar coincidencias flexibles
        normalized_text = self._normalize_for_matching(text)
        
        # Buscar el patrón normalizado en el texto normalizado
        if normalized_original in normalized_text:
            # Encontrar la posición en el texto original
            pos = self._find_flexible_match_position(text, original)
            if pos >= 0:
                # Reemplazar en el texto original
                before = text[:pos]
                after = text[pos + len(original):]
                text = before + replacement + after
                self.names_replaced += 1
                logger.debug(f"Flexible replacement: '{original}' -> '{replacement}'")
        
        return text
    
    def _find_flexible_match_position(self, text: str, pattern: str) -> int:
        """Encuentra la posición de un patrón de forma flexible"""
        import re
        
        # Crear regex flexible que ignore espacios, guiones y paréntesis en diferentes posiciones
        pattern_normalized = self._normalize_for_matching(pattern)
        
        # Buscar secuencias de caracteres que coincidan con el patrón normalizado
        for i in range(len(text)):
            for j in range(i + len(pattern_normalized), len(text) + 1):
                substring = text[i:j]
                if self._normalize_for_matching(substring) == pattern_normalized:
                    return i
        
        return -1
    
    def _determine_safe_output(self, processed_text: str) -> Tuple[str, str]:
        """
        Determina qué parte del texto procesado es seguro enviar inmediatamente
        VERSIÓN MEJORADA: Detecta patrones parciales antes de enviarlos
        
        Returns:
            Tuple[str, str]: (texto_seguro_para_enviar, texto_a_mantener_en_buffer)
        """
        # 🎯 LÓGICA ESPECIAL: Si el buffer contiene IBAN real completo, enviarlo inmediatamente
        if self._contains_complete_real_iban(processed_text):
            logger.debug("IBAN real completo detectado - enviando inmediatamente")
            return processed_text, ""
        
        # Si el texto es muy corto, mantener en buffer
        if len(processed_text) <= 60:  # Aumentado de 30 a 60
            return "", processed_text
        
        # 1. DETECTAR PATRONES PARCIALES AL FINAL del texto
        if self._has_incomplete_pattern_at_end(processed_text):
            # Si hay un patrón parcial, ser MUCHO más conservador (usuario solicita >21 chars)
            safety_margin = min(120, len(processed_text) // 2)  # Aumentado de 80 a 120
            logger.debug(f"Patrón parcial detectado, usando margen de seguridad AUMENTADO: {safety_margin}")
        else:
            # Margen normal también aumentado significativamente
            safety_margin = 80  # Aumentado de 40 a 80
        
        if len(processed_text) <= safety_margin:
            return "", processed_text
        
        # 2. BUSCAR PUNTO DE CORTE SEGURO
        safe_cutoff = len(processed_text) - safety_margin
        
        # Buscar hacia atrás un punto de corte natural
        for i in range(safe_cutoff, max(0, safe_cutoff - 30), -1):
            if processed_text[i] in ' \n\t.,;:!)}]':
                safe_to_send = processed_text[:i + 1]
                keep_in_buffer = processed_text[i + 1:]
                
                # 3. VERIFICACIÓN FINAL: No dividir mappings conocidos
                if not self._would_split_known_mapping(safe_to_send, keep_in_buffer):
                    return safe_to_send, keep_in_buffer
        
        # Si no encontramos punto seguro, ser más conservador
        emergency_cutoff = len(processed_text) - safety_margin
        if emergency_cutoff > 0:
            return processed_text[:emergency_cutoff], processed_text[emergency_cutoff:]
        
        # Último recurso: mantener todo
        return "", processed_text
    
    def _has_incomplete_pattern_at_end(self, text: str) -> bool:
        """
        Detecta si hay un patrón incompleto al final que podría necesitar más datos
        DETECTA: IBANs, emails, teléfonos parciales
        
        Returns:
            True si hay un patrón potencialmente incompleto
        """
        import re
        
        # Analizar los últimos 60 caracteres
        text_end = text[-60:] if len(text) > 60 else text
        
        # 🎯 DETECCIÓN CRÍTICA: IBAN ANÓNIMO FRAGMENTADO
        if self._has_fragmented_anonymous_iban(text_end):
            logger.debug("IBAN anónimo fragmentado detectado - BUFFER OBLIGATORIO")
            return True
        
        # 🎯 DETECCIÓN INTELIGENTE DE IBAN REAL INCOMPLETO
        if self._has_incomplete_iban_at_end(text_end):
            return True
        
        # PATRONES PROBLEMÁTICOS que podrían estar incompletos:
        incomplete_patterns = [
            # Emails parciales  
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*$',   # user@domain...
            r'[a-zA-Z0-9._%+-]+@$',                 # user@
            
            # Teléfonos parciales
            r'\+\d{1,3}[\s\-]*\d{0,3}[\s\-]*\d{0,3}[\s\-]*\d{0,3}$',  # +34 612...
            r'\(\+\d{1,3}[\s\-]*\d{0,3}[\s\-]*\d{0,3}[\s\-]*\d{0,3}$', # (+34 612...
            
            # Números de cuenta/tarjeta parciales
            r'\d{4}[\s\-]*\d{0,4}[\s\-]*\d{0,4}[\s\-]*\d{0,4}$',      # 1234 5678...
            
            # DNI/NIE parciales
            r'\d{1,8}[A-Z]?$',                      # 12345678...
        ]
        
        for pattern in incomplete_patterns:
            if re.search(pattern, text_end):
                logger.debug(f"Patrón incompleto detectado: {pattern} en '{text_end[-20:]}'")
                return True
        
        return False
    
    def _has_incomplete_iban_at_end(self, text_end: str) -> bool:
        """
        🎯 NUEVA LÓGICA INTELIGENTE: Detecta IBAN incompleto con validación de longitud
        
        IBAN Español válido: ES + 2 dígitos control + 20 caracteres = 24 total
        Ejemplo completo: ES9121000418450200051332
        
        Returns:
            True si hay IBAN incompleto que necesita más datos
        """
        import re
        
        # 🔍 CASOS ESPECÍFICOS PROBLEMÁTICOS (fragmentos sin país)
        fragment_patterns = [
            r'\d{2,4}\s+\d{4}\s+\d{4}(\s+\d{1,2})?$',  # "03 4839 3015 63"
            r'S\d{2}\s+\d{4}\s+\d{4}(\s+\d{1,2})?$',   # "S03 4839 3015 63"
            r'\d{4}\s+\d{4}\s+\d{2}\s+\d{1,3}$',       # "4839 3015 63 962"
        ]
        
        for pattern in fragment_patterns:
            if re.search(pattern, text_end):
                logger.debug(f"Fragmento IBAN detectado: patrón '{pattern}' en '{text_end[-25:]}'")
                return True
        
        # Buscar todos los posibles IBANs en los últimos 60 caracteres
        iban_patterns = [
            r'ES\s*\d{2}[\s\d]*',                     # ES33 8565...
            r'[A-Z]{2}\s*\d{2}[\s\d]*',             # Cualquier país
            r'[A-Z]{2}\d{2}[\s\d]*',                 # Sin espacios iniciales
        ]
        
        for pattern in iban_patterns:
            # Buscar todos los matches en el texto
            matches = list(re.finditer(pattern, text_end))
            if not matches:
                continue
                
            # Tomar el último match (más cerca del final)
            match = matches[-1]
            potential_iban = match.group()
            match_end = match.end()
            
            # ✅ Solo procesar si el match está en los últimos 40 caracteres
            text_after_iban = text_end[match_end:].strip()
            if len(text_after_iban) > 40:  # Demasiado texto después, probablemente no es el IBAN del final
                continue
                
            logger.debug(f"Evaluando potencial IBAN: '{potential_iban}' (texto después: '{text_after_iban[:20]}...')")
            
            # 🔍 VALIDACIÓN 1: Longitud de caracteres alfanuméricos
            clean_iban = re.sub(r'[\s\-]', '', potential_iban.upper())
            logger.debug(f"IBAN limpio: '{clean_iban}' (longitud: {len(clean_iban)})")
            
            # 🎯 ESPAÑOL: Debe tener exactamente 24 caracteres
            if clean_iban.startswith('ES'):
                if len(clean_iban) < 24:
                    logger.debug(f"IBAN español INCOMPLETO: {len(clean_iban)}/24 caracteres - SIEMPRE buffer")
                    return True  # ✅ PRIORIDAD MÁXIMA: si no tiene 24 chars, BUFFER SIEMPRE
                elif len(clean_iban) == 24:
                    # ✅ Longitud correcta, verificar si tiene separador de final
                    if self._iban_has_clear_ending(text_end, potential_iban):
                        logger.debug("IBAN español completo con final claro")
                        return False
                    else:
                        logger.debug("IBAN español 24 chars exactos - está completo, liberando")
                        return False  # ✅ IBAN completo con 24 chars = listo para enviar
                else:
                    logger.debug(f"IBAN español demasiado largo: {len(clean_iban)} chars - liberando")
                    return False  # Más de 24 = no es IBAN español válido
            elif len(clean_iban) >= 2 and clean_iban[:2].isalpha():
                # 🌍 OTROS PAÍSES: Rangos típicos 15-34 caracteres
                if len(clean_iban) < 15:
                    logger.debug(f"IBAN extranjero incompleto: {len(clean_iban)} caracteres")
                    return True
                elif len(clean_iban) >= 15 and len(clean_iban) <= 34:
                    # Podría estar completo, verificar contexto
                    if self._iban_has_clear_ending(text_end, potential_iban):
                        logger.debug("IBAN extranjero con final claro")
                        return False
                    else:
                        logger.debug("IBAN extranjero sin separador claro, esperando")
                        return True
        
        return False
    
    def _iban_has_clear_ending(self, text_end: str, iban_match: str) -> bool:
        """
        🎯 DETECCIÓN DE FINAL DE IBAN: Verifica si hay separadores claros
        
        Separadores válidos que indican final:
        - Nueva línea (\n)
        - Espacio + texto no numérico 
        - Puntuación (. , ; : ! ?)
        - Final de cadena con contexto claro
        """
        # Encontrar la posición donde termina el IBAN
        iban_end_pos = text_end.rfind(iban_match) + len(iban_match)
        
        # Verificar qué hay después del IBAN
        remaining = text_end[iban_end_pos:] if iban_end_pos < len(text_end) else ""
        
        # ✅ FINALES CLAROS
        clear_endings = [
            r'^\s*\n',                  # Nueva línea después
            r'^\s*[.,:;!?]',           # Puntuación
            r'^\s*$',                   # Final de texto
            r'^\s+[a-zA-Z]{2,}',       # Espacio + palabra (no número)
            r'^\s*[-\)\]\}]',          # Caracteres de cierre
        ]
        
        for ending_pattern in clear_endings:
            if re.match(ending_pattern, remaining):
                logger.debug(f"Final claro detectado: patrón '{ending_pattern}'")
                return True
        
        # ❌ FINALES AMBIGUOS (podría continuar)
        ambiguous_patterns = [
            r'^\s*\d',                  # Más dígitos después
            r'^[A-Z0-9]',              # Más caracteres alfanuméricos
        ]
        
        for ambiguous in ambiguous_patterns:
            if re.match(ambiguous, remaining):
                logger.debug(f"Final ambiguo detectado: patrón '{ambiguous}'")
                return False
        
        # Si no hay texto después, considerar final claro
        if not remaining.strip():
            logger.debug("Final de texto - considerando claro")
            return True
        
        # Por defecto, conservador
        logger.debug("Final incierto, siendo conservador")
        return False
    
    def _has_fragmented_anonymous_iban(self, text_end: str) -> bool:
        """
        🎯 NUEVA FUNCIÓN: Detecta IBAN anónimo fragmentado que causará concatenación
        
        Detecta casos como:
        1. 'ES66 2127 7396 56 5' (IBAN anónimo parcial)
        2. Seguido de token como '(328)-565-308' que se mapea al IBAN real
        
        Returns:
            True si detecta IBAN anónimo fragmentado que necesita buffering completo
        """
        import re
        
        # 🔍 PATRONES DE IBAN ANÓNIMO FRAGMENTADO - VERSIÓN AMPLIADA Y AGRESIVA
        anonymous_iban_patterns = [
            # Patrones específicos existentes
            r'ES\d{2}\s+\d{4}\s+\d{4}\s+\d{2}\s+\d{1,3}$',        # ES66 2127 7396 56 5
            r'ES\d{2}\s+\d{4}\s+\d{4}\s+\d{2}\s+\d{1,4}$',        # ES03 0338 4034 42 5xxx
            r'[A-Z]{2}\d{2}\s+\d{4}\s+\d{4}\s+\d{2}\s+\d{1,4}$',  # Genérico ampliado
            
            # Patrones más cortos para detección temprana
            r'ES\d{2}\s+\d{4}\s+\d{4}$',                          # ES66 2127 7396 (más corto)
            r'ES\d{2}\s+\d{4}\s+\d{3,4}\s+\d{1,3}$',              # ES03 0338 403x xx x
            r'[A-Z]{2}\d{2}\s+\d{4}\s+\d{3,4}\s+\d{1,3}$',        # Genérico medio
            
            # Patrones muy específicos para casos edge
            r'[A-Z]{2}\d{2}\s+\d{4}\s+\d{3}\s+\d{2}\s+\d{1}$',    # ES12 3456 789 12 3
            r'[A-Z]{2}\d{2}\s+\d{4}\s+\d{4}\s+\d{1,2}\s+\d{1,4}$', # Variaciones amplias
            
            # NUEVO: Patrones sin espacios (para IBANs concatenados)
            r'ES\d{2}\d{4}\d{4}\d{2}\d{1,4}$',                    # ES030338403442 + fragmento
            r'[A-Z]{2}\d{2}\d{4}\d{4}\d{2}\d{1,4}$',              # Genérico sin espacios
            
            # NUEVO: Detección ultra-agresiva de cualquier secuencia que empiece como IBAN
            r'ES\d{2}[\s\d]{10,20}$',                             # ES + 2 dígitos + 10-20 chars
            r'[A-Z]{2}\d{2}[\s\d]{10,20}$',                       # Cualquier país + patrón similar
        ]
        
        for pattern in anonymous_iban_patterns:
            if re.search(pattern, text_end):
                # Verificar si parece IBAN anónimo (no el real)
                match = re.search(pattern, text_end)
                potential_iban = match.group().strip()
                
                # Limpiar para análisis
                clean_iban = re.sub(r'[\s\-]', '', potential_iban)
                
                # ✅ Si es IBAN español pero tiene longitud incorrecta -> probablemente anónimo
                if clean_iban.startswith('ES') and len(clean_iban) != 24:
                    logger.debug(f"IBAN anónimo fragmentado detectado: '{potential_iban}' ({len(clean_iban)} chars)")
                    return True
                
                # ✅ Si parece IBAN pero no pasa validación -> probablemente anónimo
                if not self._is_likely_real_iban(clean_iban):
                    logger.debug(f"IBAN anónimo fragmentado (no válido): '{potential_iban}'")
                    return True
        
        # 🔍 DETECTAR TOKENS DE CONTINUACIÓN - VERSIÓN AMPLIADA
        # Patrones que podrían completar un IBAN anónimo fragmentado
        continuation_patterns = [
            # Patrones telefónicos que suelen ser tokens de continuación
            r'\(\d{3}\)-\d{3}-\d{3}$',           # (328)-565-308
            r'\d{3}-\d{3}-\d{3}$',               # 328-565-308
            r'\(\d{3}\)\s?\d{3}-?\d{3}$',        # (328) 565-308 o (328)565308
            
            # Secuencias numéricas largas (posibles tokens IBAN)
            r'\d{8,15}$',                        # 247719739 (ampliado de 12 a 15)
            r'\d{6,10}$',                        # Números medianos también
            
            # NUEVO: Patrones específicos de finalización IBAN
            r'\d{4}\d{4}\d{4}$',                 # 1234567890123 (3 grupos de 4)
            r'\d{2,4}\d{4,8}$',                  # Patrones variables
            
            # NUEVO: Detección ultra-agresiva - cualquier secuencia numérica al final
            r'\d{5,}$',                          # 5 o más dígitos consecutivos
        ]
        
        for pattern in continuation_patterns:
            if re.search(pattern, text_end):
                logger.debug(f"Token de continuación IBAN detectado: patrón '{pattern}'")
                return True
        
        return False
    
    def _is_likely_real_iban(self, clean_iban: str) -> bool:
        """
        Verificación rápida si un IBAN limpio parece real o anónimo
        
        Returns:
            True si parece un IBAN real válido
        """
        # Validaciones básicas para IBAN español
        if clean_iban.startswith('ES'):
            if len(clean_iban) != 24:
                return False
            
            # Verificación básica de dígitos de control
            try:
                # Algoritmo IBAN simplificado
                rearr = clean_iban[4:] + clean_iban[:4]
                converted = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rearr)
                remainder = int(converted) % 97
                return remainder == 1
            except:
                return False
        
        return True  # Por defecto, asumir que es real si no es español
    
    def _contains_complete_real_iban(self, text: str) -> bool:
        """
        🎯 FUNCIÓN CRÍTICA: Detecta si el texto contiene un IBAN real completo
        que debe ser enviado inmediatamente para evitar concatenación
        
        Returns:
            True si contiene IBAN real completo que debe enviarse ya
        """
        import re
        
        # Buscar patrones de IBAN completo español
        iban_pattern = r'ES\d{2}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}'
        matches = re.finditer(iban_pattern, text)
        
        for match in matches:
            iban_candidate = match.group().strip()
            clean_iban = re.sub(r'[\s\-]', '', iban_candidate)
            
            # Verificar si es IBAN real válido
            if self._is_likely_real_iban(clean_iban):
                # Además, verificar si este IBAN está en nuestros valores de mapping (lado real)
                if clean_iban in self.inverted_mapping or iban_candidate in self.inverted_mapping:
                    logger.debug(f"IBAN real completo identificado para envío: '{iban_candidate}'")
                    return True
        
        return False
    
    def _would_split_known_mapping(self, safe_part: str, buffer_part: str) -> bool:
        """
        Verifica si enviar safe_part y mantener buffer_part dividiría un mapping conocido
        
        Returns:
            True si detecta que se dividiría un mapping
        """
        # Crear zona de unión para análisis
        junction_zone = safe_part[-30:] + buffer_part[:30]
        
        # Verificar cada mapping conocido
        for fake_token in self.mapping.keys():
            if fake_token in junction_zone:
                # Encontrar posición del token en la zona de unión
                token_pos = junction_zone.find(fake_token)
                token_end = token_pos + len(fake_token)
                safe_part_len = len(safe_part[-30:])
                
                # Si el token se divide entre safe_part y buffer_part
                if token_pos < safe_part_len < token_end:
                    logger.debug(f"Evitando división de mapping: '{fake_token}'")
                    return True
        
        return False
    
    def _process_chunk_fallback(self, chunk: str) -> str:
        """Método de fallback en caso de error en el buffer inteligente"""
        # Usar el método original como fallback
        self.partial_word += chunk
        
        # Aplicar reemplazos básicos
        remaining_text = self.partial_word
        
        for fake_token, real_value in self.mapping.items():
            if fake_token in remaining_text:
                remaining_text = remaining_text.replace(fake_token, real_value)
                self.names_replaced += 1
        
        self.partial_word = ""
        return remaining_text
    
    def _smart_phone_replacement(self, text: str) -> str:
        """
        Aplica reemplazos inteligentes para teléfonos que pueden venir en diferentes formatos
        """
        import re
        
        # Detectar patrones de teléfono en el texto con mayor precisión
        phone_patterns = [
            r'\(\+\d{1,3}\)\s*\d{3}-\d{3}-\d{3}',  # (+34) 793-914-603
            r'\(\+\d{1,3}-\d{3}-\d{3}-\d{3}\)',    # (+34-677-977-056)
            r'\+\d{1,3}-\d{3}-\d{3}-\d{3}',        # +34-652-433-881
            r'\+\d{1,3}\s+\d{3}\s+\d{3}\s+\d{3}',  # +34 612 345 678
            r'\d{3}\s+\d{3}\s+\d{3}',              # 793 914 603
            r'\d{3}-\d{3}-\d{3}',                  # 793-914-603
            r'\+\d{1,3}\s?\d{6,}',                 # Internacional genérico
        ]
        
        # PATRÓN PELIGROSO COMPLETAMENTE REMOVIDO: r'\d{9}' causa conflictos con IBANs
        # Los patrones de 9 dígitos son demasiado agresivos y confunden partes de IBANs con teléfonos
        # La detección contextual no es suficiente porque el patrón ya asume que es "seguro"
        safe_9_digit_patterns = [
            # PATRÓN REMOVIDO: r'(?<!\d)\d{9}(?!\d)' - Causa conflictos con IBANs
            # Solo mantener patrones con formato específico de teléfono
        ]
        
        # Buscar y reemplazar teléfonos (patrones seguros)
        all_patterns = phone_patterns + safe_9_digit_patterns
        
        for pattern in all_patterns:
            matches = list(re.finditer(pattern, text))
            
            # Procesar coincidencias en orden inverso para no afectar posiciones
            for match in reversed(matches):
                found_phone = match.group()
                
                # VERIFICACIÓN ANTI-CONFLICTO: No procesar dígitos que puedan ser parte de IBAN
                if self._is_part_of_iban_context(text, match.start(), match.end()):
                    logger.debug(f"Skipping phone pattern '{found_phone}' - detected as part of IBAN context")
                    continue
                
                # Normalizar el teléfono encontrado (solo dígitos)
                found_digits = ''.join(filter(str.isdigit, found_phone))
                
                # Buscar en el mapping todos los posibles teléfonos
                best_match = None
                best_replacement = None
                
                for fake_token, real_phone in self.mapping.items():
                    # Normalizar el token del mapping
                    fake_digits = ''.join(filter(str.isdigit, fake_token))
                    
                    # Diferentes niveles de coincidencia
                    if self._phone_digits_match(found_digits, fake_digits):
                        # Si encontramos una coincidencia, usar este replacement
                        best_match = fake_token
                        best_replacement = real_phone
                        break
                
                # Si encontramos una coincidencia, hacer el reemplazo
                if best_match and best_replacement:
                    # Reemplazar en el texto original
                    text = text[:match.start()] + best_replacement + text[match.end():]
                    self.names_replaced += 1
                    logger.debug(f"Smart phone replacement: '{found_phone}' -> '{best_replacement}' (matched digits from '{best_match}')")
        
        return text
    
    def _phone_digits_match(self, found_digits: str, mapping_digits: str) -> bool:
        """
        Verifica si los dígitos de dos teléfonos coinciden usando diferentes estrategias
        """
        if not found_digits or not mapping_digits:
            return False
        
        # 1. Coincidencia exacta de todos los dígitos
        if found_digits == mapping_digits:
            return True
        
        # 2. Coincidencia de los últimos 9 dígitos (números españoles)
        if len(found_digits) >= 9 and len(mapping_digits) >= 9:
            if found_digits[-9:] == mapping_digits[-9:]:
                return True
        
        # 3. Coincidencia de los últimos 7-8 dígitos (casos especiales)
        if len(found_digits) >= 7 and len(mapping_digits) >= 7:
            if found_digits[-7:] == mapping_digits[-7:]:
                return True
        
        # 4. Si uno incluye al otro (para casos como +34 vs sin prefijo)
        if found_digits in mapping_digits or mapping_digits in found_digits:
            return True
        
        return False
    
    def _is_part_of_iban_context(self, text: str, start: int, end: int) -> bool:
        """
        Verifica si una secuencia de dígitos está en contexto de IBAN para evitar conflictos
        """
        import re
        
        # Examinar contexto antes y después (50 caracteres cada lado)
        context_start = max(0, start - 50)
        context_end = min(len(text), end + 50)
        context = text[context_start:context_end]
        
        # Buscar patrones que indican contexto de IBAN
        iban_indicators = [
            r'cuenta\s+bancaria',
            r'número\s+de\s+cuenta',
            r'IBAN',
            r'ES\d{2}[\s\d]+',           # Patrón IBAN español
            r'[A-Z]{2}\d{2}[\s\d]+',     # Patrón IBAN genérico
        ]
        
        for pattern in iban_indicators:
            if re.search(pattern, context, re.IGNORECASE):
                logger.debug(f"IBAN context detected: pattern '{pattern}' in context")
                return True
        
        # Verificar si hay código país de IBAN cerca
        before_context = text[max(0, start - 30):start]
        if re.search(r'ES\s*\d{0,2}[\s\d]*$', before_context):
            logger.debug(f"IBAN prefix detected in before context: '{before_context[-20:]}'")
            return True
        
        return False
    
    def _looks_like_phone_token(self, token: str) -> bool:
        """Verifica si un token parece de teléfono"""
        return '[PHONE_' in token.upper() or '[TEL_' in token.upper()
    
    def _looks_like_phone_value(self, value: str) -> bool:
        """Verifica si un valor parece un teléfono"""
        import re
        # Patrones de teléfono
        phone_regex = r'(\+?\d[\d\s\-()]{6,}\d)'
        digits = ''.join(filter(str.isdigit, value))
        return bool(re.search(phone_regex, value)) and len(digits) >= 7
    
    def flush_remaining(self) -> str:
        """
        Procesa cualquier texto parcial restante al final del streaming
        
        Returns:
            Texto final procesado
        """
        # Procesar tanto el buffer inteligente como el buffer de palabras
        final_text = ""
        
        # Procesar el smart_buffer si tiene contenido
        if self.smart_buffer:
            # Aplicar todos los reemplazos al buffer final
            buffer_text = self.smart_buffer
            
            # Reemplazos exactos
            for fake_token, real_value in self.mapping.items():
                if fake_token in buffer_text:
                    buffer_text = buffer_text.replace(fake_token, real_value)
                    self.names_replaced += 1
                    logger.debug(f"Final replacement: '{fake_token}' -> '{real_value}'")
            
            # Reemplazos inteligentes
            buffer_text = self._smart_complex_replacement(buffer_text)
            
            final_text += buffer_text
            self.smart_buffer = ""
        
        # Procesar el partial_word si tiene contenido (compatibilidad)
        if self.partial_word:
            remaining_text = self.partial_word
            
            # Buscar y reemplazar tokens anonimizados completos
            for fake_token, real_value in self.mapping.items():
                if fake_token in remaining_text:
                    remaining_text = remaining_text.replace(fake_token, real_value)
                    self.names_replaced += 1
                    logger.debug(f"Final partial replacement: '{fake_token}' -> '{real_value}'")
            
            # Aplicar reemplazos inteligentes de teléfonos en el flush final
            remaining_text = self._smart_phone_replacement(remaining_text)
            
            final_text += remaining_text
            self.partial_word = ""
        
        return final_text
    
    def _is_word_separator(self, char: str) -> bool:
        """Verifica si un carácter es separador de palabras"""
        return char.isspace() or char in '.,!?;:()[]{}"\'-/\\|<>=+*&%$#@'
    
    def _can_send_immediately(self, partial: str) -> bool:
        """
        Verifica si el texto parcial puede enviarse inmediatamente
        
        Args:
            partial: Texto parcial acumulado
            
        Returns:
            True si puede enviarse inmediatamente, False si debe esperar
        """
        # Si es muy corto, esperar más caracteres
        if len(partial) < 2:
            return False
        
        # Verificar si es un prefijo de algún token anonimizado
        for fake_token in self.mapping.keys():
            if fake_token.startswith(partial):
                return False  # Es prefijo de un token, esperar más
        
        # No es prefijo de ningún token, puede enviarse inmediatamente
        return True
    
    def _process_complete_word(self, word: str) -> str:
        """
        Procesa una palabra completa aplicando reemplazos
        
        Args:
            word: Palabra completa a procesar
            
        Returns:
            Palabra procesada (original o reemplazada)
        """
        if not word:
            return word
        
        original_word = word
        
        # Buscar reemplazo directo en el mapping
        if word in self.mapping:
            replacement = self.mapping[word]
            self.names_replaced += 1
            logger.debug(f"Direct replacement: '{original_word}' -> '{replacement}'")
            return replacement
        
        # Si no hay reemplazo, devolver palabra original
        return word
    
    def _is_partial_match(self, word: str, fake_token: str, real_value: str) -> bool:
        """
        Verifica si una palabra es una coincidencia parcial válida
        
        Args:
            word: Palabra a verificar
            fake_token: Token falso sin brackets
            real_value: Valor real correspondiente
            
        Returns:
            True si es una coincidencia parcial válida
        """
        word_upper = word.upper()
        token_upper = fake_token.upper()
        
        # Verificar si la palabra coincide con el inicio del token
        if token_upper.startswith(word_upper) and len(word) >= 3:
            return True
        
        # Verificar coincidencias en partes del token (separadas por _)
        token_parts = fake_token.split('_')
        for part in token_parts:
            if part.upper() == word_upper and len(word) >= 3:
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Obtiene estadísticas de procesamiento
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            "words_processed": self.words_processed,
            "names_replaced": self.names_replaced,
            "mappings_available": len(self.mapping),
            "replacement_rate": round(self.names_replaced / max(self.words_processed, 1) * 100, 2)
        }
    
    def reset_stats(self):
        """Reinicia las estadísticas de procesamiento"""
        self.words_processed = 0
        self.names_replaced = 0
    
    def debug_state(self) -> Dict:
        """
        Obtiene el estado actual para debugging
        
        Returns:
            Estado actual del deanonimizador
        """
        return {
            "partial_word": self.partial_word,
            "smart_buffer": self.smart_buffer,
            "smart_buffer_size": len(self.smart_buffer),
            "mapping_count": len(self.mapping),
            "complex_patterns_count": len(self.complex_patterns) if hasattr(self, 'complex_patterns') else 0,
            "name_prefixes_count": len(self.name_prefixes),
            "stats": self.get_stats()
        }


class WordByWordStreamProcessor:
    """
    Procesador de streaming que utiliza WordByWordDeanonymizer
    """
    
    def __init__(self, mapping: Dict[str, str]):
        self.deanonymizer = WordByWordDeanonymizer(mapping)
    
    async def process_stream(self, llm_stream, session_id: str):
        """
        Procesa un stream de LLM aplicando deanonimización palabra por palabra
        
        Args:
            llm_stream: Stream generator del LLM
            session_id: ID de sesión para logging
            
        Yields:
            Chunks procesados con deanonimización
        """
        chunk_count = 0
        total_chars = 0
        
        try:
            async for chunk in llm_stream:
                if chunk:
                    # Procesar chunk palabra por palabra
                    processed_chunk = self.deanonymizer.process_chunk(chunk)
                    
                    if processed_chunk:
                        chunk_count += 1
                        total_chars += len(processed_chunk)
                        
                        # Enviar chunk procesado
                        yield f"data: {processed_chunk}\n\n"
                        
                        # Log cada 50 chunks para debugging
                        if chunk_count % 50 == 0:
                            stats = self.deanonymizer.get_stats()
                            logger.debug(f"Session {session_id}: Processed {chunk_count} chunks, "
                                       f"{total_chars} chars, {stats['names_replaced']} replacements")
            
            # Procesar cualquier palabra parcial restante
            remaining = self.deanonymizer.flush_remaining()
            if remaining:
                yield f"data: {remaining}\n\n"
            
            # Log final
            final_stats = self.deanonymizer.get_stats()
            logger.info(f"Session {session_id} completed: {final_stats}")
            
        except Exception as e:
            logger.error(f"Error in word-by-word streaming for session {session_id}: {e}")
            raise