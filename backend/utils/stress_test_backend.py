#!/usr/bin/env python3
"""
🚀 STRESS TEST BACKEND SHIELD AI
Script para realizar pruebas de carga y estrés al backend
"""

import asyncio
import aiohttp
import time
import json
import statistics
import argparse
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class TestResult:
    """Resultado de una prueba individual"""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StressTestConfig:
    """Configuración del stress test"""
    base_url: str = "http://localhost:8000"
    concurrent_requests: int = 10
    total_requests: int = 100
    timeout: int = 30
    delay_between_requests: float = 0.1


class BackendStressTester:
    """Stress tester para el backend Shield AI"""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.session_ids: List[str] = []
        
    async def create_session(self) -> aiohttp.ClientSession:
        """Crear sesión HTTP con timeouts apropiados"""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        return aiohttp.ClientSession(timeout=timeout)
    
    def generate_test_data(self):
        """Generar datos de prueba"""
        return {
            "anonymize_request": {
                "text": "Mi nombre es Juan Pérez, mi DNI es 12345678A y mi teléfono es 666123456. Mi IBAN es ES80 8695 8760 88 7830358539.",
                "session_id": f"stress_test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            },
            "chat_request": {
                "message": "Hola, necesito ayuda con información confidencial sobre Juan Pérez.",
                "session_id": f"chat_stress_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            }
        }
    
    async def test_health_endpoint(self, session: aiohttp.ClientSession) -> TestResult:
        """Test del endpoint de health/status"""
        start_time = time.time()
        
        try:
            async with session.get(f"{self.config.base_url}/health") as response:
                response_time = time.time() - start_time
                return TestResult(
                    endpoint="/health",
                    method="GET",
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status == 200
                )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint="/health",
                method="GET",
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def test_metrics_endpoint(self, session: aiohttp.ClientSession) -> TestResult:
        """Test del endpoint de métricas Prometheus"""
        start_time = time.time()
        
        try:
            async with session.get(f"{self.config.base_url}/metrics") as response:
                response_time = time.time() - start_time
                return TestResult(
                    endpoint="/metrics",
                    method="GET",
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status == 200
                )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint="/metrics",
                method="GET",
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def test_anonymize_endpoint(self, session: aiohttp.ClientSession) -> TestResult:
        """Test del endpoint de anonimización"""
        start_time = time.time()
        data = self.generate_test_data()["anonymize_request"]
        
        try:
            headers = {"Content-Type": "application/json"}
            async with session.post(
                f"{self.config.base_url}/anonymize",
                json=data,
                headers=headers
            ) as response:
                response_time = time.time() - start_time
                
                # Guardar session_id para tests de deanonimización
                if response.status == 200:
                    self.session_ids.append(data["session_id"])
                
                return TestResult(
                    endpoint="/anonymize",
                    method="POST",
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status == 200
                )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint="/anonymize",
                method="POST",
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def test_chat_streaming_endpoint(self, session: aiohttp.ClientSession) -> TestResult:
        """Test del endpoint de chat streaming"""
        start_time = time.time()
        data = self.generate_test_data()["chat_request"]
        
        try:
            headers = {"Content-Type": "application/json"}
            async with session.post(
                f"{self.config.base_url}/chat/streaming",
                json=data,
                headers=headers
            ) as response:
                response_time = time.time() - start_time
                
                return TestResult(
                    endpoint="/chat/streaming",
                    method="POST",
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status == 200
                )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint="/chat/streaming",
                method="POST",
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def test_deanonymize_endpoint(self, session: aiohttp.ClientSession) -> TestResult:
        """Test del endpoint de deanonimización (requiere session_id previo)"""
        start_time = time.time()
        
        # Usar un session_id existente o crear uno nuevo
        if self.session_ids:
            session_id = self.session_ids[-1]
        else:
            # Crear una sesión rápida para poder probar deanonimización
            await self.test_anonymize_endpoint(session)
            session_id = self.session_ids[-1] if self.session_ids else f"fallback_{int(time.time())}"
        
        try:
            endpoint = f"/anonymize/session/{session_id}/anonymized-request"
            async with session.get(f"{self.config.base_url}{endpoint}") as response:
                response_time = time.time() - start_time
                
                return TestResult(
                    endpoint=endpoint,
                    method="GET",
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status in [200, 404]  # 404 es válido si la sesión no existe
                )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint="/anonymize/session/*/anonymized-request",
                method="GET",
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def run_single_test_batch(self, session: aiohttp.ClientSession) -> List[TestResult]:
        """Ejecutar un batch de tests de todos los endpoints"""
        tasks = [
            self.test_health_endpoint(session),
            self.test_metrics_endpoint(session),
            self.test_anonymize_endpoint(session),
            self.test_chat_streaming_endpoint(session),
            self.test_deanonymize_endpoint(session)
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_concurrent_stress_test(self):
        """Ejecutar stress test con múltiples conexiones concurrentes"""
        print(f"🚀 INICIANDO STRESS TEST")
        print(f"📊 Configuración:")
        print(f"   - URL Base: {self.config.base_url}")
        print(f"   - Requests Concurrentes: {self.config.concurrent_requests}")
        print(f"   - Total Requests: {self.config.total_requests}")
        print(f"   - Timeout: {self.config.timeout}s")
        print(f"   - Delay entre requests: {self.config.delay_between_requests}s")
        print("=" * 60)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Crear semáforo para limitar concurrencia
            semaphore = asyncio.Semaphore(self.config.concurrent_requests)
            
            async def bounded_test():
                async with semaphore:
                    result = await self.run_single_test_batch(session)
                    if self.config.delay_between_requests > 0:
                        await asyncio.sleep(self.config.delay_between_requests)
                    return result
            
            # Calcular cuántos batches necesitamos
            batches_needed = self.config.total_requests // 5  # 5 endpoints por batch
            
            print(f"🔄 Ejecutando {batches_needed} batches de tests...")
            
            # Ejecutar batches
            all_tasks = [bounded_test() for _ in range(batches_needed)]
            batch_results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # Procesar resultados
            for batch_result in batch_results:
                if isinstance(batch_result, Exception):
                    print(f"❌ Error en batch: {batch_result}")
                    continue
                
                for result in batch_result:
                    if isinstance(result, TestResult):
                        self.results.append(result)
                    elif isinstance(result, Exception):
                        print(f"❌ Error en test individual: {result}")
        
        total_time = time.time() - start_time
        print(f"⏱️  Tiempo total: {total_time:.2f} segundos")
        
        return self.analyze_results(total_time)
    
    def analyze_results(self, total_time: float) -> Dict[str, Any]:
        """Analizar los resultados del stress test"""
        if not self.results:
            return {"error": "No hay resultados para analizar"}
        
        # Agrupar por endpoint
        endpoint_stats = {}
        for result in self.results:
            if result.endpoint not in endpoint_stats:
                endpoint_stats[result.endpoint] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "response_times": [],
                    "status_codes": []
                }
            
            stats = endpoint_stats[result.endpoint]
            stats["total"] += 1
            stats["response_times"].append(result.response_time)
            stats["status_codes"].append(result.status_code)
            
            if result.success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        # Calcular estadísticas
        analysis = {
            "summary": {
                "total_requests": len(self.results),
                "total_time": total_time,
                "requests_per_second": len(self.results) / total_time if total_time > 0 else 0,
                "success_rate": sum(1 for r in self.results if r.success) / len(self.results) * 100
            },
            "endpoints": {}
        }
        
        for endpoint, stats in endpoint_stats.items():
            response_times = stats["response_times"]
            
            analysis["endpoints"][endpoint] = {
                "total_requests": stats["total"],
                "success_count": stats["success"],
                "failed_count": stats["failed"],
                "success_rate": (stats["success"] / stats["total"]) * 100,
                "response_time": {
                    "avg": statistics.mean(response_times),
                    "min": min(response_times),
                    "max": max(response_times),
                    "median": statistics.median(response_times),
                    "p95": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
                },
                "status_codes": dict(zip(*[list(s) for s in zip(*[(code, stats["status_codes"].count(code)) for code in set(stats["status_codes"])])])) if stats["status_codes"] else {}
            }
        
        return analysis
    
    def print_results(self, analysis: Dict[str, Any]):
        """Imprimir resultados del análisis"""
        print("\n🎯 RESULTADOS DEL STRESS TEST")
        print("=" * 60)
        
        summary = analysis["summary"]
        print(f"📊 RESUMEN GENERAL:")
        print(f"   ✅ Total Requests: {summary['total_requests']}")
        print(f"   ⏱️  Tiempo Total: {summary['total_time']:.2f}s")
        print(f"   🚀 Requests/segundo: {summary['requests_per_second']:.2f}")
        print(f"   ✅ Tasa de Éxito: {summary['success_rate']:.1f}%")
        
        print(f"\n📋 DETALLES POR ENDPOINT:")
        print("-" * 60)
        
        for endpoint, stats in analysis["endpoints"].items():
            print(f"\n🎯 {endpoint}")
            print(f"   📊 Requests: {stats['total_requests']} (✅{stats['success_count']} ❌{stats['failed_count']})")
            print(f"   ✅ Éxito: {stats['success_rate']:.1f}%")
            print(f"   ⏱️  Response Time:")
            print(f"      - Promedio: {stats['response_time']['avg']:.3f}s")
            print(f"      - Mínimo: {stats['response_time']['min']:.3f}s")
            print(f"      - Máximo: {stats['response_time']['max']:.3f}s")
            print(f"      - Mediana: {stats['response_time']['median']:.3f}s")
            print(f"      - P95: {stats['response_time']['p95']:.3f}s")
            print(f"   📈 Status Codes: {stats['status_codes']}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        print("-" * 30)
        
        if summary['success_rate'] >= 95:
            print("✅ Excelente tasa de éxito - El backend está manejando bien la carga")
        elif summary['success_rate'] >= 90:
            print("⚠️  Buena tasa de éxito - Considerar optimizaciones menores")
        else:
            print("❌ Baja tasa de éxito - Revisar capacidad del backend")
        
        avg_response_time = statistics.mean([r.response_time for r in self.results])
        if avg_response_time < 0.1:
            print("✅ Excelente tiempo de respuesta")
        elif avg_response_time < 0.5:
            print("✅ Buen tiempo de respuesta")
        elif avg_response_time < 1.0:
            print("⚠️  Tiempo de respuesta moderado")
        else:
            print("❌ Tiempo de respuesta lento - Optimizar performance")
        
        print(f"\n🔍 Para monitorear el impacto:")
        print(f"   - Revisar Grafana: http://localhost:3000")
        print(f"   - Métricas Prometheus: http://localhost:8000/metrics")


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Stress Test para Backend Shield AI")
    parser.add_argument("--url", default="http://localhost:8000", help="URL base del backend")
    parser.add_argument("--concurrent", type=int, default=10, help="Requests concurrentes")
    parser.add_argument("--total", type=int, default=100, help="Total de requests")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout en segundos")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay entre requests")
    
    # Presets predefinidos
    parser.add_argument("--preset", choices=["light", "medium", "heavy", "extreme"], 
                       help="Usar preset predefinido")
    
    args = parser.parse_args()
    
    # Aplicar presets
    if args.preset == "light":
        config = StressTestConfig(args.url, 5, 50, 15, 0.2)
    elif args.preset == "medium":
        config = StressTestConfig(args.url, 15, 200, 30, 0.1)
    elif args.preset == "heavy":
        config = StressTestConfig(args.url, 25, 500, 60, 0.05)
    elif args.preset == "extreme":
        config = StressTestConfig(args.url, 50, 1000, 120, 0.01)
    else:
        config = StressTestConfig(args.url, args.concurrent, args.total, args.timeout, args.delay)
    
    print("🧪 SHIELD AI BACKEND STRESS TESTER")
    print("=" * 50)
    
    tester = BackendStressTester(config)
    
    try:
        analysis = await tester.run_concurrent_stress_test()
        tester.print_results(analysis)
        
        # Guardar resultados en archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados guardados en: {filename}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante el stress test: {e}")


if __name__ == "__main__":
    asyncio.run(main())