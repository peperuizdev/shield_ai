"""
Chunked Deanonymization Helper - VERSIÓN OPTIMIZADA
Maneja la deanonymización precisa de chunks fragmentados del LLM
Balanceado para streaming fluido manteniendo precisión en reemplazos
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ChunkDeanonymizer:
    """
    Deanonymización BALANCEADA para streaming fluido.
    Prioriza streaming fluido manteniendo precisión en reemplazos.
    """
    
    def __init__(self, reverse_map: Dict[str, str]):
        self.reverse_map = reverse_map
        self.input_buffer = ""
        self.last_sent_pos = 0
        
        # Separar entidades por complejidad para tratamiento diferenciado
        self.simple_entities = {}  # Palabras simples, emails, teléfonos
        self.complex_entities = {}  # Nombres multi-palabra largos
        
        for fake, real in reverse_map.items():
            if ' ' in fake and len(fake.split()) >= 3:
                self.complex_entities[fake] = real
            else:
                self.simple_entities[fake] = real
                
        logger.info(f"🔧 Simple entities: {len(self.simple_entities)}, Complex: {len(self.complex_entities)}")
        
    def process_chunk(self, chunk: str) -> Tuple[str, str]:
        """
        Versión STREAMING-FRIENDLY con menos bloqueos.
        
        Args:
            chunk: Fragmento de texto del LLM
            
        Returns:
            Tuple[anonymous_output, deanonymized_output]: Texto para cada stream
        """
        # Acumular chunk
        self.input_buffer += chunk
        # ✅ SIEMPRE devolver el chunk original para el stream anonimizado
        anonymous_output = chunk
        
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
        
        # Deanonymizar todo el buffer con entidades simples primero
        deanonymized_buffer = self._quick_deanonymize(self.input_buffer)
        
        # Enviar todo el contenido nuevo
        new_content = deanonymized_buffer[self.last_sent_pos:]
        self.last_sent_pos = len(deanonymized_buffer)
        
        logger.debug(f"📝 Complete sentence - sending: '{new_content[:50]}...'")
        return new_content
    
    def _process_partial_content(self) -> str:
        """Procesa contenido parcial de forma menos conservadora - SOLO retorna deanonymized"""
        
        deanonymized_buffer = self._quick_deanonymize(self.input_buffer)
        
        # Estrategia más permisiva para contenido parcial
        words = deanonymized_buffer[self.last_sent_pos:].split()
        
        if len(words) >= 3:  # Reducido de 4+ a 3+
            # Enviar todas las palabras excepto la última (por si está cortada)
            safe_content = ' '.join(words[:-1]) + ' '
            self.last_sent_pos += len(safe_content)
            
            logger.debug(f"📦 Partial content - sending: '{safe_content[:50]}...'")
            return safe_content
        
        return ""
    
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
    
    def _is_safe_simple_replacement(self, text: str, entity: str) -> bool:
        """Validación relajada para entidades simples"""
        
        # Para emails, teléfonos, etc. - validación básica
        if '@' in entity or entity.isdigit():
            return entity in text
        
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
    
    def finalize(self) -> Tuple[str, str]:
        """Envía todo el contenido restante al final"""
        final_deanonymized = self._quick_deanonymize(self.input_buffer)
        remaining = final_deanonymized[self.last_sent_pos:]
        
        logger.info(f"🏁 Finalizing - sending remaining: '{remaining[:100]}...'")
        return "", remaining
