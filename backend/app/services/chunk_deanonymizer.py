"""
Chunked Deanonymization Helper - VERSIÓN OPTIMIZADA CON EMAIL-AWARE PROCESSING
Maneja la deanonymización precisa de chunks fragmentados del LLM
Balanceado para streaming fluido manteniendo precisión en reemplazos
VERSIÓN MEJORADA: Email-aware processin        # Crear múltiples patrone        # Crear múltiples patrones para el mismo teléfono (espacios y guiones)
        normalized_with_dashes = self._normalize_phone_format(phone)
        phone_variants = [
            re.escape(phone),                                    # Original
            re.escape(normalized_phone),                         # Normalizado espacios
            re.escape(normalized_with_dashes),                   # Normalizado guiones
            re.escape(phone.replace(' ', '')),                   # Sin espacios
            re.escape(phone.replace(' ', '  ')),                 # Espacios dobles
            re.escape(phone.replace(' ', '-')),                  # Convertido a guiones
        ]el mismo teléfono (espacios y guiones)
        normalized_with_dashes = self._normalize_phone_format(phone)
        phone_variants = [
            re.escape(phone),                                    # Original
            re.escape(normalized_phone),                         # Normalizado espacios
            re.escape(normalized_with_dashes),                   # Normalizado guiones
            re.escape(phone.replace(' ', '')),                   # Sin espacios
            re.escape(phone.replace(' ', '  ')),                 # Espacios dobles
            re.escape(phone.replace(' ', '-')),                  # Convertido a guiones
        ]evitar corrupción de datos
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ChunkDeanonymizer:
    """
    Deanonymización BALANCEADA para streaming fluido.
    Prioriza streaming fluido manteniendo precisión en reemplazos.
    VERSIÓN MEJORADA: Email-aware processing para evitar fragmentación
    """
    
    def __init__(self, reverse_map: Dict[str, str]):
        self.reverse_map = reverse_map
        self.input_buffer = ""
        self.last_sent_pos = 0
        
        # ⭐ NUEVO: Flag para tracking de retención
        self.was_retaining = False
        
        # Separar entidades por tipo para tratamiento específico
        self.email_entities = {}      # Emails (requieren procesamiento especial)
        self.phone_entities = {}      # Teléfonos (requieren procesamiento especial)
        self.simple_entities = {}     # Palabras simples
        self.complex_entities = {}    # Nombres multi-palabra largos
        
        for fake, real in reverse_map.items():
            if '@' in fake:  # ⭐ DETECTAR EMAILS
                self.email_entities[fake] = real
            elif self._is_phone_number(fake):  # ⭐ DETECCIÓN MEJORADA DE TELÉFONOS
                self.phone_entities[fake] = real
            elif ' ' in fake and len(fake.split()) >= 3:
                self.complex_entities[fake] = real
            else:
                self.simple_entities[fake] = real
                
        logger.info(f"🔧 Emails: {len(self.email_entities)}, Phones: {len(self.phone_entities)}, Simple: {len(self.simple_entities)}, Complex: {len(self.complex_entities)}")
        
        # ⭐ LOGGING DETALLADO DEL MAPPING PARA DEBUGGING
        logger.debug(f"🔍 MAPPING DETALLADO:")
        for fake, real in reverse_map.items():
            entity_type = "EMAIL" if '@' in fake else "PHONE" if self._is_phone_number(fake) else "SIMPLE" if ' ' not in fake else "COMPLEX"
            logger.debug(f"  [{entity_type}] '{fake}' -> '{real}'")
        
    def process_chunk(self, chunk: str) -> Tuple[str, str]:
        """
        Versión STREAMING-FRIENDLY con procesamiento email-aware.
        ⭐ NUEVO: Detección simple de fragmentos de palabras
        
        Args:
            chunk: Fragmento de texto del LLM
            
        Returns:
            Tuple[anonymous_output, deanonymized_output]: Texto para cada stream
        """
        # Acumular chunk
        self.input_buffer += chunk
        # ✅ SIEMPRE devolver el chunk original para el stream anonimizado
        anonymous_output = chunk
        
        # ⭐ NUEVO: Verificar si debemos retener por fragmentación de palabras
        should_retain = self._should_retain_for_word_completion()
        
        # ⭐ NUEVO: Detectar transición de retención
        just_stopped_retaining = self.was_retaining and not should_retain
        
        # ⭐ Actualizar estado de retención
        self.was_retaining = should_retain
        
        if should_retain:
            logger.debug(f"🔄 Retaining chunk - potential word fragmentation detected")
            return anonymous_output, ""
        
        # ⭐ Si acabamos de salir de retención, usar procesamiento comprehensivo
        if just_stopped_retaining:
            logger.debug(f"🎯 Just stopped retaining - using comprehensive processing")
            deanonymized_output = self._process_after_retention()
            return anonymous_output, deanonymized_output
        
        # ESTRATEGIA BALANCEADA: Procesar según tipo de contenido
        
        # 1. Si el chunk termina con separador claro, procesar inmediatamente
        if chunk.endswith(('.', '!', '?', '\n', '. ', '.\n')):
            deanonymized_output = self._process_complete_sentence()
            return anonymous_output, deanonymized_output
        
        # 2. Si hay suficiente contenido, procesar parcialmente
        if len(self.input_buffer) >= 100:  # Reducido de filtros ultra-conservadores
            deanonymized_output = self._process_partial_content()
            return anonymous_output, deanonymized_output
        
        # 3. Solo para chunks muy pequeños, ser conservador
        return anonymous_output, ""
    
    def _process_complete_sentence(self) -> str:
        """Procesa cuando detecta fin de oración - SOLO retorna deanonymized"""
        
        # Deanonymizar todo el buffer usando procesamiento comprehensivo
        deanonymized_buffer = self._comprehensive_deanonymize(self.input_buffer)
        
        # Calcular contenido nuevo desde la última posición enviada
        new_content = deanonymized_buffer[self.last_sent_pos:]
        
        # Solo enviar si hay contenido nuevo significativo
        if new_content.strip():
            # Actualizar posición al final del contenido deanonimizado
            self.last_sent_pos += len(new_content)
            
            logger.debug(f"📝 Complete sentence - sending: '{new_content[:50]}...' (pos: {self.last_sent_pos})")
            return new_content
        
        logger.debug("📝 Complete sentence - no new content to send")
        return ""
    
    def _process_after_retention(self) -> str:
        """
        ⭐ NUEVO: Procesa después de salir de retención con deanonymización completa segura
        """
        # Deanonymizar todo el buffer
        deanonymized_buffer = self._comprehensive_deanonymize(self.input_buffer)
        
        # Calcular contenido nuevo desde la última posición
        new_content = deanonymized_buffer[self.last_sent_pos:]
        
        # Solo enviar si hay contenido nuevo significativo
        if new_content.strip():
            # ⭐ CLAVE: Actualizar posición basada en la longitud del contenido deanonimizado enviado
            self.last_sent_pos += len(new_content)
            
            logger.debug(f"🎯 After retention - sending: '{new_content[:50]}...' (pos updated to: {self.last_sent_pos})")
            return new_content
        
        logger.debug("🎯 After retention - no new content to send")
        return ""
    
    def _process_partial_content(self) -> str:
        """DESHABILITADO: Para evitar fragmentación, solo procesamos en puntos seguros"""
        # No procesar contenido parcial para evitar fragmentación
        return ""
    
    def _comprehensive_deanonymize(self, text: str) -> str:
        """Deanonymización COMPLETA para oraciones terminadas con ORDEN OPTIMIZADO"""
        result = text
        
        # ⭐ NUEVO: APLICAR REEMPLAZOS EN ORDEN DE PRIORIDAD PARA EVITAR FRAGMENTACIÓN
        
        # PASO 1: Reemplazar TELÉFONOS primero (más específicos y problemáticos)
        # Ordenar por longitud descendente para aplicar números completos antes que fragmentos
        sorted_phones = sorted(self.phone_entities.items(), key=lambda x: len(x[0]), reverse=True)
        for fake_phone, real_phone in sorted_phones:
            result = self._smart_phone_replacement(result, fake_phone, real_phone)
        
        # PASO 2: Reemplazar EMAILS (también específicos)
        for fake_email, real_email in self.email_entities.items():
            if fake_email in result:
                # ⭐ VALIDACIÓN ESPECÍFICA PARA EMAILS
                if self._is_complete_email(result, fake_email):
                    result = result.replace(fake_email, real_email)
                    logger.debug(f"✅ Email replacement: '{fake_email}' -> '{real_email}'")
        
        # PASO 3: Reemplazar entidades COMPLEJAS (nombres largos)
        # Ordenar por longitud descendente para evitar reemplazos parciales
        sorted_complex = sorted(self.complex_entities.items(), key=lambda x: len(x[0]), reverse=True)
        for fake, real in sorted_complex:
            if fake in result:
                if self._is_complete_complex_entity(result, fake):
                    result = result.replace(fake, real)
                    logger.debug(f"✅ Complex replacement: '{fake}' -> '{real}'")
        
        # PASO 4: Reemplazar entidades SIMPLES al final
        # ⭐ FILTRAR entidades simples que podrían ser fragmentos de teléfonos
        filtered_simple = self._filter_phone_fragments(self.simple_entities, text)
        sorted_simple = sorted(filtered_simple.items(), key=lambda x: len(x[0]), reverse=True)
        
        for fake, real in sorted_simple:
            if fake in result:
                if self._is_safe_simple_replacement(result, fake):
                    result = result.replace(fake, real)
                    logger.debug(f"✅ Simple replacement: '{fake}' -> '{real}'")
        
        return result
    
    def _safe_partial_deanonymize(self, text: str) -> str:
        """Deanonymización SEGURA para contenido parcial (evita corromper emails)"""
        result = text
        
        # Para contenido parcial, SOLO reemplazar entidades que están COMPLETAS
        
        # PASO 1: Solo reemplazar emails que están 100% completos
        for fake_email, real_email in self.email_entities.items():
            if fake_email in result and self._is_complete_email(result, fake_email):
                result = result.replace(fake_email, real_email)
                logger.debug(f"✅ Safe email replacement: '{fake_email}' -> '{real_email}'")
        
        # PASO 2: Solo nombres simples que no pueden fragmentarse
        for fake, real in self.simple_entities.items():
            if fake in result and self._is_safe_simple_replacement(result, fake):
                result = result.replace(fake, real)
                logger.debug(f"✅ Safe simple replacement: '{fake}' -> '{real}'")
        
        return result

    def _quick_deanonymize(self, text: str) -> str:
        """Deanonymización rápida priorizando streaming"""
        result = text
        
        # PASO 1: Reemplazar entidades simples (rápido y seguro)
        for fake, real in self.simple_entities.items():
            if fake in result:
                # Validación básica pero no ultra-restrictiva
                if self._is_safe_simple_replacement(result, fake):
                    result = result.replace(fake, real)
                    logger.debug(f"✅ Simple replacement: '{fake}' -> '{real}'")
        
        # PASO 2: Reemplazar entidades complejas solo si están completas
        for fake, real in self.complex_entities.items():
            if fake in result:
                # Solo para entidades complejas, validación más estricta
                if self._is_complete_complex_entity(result, fake):
                    result = result.replace(fake, real)
                    logger.debug(f"✅ Complex replacement: '{fake}' -> '{real}'")
        
        return result
    
    def _is_phone_number(self, text: str) -> bool:
        """⭐ NUEVA: Detección mejorada de números de teléfono"""
        # Detectar patrones de teléfono comunes
        phone_patterns = [
            r'\+\d{1,3}\s?\d{3}\s?\d{3}\s?\d{3}',  # +34 612 345 678
            r'\+\d{10,15}',                        # +34612345678
            r'\d{9,15}',                           # 612345678
            r'\(\+\d{1,3}\)\s?\d+',                # (+34) 612345678
        ]
        
        for pattern in phone_patterns:
            if re.search(pattern, text):
                return True
        
        # Fallback: contiene dígitos y símbolos típicos de teléfono
        return (any(char.isdigit() for char in text) and 
                ('+' in text or len(text) >= 9) and
                ('-' in text or ' ' in text or text.isdigit()) and  # Acepta guiones, espacios o solo dígitos
                len(text) <= 25)  # Límite aumentado para formato con guiones

    def _normalize_phone_format(self, phone: str) -> str:
        """⭐ MEJORADO: Normaliza teléfonos entre todos los formatos posibles"""
        import re
        
        # Convertir espacios a guiones: +34 612 345 678 → +34-612-345-678
        if ' ' in phone and not '(' in phone:
            # Patrón para teléfonos con espacios
            match = re.match(r'(\+\d{1,3})\s+(\d{3})\s+(\d{3})\s+(\d{3})', phone)
            if match:
                country, part1, part2, part3 = match.groups()
                return f"{country}-{part1}-{part2}-{part3}"
        
        # Convertir guiones a espacios: +34-612-345-678 → +34 612 345 678
        elif '-' in phone and not '(' in phone:
            # Patrón para teléfonos con guiones
            match = re.match(r'(\+\d{1,3})-(\d{3})-(\d{3})-(\d{3})', phone)
            if match:
                country, part1, part2, part3 = match.groups()
                return f"{country} {part1} {part2} {part3}"
        
        # ⭐ NUEVO: Convertir paréntesis: (+34) 680-449-032 → +34 680 449 032
        elif '(' in phone:
            # Patrón para teléfonos con paréntesis
            match = re.match(r'\((\+\d{1,3})\)\s?(\d{3})-(\d{3})-(\d{3})', phone)
            if match:
                country, part1, part2, part3 = match.groups()
                return f"{country} {part1} {part2} {part3}"  # Convertir a formato con espacios
        
        # Si no coincide con patrones conocidos, devolver original
        return phone

    def _smart_phone_replacement(self, text: str, fake_phone: str, real_phone: str) -> str:
        """⭐ MEJORADO: Reemplazo inteligente con conversión de formatos espacios/guiones"""
        
        # 1. Intentar reemplazo directo primero (formato original)
        if fake_phone in text and self._is_complete_phone(text, fake_phone):
            result = text.replace(fake_phone, real_phone)
            logger.debug(f"✅ Direct phone replacement: '{fake_phone}' -> '{real_phone}'")
            return result
        
        # 2. ⭐ NUEVO: Intentar con formato normalizado (espacios ↔ guiones)
        fake_normalized = self._normalize_phone_format(fake_phone)
        real_normalized = self._normalize_phone_format(real_phone)
        
        if fake_normalized != fake_phone and fake_normalized in text:
            result = text.replace(fake_normalized, real_normalized)
            logger.debug(f"✅ Normalized phone replacement: '{fake_normalized}' -> '{real_normalized}'")
            return result
        
        # 3. Buscar variantes con diferentes separadores
        fake_digits_only = re.sub(r'[^\d+]', '', fake_phone)
        
        # Buscar patrones con espacios, guiones O paréntesis
        patterns = [
            r'(\+?\d{1,3})\s+(\d{3})\s+(\d{3})\s+(\d{3})',    # Espacios
            r'(\+?\d{1,3})-(\d{3})-(\d{3})-(\d{3})',          # Guiones
            r'\((\+\d{1,3})\)\s?(\d{3})-(\d{3})-(\d{3})',     # Paréntesis con guiones
        ]
        
        for pattern in patterns:
            def phone_replacer(match):
                matched_phone = match.group(0)
                matched_digits = re.sub(r'[^\d+]', '', matched_phone)
                
                if matched_digits == fake_digits_only:
                    # Usar el formato del teléfono real para el reemplazo
                    logger.debug(f"✅ Pattern phone replacement: '{matched_phone}' -> '{real_phone}'")
                    return real_phone
                return matched_phone
            
            result = re.sub(pattern, phone_replacer, text)
            if result != text:  # Si hubo cambios, devolver resultado
                return result
        
        return text

    def _is_complete_email(self, text: str, email: str) -> bool:
        """Validación ESTRICTA para emails completos"""
        # ⭐ PATRÓN ESPECÍFICO PARA EMAILS
        escaped_email = re.escape(email)
        # El email debe estar rodeado por espacios, inicio/fin de línea, o signos de puntuación
        pattern = r'(?:^|[\s\(])' + escaped_email + r'(?:[\s\.,\)\?!:]|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            logger.debug(f"🔍 Email '{email}' found as complete entity in: '{text[max(0, match.start()-10):match.end()+10]}'")
            return True
        return False
    
    def _is_complete_phone(self, text: str, phone: str) -> bool:
        """⭐ VALIDACIÓN MEJORADA para teléfonos completos con espacios flexibles"""
        
        # Normalizar el teléfono para comparación (remover espacios extra)
        normalized_phone = re.sub(r'\s+', ' ', phone.strip())
        
        # Crear múltiples patrones para el mismo teléfono
        phone_variants = [
            re.escape(phone),                                    # Formato original
            re.escape(normalized_phone),                         # Formato normalizado
            re.escape(phone.replace(' ', '')),                   # Sin espacios
            re.escape(phone.replace(' ', '  ')),                 # Espacios dobles
        ]
        
        for variant in phone_variants:
            # El teléfono debe estar rodeado por espacios, inicio/fin de línea, o signos de puntuación
            pattern = r'(?:^|[\s\(])' + variant + r'(?:[\s\.,\)\?!:]|$)'
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"🔍 Phone '{phone}' found as complete entity (variant: '{variant}')")
                return True
        
        # Patrón flexible para teléfonos con espacios variables
        flexible_pattern = re.escape(phone).replace(r'\ ', r'\s*')
        pattern = r'(?:^|[\s\(])' + flexible_pattern + r'(?:[\s\.,\)\?!:]|$)'
        if re.search(pattern, text, re.IGNORECASE):
            logger.debug(f"🔍 Phone '{phone}' found with flexible spacing")
            return True
        
        return False

    def _is_safe_simple_replacement(self, text: str, entity: str) -> bool:
        """Validación relajada para entidades simples (ya no incluye emails/teléfonos)"""
        
        # Para palabras simples - verificar límites de palabra básicos
        pattern = r'\b' + re.escape(entity) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _is_complete_complex_entity(self, text: str, entity: str) -> bool:
        """Validación estricta solo para entidades complejas (nombres largos)"""
        
        # Solo aplicar ultra-conservadurismo a nombres muy largos
        if len(entity.split()) >= 3:
            escaped = re.escape(entity)
            pattern = r'(?:^|\s)' + escaped + r'(?:\s|$|[,.!?;])'
            return bool(re.search(pattern, text, re.IGNORECASE))
        
        return True  # Para entidades no tan complejas, ser permisivo
    
    def _filter_phone_fragments(self, simple_entities: Dict[str, str], original_text: str) -> Dict[str, str]:
        """⭐ NUEVA: Filtra entidades simples que podrían ser fragmentos de teléfonos"""
        filtered = {}
        
        # Obtener todos los números de teléfono completos detectados
        phone_numbers = set()
        for phone_fake in self.phone_entities.keys():
            phone_numbers.add(phone_fake)
        
        # También buscar números de teléfono en el texto original
        # Para detectar posibles fragmentos (espacios, guiones y paréntesis)
        import re
        phone_patterns = [
            r'\+\d{1,3}\s?\d{3}\s?\d{3}\s?\d{3}',    # +34 612 345 678 (espacios)
            r'\+\d{1,3}-\d{3}-\d{3}-\d{3}',           # +34-612-345-678 (guiones)
            r'\(\+\d{1,3}\)\s?\d{3}-\d{3}-\d{3}',     # (+34) 680-449-032 (paréntesis)
            r'\d{3}\s?\d{3}\s?\d{3}',                # 612 345 678 (espacios)
            r'\d{3}-\d{3}-\d{3}',                     # 612-345-678 (guiones)
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, original_text)
            phone_numbers.update(matches)
        
        # Filtrar entidades simples que NO sean fragmentos de teléfonos
        for fake, real in simple_entities.items():
            is_phone_fragment = False
            
            # Verificar si esta entidad simple es parte de algún teléfono
            for phone in phone_numbers:
                if fake in phone and fake != phone:
                    is_phone_fragment = True
                    logger.debug(f"🚫 Filtering phone fragment: '{fake}' (part of phone '{phone}')")
                    break
            
            # También verificar si parece un fragmento de número
            if re.match(r'^\d{3}\s?\d{3}$', fake) or re.match(r'^\d{3}$', fake):
                is_phone_fragment = True
                logger.debug(f"🚫 Filtering potential phone fragment: '{fake}' (matches phone pattern)")
            
            if not is_phone_fragment:
                filtered[fake] = real
            
        logger.debug(f"📊 Filtered {len(simple_entities) - len(filtered)} phone fragments from simple entities")
        return filtered
    
    def finalize(self) -> Tuple[str, str]:
        """Envía todo el contenido restante al final"""
        final_deanonymized = self._comprehensive_deanonymize(self.input_buffer)
        remaining = final_deanonymized[self.last_sent_pos:]
        
        logger.info(f"🏁 Finalizing - sending remaining: '{remaining[:100]}...'")
        return "", remaining
    
    def _should_retain_for_word_completion(self) -> bool:
        """
        ⭐ NUEVO: Verificar si debemos retener el chunk porque el final del buffer
        podría ser el inicio de alguna palabra del mapping.
        """
        
        # Obtener las últimas 50 caracteres del buffer para analizar
        text_to_analyze = self.input_buffer[-50:]
        
        # Verificar contra todas las palabras del mapping
        all_mapping_words = list(self.reverse_map.keys())
        
        for mapping_word in all_mapping_words:
            # Verificar si el final del buffer es un prefijo de esta palabra del mapping
            if self._is_partial_match_at_end(text_to_analyze, mapping_word):
                logger.debug(f"🎯 Potential fragment detected: buffer ends with start of '{mapping_word}'")
                return True
        
        return False
    
    def _word_just_completed(self) -> bool:
        """
        ⭐ NUEVO: Verificar si acabamos de completar una palabra del mapping
        """
        
        # Obtener las últimas palabras del buffer para analizar
        text_to_analyze = self.input_buffer[-100:]
        
        # Verificar si alguna palabra del mapping está ahora completa al final
        all_mapping_words = list(self.reverse_map.keys())
        
        for mapping_word in all_mapping_words:
            # Verificar si la palabra completa está presente
            if mapping_word in text_to_analyze:
                # Verificar que termina al final del buffer (no en el medio)
                words_at_end = text_to_analyze.split()[-len(mapping_word.split()):]
                reconstructed = ' '.join(words_at_end)
                
                if reconstructed == mapping_word:
                    logger.debug(f"✅ Word just completed: '{mapping_word}'")
                    return True
        
        return False
    
    def _is_partial_match_at_end(self, text: str, target_word: str) -> bool:
        """
        Verificar si el final del texto es un prefijo parcial de target_word.
        
        Ejemplos:
        - text="completo:** Leó", target_word="León Sancho-Miranda" → True
        - text="Hola Juan", target_word="Juan García" → True  
        - text="Hola mundo", target_word="León Sancho-Miranda" → False
        """
        
        # Extraer palabras del final del texto (hasta 4 palabras)
        words_in_text = text.split()[-4:]  # Últimas 4 palabras
        
        if not words_in_text:
            return False
        
        # Probar diferentes combinaciones de palabras del final
        for i in range(len(words_in_text)):
            partial_text = ' '.join(words_in_text[i:])
            
            # Verificar si esta parte del texto es un prefijo de target_word
            if target_word.startswith(partial_text):
                # Asegurarse de que no es la palabra completa (eso no es fragmentación)
                if partial_text != target_word:
                    # Añadir verificación adicional para reducir falsos positivos
                    # Solo considerar fragmentación si el prefijo es sustancial
                    if len(partial_text) >= 2:  # Al menos 2 caracteres
                        logger.debug(f"✅ Fragment match: '{partial_text}' is prefix of '{target_word}'")
                        return True
        
        return False
