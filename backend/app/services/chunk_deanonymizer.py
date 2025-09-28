"""
Chunked Deanonymization Helper
Maneja la deanonymización de chunks fragmentados del LLM
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ChunkDeanonymizer:
    """
    Maneja la deanonymización de chunks fragmentados en tiempo real.
    Estrategia mejorada: acumula más contenido antes de procesar para evitar fragmentación.
    """
    
    def __init__(self, reverse_map: Dict[str, str]):
        self.reverse_map = reverse_map
        self.input_buffer = ""  # Todo el texto recibido
        self.output_buffer = ""  # Todo el texto procesado
        self.last_sent_pos = 0   # Posición hasta donde hemos enviado texto
        
    def process_chunk(self, chunk: str) -> Tuple[str, str]:
        """
        Procesa un chunk con estrategia de buffer mejorada.
        
        Args:
            chunk: Fragmento de texto del LLM
            
        Returns:
            Tuple[anonymous_output, deanonymized_output]: Texto a enviar en cada stream
        """
        # Añadir chunk al buffer de entrada
        self.input_buffer += chunk
        
        # El output anónimo siempre es el chunk original (sin procesar)
        anonymous_output = chunk
        
        # Procesar el buffer completo para deanonymización
        full_deanonymized = self._deanonymize_full_buffer()
        
        # Determinar qué parte nueva enviar en el stream deanonymizado
        new_content = full_deanonymized[self.last_sent_pos:]
        
        # Estrategia conservadora: solo enviar contenido "estable"
        # Si el chunk actual termina en medio de una palabra, retener la última palabra
        stable_content = self._get_stable_content(new_content)
        
        # Actualizar posición de envío
        if stable_content:
            self.last_sent_pos += len(stable_content)
        
        deanonymized_output = stable_content
        
        # Log detallado para debugging
        logger.debug(f"📝 Chunk in: {repr(chunk)}")
        logger.debug(f"📦 Input buffer ({len(self.input_buffer)}): {repr(self.input_buffer[:100])}")
        logger.debug(f"🔄 Full deanon ({len(full_deanonymized)}): {repr(full_deanonymized[:100])}")
        logger.debug(f"📤 Stable content: {repr(stable_content)}")
        logger.debug(f"� Last sent pos: {self.last_sent_pos}")
        
        # Debug específico para detección de nombres
        for fake_name in self.reverse_map.keys():
            if fake_name in self.input_buffer:
                logger.debug(f"🎯 FOUND COMPLETE NAME '{fake_name}' in buffer!")
            else:
                # Verificar fragmentos
                for word in fake_name.split():
                    if word in self.input_buffer:
                        logger.debug(f"🔍 Found partial name fragment '{word}' from '{fake_name}'")
        
        return anonymous_output, deanonymized_output
    
    def _deanonymize_full_buffer(self) -> str:
        """
        Deanonymiza el buffer completo de entrada usando estrategia mejorada.
        Prioriza coincidencias exactas y maneja mejor los nombres fragmentados.
        """
        result = self.input_buffer
        replacements_made = []
        
        # Ordenar por longitud descendente para procesar nombres completos primero
        sorted_items = sorted(self.reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        logger.debug(f"🔍 Procesando buffer: {repr(result[:200])}")
        logger.debug(f"🗺️ Mapa disponible: {self.reverse_map}")
        
        # ESTRATEGIA 1: Coincidencias exactas completas (máxima prioridad)
        for fake_data, original_data in sorted_items:
            if fake_data in result:
                count_before = result.count(fake_data)
                result = result.replace(fake_data, original_data)
                replacements_made.append(f"'{fake_data}' -> '{original_data}' (exact, {count_before}x)")
                logger.info(f"🎯 EXACT REPLACEMENT: '{fake_data}' -> '{original_data}'")
        
        # ESTRATEGIA 2: Coincidencias por palabras individuales (si no hubo exactas)
        if not replacements_made:
            logger.debug("🔍 No exact matches, trying word-by-word...")
            
            for fake_data, original_data in sorted_items:
                if ' ' in fake_data and ' ' in original_data:  # Solo nombres multi-palabra
                    fake_words = fake_data.split()
                    original_words = original_data.split()
                    
                    # Verificar cada palabra individual del nombre falso
                    for i, fake_word in enumerate(fake_words):
                        if fake_word in result and len(fake_word) >= 3:  # Mínimo 3 chars
                            if i < len(original_words):
                                original_word = original_words[i]
                                # Reemplazar solo si no es parte de otra palabra
                                import re
                                pattern = r'\b' + re.escape(fake_word) + r'\b'
                                if re.search(pattern, result):
                                    result = re.sub(pattern, original_word, result)
                                    replacements_made.append(f"'{fake_word}' -> '{original_word}' (word {i+1})")
                                    logger.info(f"🔄 WORD REPLACEMENT: '{fake_word}' -> '{original_word}'")
        
        # ESTRATEGIA 3: Coincidencias de subcadenas largas (último recurso)
        if not replacements_made:
            logger.debug("🔍 No word matches, trying substring matching...")
            
            for fake_data, original_data in sorted_items:
                # Buscar subcadenas significativas del nombre falso
                if len(fake_data) >= 6:  # Solo nombres suficientemente largos
                    for i in range(len(fake_data) - 3):
                        for j in range(i + 4, len(fake_data) + 1):
                            substring = fake_data[i:j]
                            if len(substring) >= 4 and substring in result:
                                # Calcular substring correspondiente en original
                                if j <= len(original_data):
                                    orig_substring = original_data[i:j]
                                    result = result.replace(substring, orig_substring)
                                    replacements_made.append(f"'{substring}' -> '{orig_substring}' (substring)")
                                    logger.info(f"� SUBSTRING REPLACEMENT: '{substring}' -> '{orig_substring}'")
                                    break
                        if replacements_made:
                            break
                if replacements_made:
                    break
        
        if replacements_made:
            logger.debug(f"✅ All replacements made: {replacements_made}")
        else:
            logger.debug("⚠️ No replacements made in this buffer")
        
        return result
    
    def _get_stable_content(self, new_content: str) -> str:
        """
        Retorna solo el contenido "estable" que se puede enviar sin riesgo.
        Retiene palabras incompletas al final para evitar cortar nombres a medias.
        """
        if not new_content:
            return ""
            
        # Si termina con espacio o puntuación, enviar todo
        if new_content.endswith((' ', '.', ',', '!', '?', '\n', '\t')):
            return new_content
            
        # Si es muy corto, retener todo para acumular más
        if len(new_content.strip()) < 3:
            return ""
            
        # Buscar la última palabra completa
        words = new_content.split()
        if len(words) <= 1:
            return ""  # Retener si solo hay una palabra incompleta
            
        # Enviar todas las palabras completas excepto la última (que puede estar incompleta)
        stable_words = words[:-1]
        return ' '.join(stable_words) + ' ' if stable_words else ""
    
    def finalize(self) -> Tuple[str, str]:
        """
        Finaliza el procesamiento y retorna cualquier texto pendiente.
        Procesa todo el contenido restante sin restricciones de estabilidad.
        """
        # Procesar todo el buffer final
        final_deanonymized = self._deanonymize_full_buffer()
        
        # Retornar todo lo que no se ha enviado aún
        remaining_content = final_deanonymized[self.last_sent_pos:]
        
        logger.debug(f"🏁 Finalizando: remaining content = {repr(remaining_content)}")
        
        return "", remaining_content