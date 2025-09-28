"""
Chunked Deanonymization Helper - VERSIÓN CORREGIDA
Maneja la deanonymización precisa de chunks fragmentados del LLM
Evita reemplazos incorrectos usando coincidencias exactas validadas
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ChunkDeanonymizer:
    """
    Deanonymización inteligente y CONSERVADORA de chunks fragmentados.
    Prioriza precisión sobre velocidad para evitar reemplazos incorrectos.
    """
    
    def __init__(self, reverse_map: Dict[str, str]):
        self.reverse_map = reverse_map
        self.input_buffer = ""  # Texto acumulado del LLM
        self.last_sent_pos = 0   # Posición hasta donde hemos enviado
        
        # Identificar entidades largas que requieren cuidado extra
        self.long_entities = [entity for entity in reverse_map.keys() 
                             if ' ' in entity and len(entity.split()) >= 3]
        logger.debug(f"🔒 Long entities requiring extra care: {self.long_entities}")
        
    def process_chunk(self, chunk: str) -> Tuple[str, str]:
        """
        Procesa un chunk con MÁXIMA PROTECCIÓN para nombres largos.
        
        Args:
            chunk: Fragmento de texto del LLM
            
        Returns:
            Tuple[anonymous_output, deanonymized_output]: Texto para cada stream
        """
        # Acumular chunk en el buffer
        self.input_buffer += chunk
        
        # Output anónimo siempre es el chunk original
        anonymous_output = chunk
        
        # Procesar buffer completo con validación estricta
        full_deanonymized = self._safe_deanonymize_buffer()
        
        # ESTRATEGIA ULTRA-CONSERVADORA: No enviar NADA si hay entidades largas pendientes
        might_be_inside_entity = self._might_be_inside_long_entity(self.input_buffer)
        
        if might_be_inside_entity:
            # Si hay riesgo de entidad larga, NO ENVIAR NADA hasta completar
            logger.debug(f"🔒 HOLDING OUTPUT - Possible long entity in progress")
            return anonymous_output, ""
        
        # Solo si NO hay riesgo, calcular contenido para enviar
        new_content = full_deanonymized[self.last_sent_pos:]
        
        # Aplicar filtros de estabilidad muy conservadores
        stable_content = self._get_stable_content(new_content)
        
        # Verificación adicional: no enviar si detectamos posibles fragmentos de entidades
        if stable_content and self._contains_possible_entity_fragment(stable_content):
            logger.debug(f"🔒 BLOCKING FRAGMENT - Possible entity fragment detected")
            return anonymous_output, ""
        
        if stable_content:
            self.last_sent_pos += len(stable_content)
        
        # Debug logging
        logger.debug(f"📝 Chunk in: {repr(chunk)}")
        logger.debug(f"📦 Buffer: {repr(self.input_buffer[:100])}")
        logger.debug(f"📤 Deanon out: {repr(stable_content)}")
        
        return anonymous_output, stable_content
    
    def _safe_deanonymize_buffer(self) -> str:
        """
        Deanonymiza usando SOLO coincidencias exactas y VALIDADAS.
        Evita fragmentaciones y reemplazos parciales incorrectos.
        """
        result = self.input_buffer
        replacements_made = []
        
        # Procesar entidades por orden de longitud (más largas primero)
        sorted_entities = sorted(self.reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        logger.debug(f"🔍 Processing buffer: {repr(result[:200])}")
        logger.debug(f"🗺️ Entities available: {list(self.reverse_map.keys())}")
        
        # ESTRATEGIA 1: COINCIDENCIAS EXACTAS COMPLETAS Y VALIDADAS
        for fake_entity, real_entity in sorted_entities:
            if fake_entity in result:
                # Validar que es una coincidencia segura (no fragmento de algo más grande)
                if self._is_complete_entity_match(result, fake_entity):
                    result = result.replace(fake_entity, real_entity)
                    replacements_made.append(f"'{fake_entity}' -> '{real_entity}'")
                    logger.info(f"🎯 EXACT REPLACEMENT: '{fake_entity}' -> '{real_entity}'")
        
        # ESTRATEGIA 2: REEMPLAZOS DE FRAGMENTOS LARGOS (para nombres multi-palabra)
        # Solo si no se hizo ningún reemplazo exacto
        if not replacements_made:
            for fake_entity, real_entity in sorted_entities:
                if ' ' in fake_entity and len(fake_entity.split()) >= 3:  # Solo nombres largos
                    fake_words = fake_entity.split()
                    
                    # Buscar fragmentos de 2+ palabras consecutivas del nombre original
                    for i in range(len(fake_words) - 1):
                        for j in range(i + 2, len(fake_words) + 1):
                            fragment = ' '.join(fake_words[i:j])
                            
                            if len(fragment) >= 10 and fragment in result:  # Solo fragmentos largos
                                if self._is_complete_entity_match(result, fragment):
                                    result = result.replace(fragment, real_entity)
                                    replacements_made.append(f"'{fragment}' -> '{real_entity}' (fragment)")
                                    logger.info(f"🔧 FRAGMENT REPLACEMENT: '{fragment}' -> '{real_entity}'")
                                    break
                        if replacements_made:
                            break
                else:
                    logger.debug(f"❌ FRAGMENT DETECTED - Skipping unsafe replacement for '{fake_entity}'")
        
        if replacements_made:
            logger.debug(f"✅ Safe replacements: {replacements_made}")
        else:
            logger.debug("⚠️ No complete entities found for replacement")
        
        return result
    
    def _is_complete_entity_match(self, text: str, entity: str) -> bool:
        """
        Valida que una entidad aparece como elemento completo, no como fragmento.
        VERSIÓN ULTRA-CONSERVADORA para evitar reemplazos parciales.
        
        Args:
            text: Texto completo donde buscar
            entity: Entidad a validar
            
        Returns:
            bool: True si es una entidad completa y segura de reemplazar
        """
        # Escapar caracteres especiales para regex
        escaped_entity = re.escape(entity)
        
        # VALIDACIÓN ULTRA-ESTRICTA: Solo permitir reemplazos con separadores claros
        # Para nombres largos multi-palabra, ser extra cuidadoso
        if ' ' in entity and len(entity.split()) >= 3:
            # Nombres largos (3+ palabras): Requieren separadores muy específicos
            pattern = r'(?:^|\s|\n)' + escaped_entity + r'(?:\s|\n|$|[,.!?;:\)])'
        elif '@' in entity:
            # Emails: deben estar rodeados de espacios o límites claros
            pattern = r'(?:^|\s|\n)' + escaped_entity + r'(?:\s|\n|$|[,.!?;:\)])'
        elif '_' in entity or '-' in entity:
            # Entidades con separadores: rodeadas de espacios o límites claros
            pattern = r'(?:^|\s|\n)' + escaped_entity + r'(?:\s|\n|$|[,.!?;:\)])'
        elif entity.isdigit() and len(entity) >= 3:
            # Números largos: límites de palabra muy estrictos
            pattern = r'(?:^|\s|\n)' + escaped_entity + r'(?:\s|\n|$|[,.!?;:\)])'
        elif ' ' in entity:
            # Nombres multi-palabra normales: límites de palabra estrictos
            pattern = r'(?:^|\s|\n)' + escaped_entity + r'(?:\s|\n|$|[,.!?;:\)])'
        else:
            # Palabras simples: límites de palabra muy estrictos
            pattern = r'(?:^|\s|\n)' + escaped_entity + r'(?:\s|\n|$|[,.!?;:\)])'
        
        # Buscar coincidencia con el patrón
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            logger.debug(f"✅ ULTRA-CONSERVATIVE MATCH: '{entity}' found safely with pattern: {pattern}")
            return True
        else:
            logger.debug(f"❌ ULTRA-CONSERVATIVE REJECTION: '{entity}' not found with safe boundaries")
            return False
    
    def _get_stable_content(self, new_content: str) -> str:
        """
        Retorna solo contenido "estable" para evitar enviar palabras cortadas.
        VERSIÓN ULTRA-CONSERVADORA para nombres largos.
        """
        if not new_content:
            return ""
            
        # Si termina con separador claro, enviar todo
        if new_content.endswith((' ', '.', ',', '!', '?', '\n', '\t', ':', ';', ')')):
            return new_content
            
        # Si muy corto, esperar más contenido
        if len(new_content.strip()) < 5:  # Aumentado de 3 a 5 para ser más conservador
            return ""
            
        # Para nombres largos, ser extra cuidadoso
        # Enviar solo si hay múltiples palabras Y terminan con separador claro
        words = new_content.split()
        
        # Si solo hay 1-2 palabras, esperar más contenido para evitar cortar nombres
        if len(words) <= 2:
            return ""
            
        # Si hay 3+ palabras, enviar todas excepto las últimas 2 (más conservador)
        if len(words) >= 4:
            return ' '.join(words[:-2]) + ' '
        elif len(words) == 3:
            # Con 3 palabras, enviar solo la primera para evitar cortar nombres largos
            return words[0] + ' '
        else:
            return ""
    
    def finalize(self) -> Tuple[str, str]:
        """
        Finaliza procesamiento enviando todo el contenido restante.
        """
        final_deanonymized = self._safe_deanonymize_buffer()
        remaining_content = final_deanonymized[self.last_sent_pos:]
        
        logger.debug(f"🏁 Finalizing with remaining content: {repr(remaining_content)}")
        
        return "", remaining_content
    
    def _might_be_inside_long_entity(self, text: str) -> bool:
        """
        Detecta si el texto actual podría estar en medio de una entidad larga.
        Esto ayuda a evitar reemplazos prematuros de nombres largos.
        """
        # Verificar si algún fragmento del final del texto podría ser parte de una entidad larga
        text_end = text[-50:] if len(text) > 50 else text  # Solo los últimos 50 chars
        
        for entity in self.long_entities:
            entity_words = entity.split()
            
            # Verificar si alguna parte del final del texto coincide con el inicio de la entidad
            for i in range(1, len(entity_words)):
                partial_entity = ' '.join(entity_words[:i])
                if text_end.endswith(partial_entity) or partial_entity in text_end[-len(partial_entity)-5:]:
                    logger.debug(f"⚠️ Possible partial match for long entity '{entity}': found '{partial_entity}'")
                    return True
                    
        return False
    
    def _contains_possible_entity_fragment(self, content: str) -> bool:
        """
        Verifica si el contenido a enviar podría contener fragmentos de entidades.
        """
        content_lower = content.lower()
        
        for entity in self.reverse_map.keys():
            entity_lower = entity.lower()
            entity_words = entity_lower.split()
            
            # Verificar si alguna palabra del contenido podría ser parte de una entidad
            for word in content.split():
                word_lower = word.strip('.,!?;:').lower()
                
                # Si la palabra es parte de alguna entidad, podría ser un fragmento
                for entity_word in entity_words:
                    if (word_lower in entity_word or entity_word in word_lower) and len(word_lower) >= 3:
                        logger.debug(f"🚨 Fragment risk: '{word}' might be part of '{entity}'")
                        return True
        
        return False