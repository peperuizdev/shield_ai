#!/usr/bin/env python3
"""
🚀 QUICK STRESS TEST - Prueba rápida del backend
"""

import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


class QuickStressTester:
    """Stress tester simple y rápido"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    def test_endpoint(self, endpoint, method="GET", data=None, timeout=10):
        """Test individual de un endpoint"""
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(
                    f"{self.base_url}{endpoint}", 
                    json=data, 
                    headers={"Content-Type": "application/json"},
                    timeout=timeout
                )
            
            response_time = time.time() - start_time
            
            return {
                "endpoint": endpoint,
                "method": method,
                "status": response.status_code,
                "time": response_time,
                "success": response.status_code < 400,
                "size": len(response.content)
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "endpoint": endpoint,
                "method": method,
                "status": 0,
                "time": response_time,
                "success": False,
                "error": str(e),
                "size": 0
            }
    
    def run_quick_test(self, threads=5, requests_per_endpoint=10):
        """Ejecutar prueba rápida"""
        print(f"🚀 QUICK STRESS TEST")
        print(f"🔧 Configuración: {threads} hilos, {requests_per_endpoint} requests por endpoint")
        print("=" * 50)
        
        # Endpoints a testear
        test_cases = [
            ("/health", "GET", None),
            ("/metrics", "GET", None),
            ("/anonymize", "POST", {
                "text": "Hola soy Juan con DNI 12345678A",
                "session_id": f"quick_test_{int(time.time())}"
            }),
            ("/chat/streaming", "POST", {
                "message": "Hola mundo",
                "session_id": f"chat_test_{int(time.time())}"
            })
        ]
        
        all_tasks = []
        
        # Crear todas las tareas
        for endpoint, method, data in test_cases:
            for i in range(requests_per_endpoint):
                # Hacer data único para cada request
                if data:
                    unique_data = data.copy()
                    if "session_id" in unique_data:
                        unique_data["session_id"] = f"{unique_data['session_id']}_{i}"
                else:
                    unique_data = None
                
                all_tasks.append((endpoint, method, unique_data))
        
        print(f"📊 Ejecutando {len(all_tasks)} requests...")
        
        start_time = time.time()
        
        # Ejecutar con ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [
                executor.submit(self.test_endpoint, endpoint, method, data)
                for endpoint, method, data in all_tasks
            ]
            
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
                completed += 1
                
                if completed % 10 == 0:
                    print(f"✅ Completado: {completed}/{len(all_tasks)}")
        
        total_time = time.time() - start_time
        self.print_quick_results(total_time)
    
    def print_quick_results(self, total_time):
        """Imprimir resultados rápidos"""
        print(f"\n🎯 RESULTADOS QUICK TEST")
        print("=" * 40)
        
        total_requests = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total_requests - successful
        
        response_times = [r["time"] for r in self.results]
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"📊 RESUMEN:")
        print(f"   Total: {total_requests}")
        print(f"   ✅ Éxito: {successful} ({successful/total_requests*100:.1f}%)")
        print(f"   ❌ Error: {failed}")
        print(f"   ⏱️  Tiempo total: {total_time:.2f}s")
        print(f"   🚀 RPS: {total_requests/total_time:.1f}")
        print(f"   📈 Response time: {avg_time:.3f}s (min: {min_time:.3f}s, max: {max_time:.3f}s)")
        
        # Detalles por endpoint
        print(f"\n📋 POR ENDPOINT:")
        endpoints = {}
        for result in self.results:
            ep = result["endpoint"]
            if ep not in endpoints:
                endpoints[ep] = {"total": 0, "success": 0, "times": []}
            
            endpoints[ep]["total"] += 1
            if result["success"]:
                endpoints[ep]["success"] += 1
            endpoints[ep]["times"].append(result["time"])
        
        for endpoint, stats in endpoints.items():
            success_rate = (stats["success"] / stats["total"]) * 100
            avg_time = statistics.mean(stats["times"])
            print(f"   {endpoint}: {success_rate:.1f}% éxito, {avg_time:.3f}s promedio")
        
        # Estado general
        print(f"\n💡 ESTADO:")
        if successful/total_requests >= 0.95:
            print("✅ Backend funcionando correctamente")
        elif successful/total_requests >= 0.8:
            print("⚠️  Backend con algunos problemas")
        else:
            print("❌ Backend con problemas serios")


def main():
    """Función principal para quick test"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick Stress Test")
    parser.add_argument("--url", default="http://localhost:8000", help="URL del backend")
    parser.add_argument("--threads", type=int, default=5, help="Número de hilos")
    parser.add_argument("--requests", type=int, default=10, help="Requests por endpoint")
    
    args = parser.parse_args()
    
    tester = QuickStressTester(args.url)
    tester.run_quick_test(args.threads, args.requests)


if __name__ == "__main__":
    main()