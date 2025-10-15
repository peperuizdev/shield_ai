"""
Enhanced Phone Deanonymizer for Shield AI

Este módulo mejora la deanonimización de teléfonos manejando:
1. Fragmentación durante streaming
2. Variaciones de formato (con/sin código país)
3. Diferentes separadores (espacios, guiones)
4. Normalización inteligente
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set

logger = logging.getLogger(__name__)

class PhonePattern:
    """Representa un patrón de teléfono con sus variaciones"""
    
    def __init__(self, original_fake: str, original_real: str):
        self.original_fake = original_fake
        self.original_real = original_real
        self.variations = self._generate_variations()
        self.digits_only_fake = self._extract_digits(original_fake)
        self.digits_only_real = self._extract_digits(original_real)
    
    def _extract_digits(self, phone: str) -> str:
        """Extrae solo los dígitos de un teléfono"""
        return ''.join(filter(str.isdigit, phone))
    
    def _generate_variations(self) -> Set[str]:
        """Genera todas las variaciones posibles del teléfono fake"""
        variations = set()
        
        # Agregar el original
        variations.add(self.original_fake)
        
        # Si es un token explícito ([PHONE_X]), no generar variaciones del fake
        if self.original_fake.startswith('[') and self.original_fake.endswith(']'):
            # Para tokens, generar variaciones del valor real
            real_digits = self._extract_digits(self.original_real)
            
            if len(real_digits) >= 9:  # Teléfonos válidos
                # Variaciones del número real
                if len(real_digits) == 9:
                    # Formatos comunes españoles
                    variations.add(real_digits)  # Sin espacios
                    variations.add(f"{real_digits[:3]} {real_digits[3:6]} {real_digits[6:]}")  # Con espacios
                    variations.add(f"{real_digits[:3]}-{real_digits[3:6]}-{real_digits[6:]}")  # Con guiones
                    variations.add(f"+34 {real_digits}")  # Con +34 sin espacios
                    variations.add(f"+34 {real_digits[:3]} {real_digits[3:6]} {real_digits[6:]}")  # Con +34 y espacios
                    variations.add(f"+34-{real_digits[:3]}-{real_digits[3:6]}-{real_digits[6:]}")  # Con +34 y guiones
                    variations.add(f"(+34) {real_digits[:3]} {real_digits[3:6]} {real_digits[6:]}")  # Con paréntesis
                elif len(real_digits) > 9:
                    # Ya tiene código país, generar versiones
                    variations.add(real_digits)
                    # Versión sin código país (últimos 9 dígitos)
                    national = real_digits[-9:]
                    variations.add(national)
                    variations.add(f"{national[:3]} {national[3:6]} {national[6:]}")
            
            return variations
        
        # Para teléfonos normales (no tokens), lógica original
        digits = self._extract_digits(self.original_fake)
        
        if len(digits) >= 9:  # Teléfonos válidos
            # Variaciones básicas
            variations.add(digits)  # Solo números
            
            # Si tiene 9 dígitos (formato español típico)
            if len(digits) == 9:
                # Formatos con espacios
                variations.add(f"{digits[:3]} {digits[3:6]} {digits[6:]}")
                variations.add(f"{digits[:3]}-{digits[3:6]}-{digits[6:]}")
                
                # Con código +34
                variations.add(f"+34 {digits}")
                variations.add(f"+34 {digits[:3]} {digits[3:6]} {digits[6:]}")
                variations.add(f"+34-{digits[:3]}-{digits[3:6]}-{digits[6:]}")
                variations.add(f"(+34) {digits[:3]} {digits[3:6]} {digits[6:]}")
                variations.add(f"+34{digits}")
            
            # Si ya tiene código país, generar versiones sin él
            if self.original_fake.startswith(('+', '(+')):
                # Quitar código país y generar variaciones
                clean_digits = digits[-9:] if len(digits) > 9 else digits
                if len(clean_digits) == 9:
                    variations.add(clean_digits)
                    variations.add(f"{clean_digits[:3]} {clean_digits[3:6]} {clean_digits[6:]}")
                    variations.add(f"{clean_digits[:3]}-{clean_digits[3:6]}-{clean_digits[6:]}")
        
        logger.debug(f"Generated {len(variations)} variations for '{self.original_fake}': {variations}")
        return variations
    
    def matches(self, text: str) -> bool:
        """Verifica si el texto coincide con alguna variación"""
        # Coincidencia exacta con variaciones
        if text.strip() in self.variations:
            return True
        
        # Normalizar y comparar por dígitos para mayor flexibilidad
        text_digits = self._extract_digits(text)
        
        # Si el texto tiene al menos 7 dígitos, comparar
        if len(text_digits) >= 7:
            # Comparar con dígitos del número real (más flexible)
            real_digits = self._extract_digits(self.original_real)
            
            # Verificar si coincide con los últimos dígitos del número real
            if len(text_digits) >= 9 and len(real_digits) >= 9:
                # Para números completos
                return text_digits == real_digits[-9:] or text_digits == real_digits
            elif len(text_digits) == len(real_digits):
                # Misma cantidad de dígitos
                return text_digits == real_digits
        
        # Verificar si el texto contiene una variación
        for variation in self.variations:
            if variation in text:
                return True
        
        return False

class EnhancedPhoneDeanonymizer:
    """
    Deanonimizador mejorado que maneja específicamente teléfonos
    """
    
    def __init__(self, mapping: Dict[str, str]):
        self.original_mapping = mapping
        self.phone_patterns: List[PhonePattern] = []
        self.non_phone_mapping: Dict[str, str] = {}
        self.buffer = ""
        self.max_buffer_size = 50  # Máximo tamaño del buffer
        
        self._analyze_mapping()
        
        logger.info(f"EnhancedPhoneDeanonymizer initialized with {len(self.phone_patterns)} phone patterns")
    
    def _analyze_mapping(self):
        """Analiza el mapping y separa teléfonos del resto"""
        
        for fake, real in self.original_mapping.items():
            if self._looks_like_phone(fake) or self._looks_like_phone(real):
                # Es un teléfono
                pattern = PhonePattern(fake, real)
                self.phone_patterns.append(pattern)
                logger.debug(f"Detected phone pattern: {fake} -> {real}")
            else:
                # No es teléfono, mapeo normal
                self.non_phone_mapping[fake] = real
    
    def _looks_like_phone(self, text: str) -> bool:
        """Detecta si un texto parece un teléfono"""
        
        # Primero, verificar si es un token de teléfono explícito
        if '[PHONE_' in text.upper():
            return True
        
        # Patrones de teléfono
        phone_regex_patterns = [
            r'\+?\d[\d\s\-()]{6,}\d',  # Patrón general
            r'\d{3}\s?\d{3}\s?\d{3}',  # Formato 3-3-3
            r'\+\d{1,3}\s?\d{6,}',     # Con código país
            r'\(\+\d{1,3}\)',          # Código país con paréntesis
        ]
        
        for pattern in phone_regex_patterns:
            if re.search(pattern, text):
                return True
        
        # También verificar por conteo de dígitos
        digits = ''.join(filter(str.isdigit, text))
        return len(digits) >= 7  # Al menos 7 dígitos
    
    def process_chunk(self, chunk: str) -> str:
        """
        Procesa un chunk con detección mejorada de teléfonos
        """
        if not chunk:
            return ""
        
        # 1. Reemplazo directo para tokens exactos (como [PHONE_1])
        for fake, real in self.original_mapping.items():
            if chunk == fake:
                logger.debug(f"Direct token replacement: {fake} -> {real}")
                return real
        
        # 2. Agregar al buffer para análisis contextual
        self.buffer += chunk
        
        # Mantener tamaño del buffer
        if len(self.buffer) > self.max_buffer_size:
            self.buffer = self.buffer[-self.max_buffer_size:]
        
        # 3. Verificar si el buffer completo coincide con algún patrón de teléfono
        for pattern in self.phone_patterns:
            if pattern.matches(self.buffer):
                logger.debug(f"Phone match found in buffer: '{self.buffer}' -> '{pattern.original_real}'")
                # Enviar el teléfono completo y limpiar buffer
                self.buffer = ""
                return pattern.original_real
        
        # 4. Si no hay coincidencia completa, decidir si enviar el chunk o esperar
        if self._should_wait_for_more(chunk):
            # No enviar aún, puede ser parte de un teléfono
            return ""
        else:
            # Enviar el chunk actual
            return chunk
    
    def _try_exact_replacements(self, chunk: str) -> str:
        """Intenta reemplazos exactos para tokens no-teléfono"""
        
        for fake, real in self.non_phone_mapping.items():
            if chunk == fake:
                logger.debug(f"Exact replacement: {fake} -> {real}")
                return real
        
        return chunk
    
    def _try_phone_replacements(self, chunk: str) -> str:
        """Intenta reemplazos de teléfonos considerando el buffer"""
        
        # Probar con el buffer completo
        for pattern in self.phone_patterns:
            if pattern.matches(self.buffer):
                logger.debug(f"Phone match found in buffer: '{self.buffer}' -> '{pattern.original_real}'")
                # Calcular qué parte del buffer corresponde al chunk actual
                return self._extract_chunk_replacement(chunk, pattern.original_real)
            
            # También probar solo con el chunk
            if pattern.matches(chunk):
                logger.debug(f"Phone match found in chunk: '{chunk}' -> '{pattern.original_real}'")
                return pattern.original_real
        
        return chunk
    
    def _extract_chunk_replacement(self, chunk: str, full_replacement: str) -> str:
        """
        Extrae la parte del reemplazo que corresponde al chunk actual
        """
        # Si el chunk es el último de un teléfono, devolver el teléfono completo
        # Esta es una simplificación; en un caso real sería más complejo
        
        # Por ahora, devolver el reemplazo completo cuando detectamos el patrón
        return full_replacement
    
    def _should_wait_for_more(self, chunk: str) -> bool:
        """Determina si debemos esperar más caracteres antes de enviar"""
        
        # Si el buffer parece el inicio de un teléfono, esperar
        if self._buffer_looks_like_phone_start():
            return True
        
        # Si el chunk tiene dígitos y es corto, esperar
        if re.search(r'\d', chunk) and len(chunk) <= 3:
            return True
        
        # Si el buffer termina con +, esperar
        if self.buffer.endswith('+'):
            return True
        
        return False
    
    def _buffer_looks_like_phone_start(self) -> bool:
        """Verifica si el buffer parece el inicio de un teléfono"""
        
        phone_start_patterns = [
            r'\+\d{0,3}$',          # +34, +3, +
            r'\d{1,3}$',            # 612, 61, 6
            r'\(\+\d{0,3}$',        # (+34, (+3, (+
            r'\+\d{1,3}\s\d{0,3}$', # +34 6, +34 61
        ]
        
        for pattern in phone_start_patterns:
            if re.search(pattern, self.buffer):
                return True
        
        return False
    
    def flush_remaining(self) -> str:
        """Procesa cualquier contenido restante en el buffer"""
        
        if not self.buffer:
            return ""
        
        # Intentar último reemplazo de teléfonos
        for pattern in self.phone_patterns:
            if pattern.matches(self.buffer):
                logger.debug(f"Final phone replacement: '{self.buffer}' -> '{pattern.original_real}'")
                self.buffer = ""
                return pattern.original_real
        
        # Intentar reemplazos exactos
        for fake, real in self.non_phone_mapping.items():
            if self.buffer == fake:
                logger.debug(f"Final exact replacement: '{fake}' -> '{real}'")
                self.buffer = ""
                return real
        
        # No hay reemplazo, devolver buffer
        result = self.buffer
        self.buffer = ""
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas del procesamiento"""
        return {
            "phone_patterns": len(self.phone_patterns),
            "non_phone_mappings": len(self.non_phone_mapping),
            "total_mappings": len(self.original_mapping),
            "buffer_size": len(self.buffer)
        }
    
    def debug_state(self) -> Dict:
        """Estado actual para debugging"""
        return {
            "buffer": self.buffer,
            "phone_patterns_count": len(self.phone_patterns),
            "non_phone_mappings_count": len(self.non_phone_mapping),
            "stats": self.get_stats()
        }

# Función para integrar con el sistema existente
def create_enhanced_phone_deanonymizer(mapping: Dict[str, str]) -> EnhancedPhoneDeanonymizer:
    """
    Factory function para crear un deanonimizador mejorado
    
    Args:
        mapping: Mapping original de fake -> real
    
    Returns:
        EnhancedPhoneDeanonymizer configurado
    """
    return EnhancedPhoneDeanonymizer(mapping)