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
        self.mapping = mapping or {}
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
        
        logger.info(f"WordByWordDeanonymizer initialized with {len(self.mapping)} mappings")
    
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
        
        Returns:
            Tuple[str, str]: (texto_seguro_para_enviar, texto_a_mantener_en_buffer)
        """
        # Estrategia conservadora: enviar todo excepto los últimos N caracteres
        # que podrían ser parte de un patrón incompleto
        
        safety_margin = 50  # Mantener los últimos 50 caracteres en buffer
        
        if len(processed_text) <= safety_margin:
            # Si el texto es muy corto, mantener todo en buffer
            return "", processed_text
        
        # Buscar un punto de corte seguro (espacios, puntos, etc.)
        safe_cutoff = len(processed_text) - safety_margin
        
        # Buscar hacia atrás un punto de corte natural
        for i in range(safe_cutoff, max(0, safe_cutoff - 20), -1):
            if processed_text[i] in ' \n\t.,;:':
                safe_to_send = processed_text[:i + 1]
                keep_in_buffer = processed_text[i + 1:]
                return safe_to_send, keep_in_buffer
        
        # Si no encontramos un punto natural, usar el margen de seguridad
        safe_to_send = processed_text[:safe_cutoff]
        keep_in_buffer = processed_text[safe_cutoff:]
        
        return safe_to_send, keep_in_buffer
    
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
            r'\d{9}',                              # 793914603 (sin espacios)
            r'\+\d{1,3}\s?\d{6,}',                 # Internacional genérico
        ]
        
        # Buscar y reemplazar teléfonos
        for pattern in phone_patterns:
            matches = list(re.finditer(pattern, text))
            
            # Procesar coincidencias en orden inverso para no afectar posiciones
            for match in reversed(matches):
                found_phone = match.group()
                
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