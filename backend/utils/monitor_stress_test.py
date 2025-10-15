#!/usr/bin/env python3
"""
📊 MONITOR DE MÉTRICAS DURANTE STRESS TEST
Monitorea las métricas del backend mientras se ejecuta un stress test
"""

import requests
import time
import threading
import json
from datetime import datetime
from typing import Dict, List
import os
import sys


class MetricsMonitor:
    """Monitor de métricas en tiempo real"""
    
    def __init__(self, backend_url="http://localhost:8000"):
        self.backend_url = backend_url
        self.metrics_data: List[Dict] = []
        self.monitoring = False
        self.monitor_thread = None
    
    def parse_prometheus_metrics(self, metrics_text: str) -> Dict:
        """Parsear métricas de Prometheus"""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            line = line.strip()
            
            # Ignorar comentarios y líneas vacías
            if not line or line.startswith('#'):
                continue
            
            # Buscar métricas específicas
            if 'system_cpu_usage_percent' in line and not line.startswith('#'):
                try:
                    value = float(line.split()[-1])
                    metrics['cpu_usage_percent'] = value
                except:
                    pass
            
            elif 'system_memory_usage_bytes' in line and not line.startswith('#'):
                try:
                    value = float(line.split()[-1])
                    metrics['memory_usage_gb'] = value / (1024**3)
                except:
                    pass
            
            elif 'http_requests_total' in line and not line.startswith('#'):
                try:
                    # Sumar todos los requests
                    if 'total_requests' not in metrics:
                        metrics['total_requests'] = 0
                    value = float(line.split()[-1])
                    metrics['total_requests'] += value
                except:
                    pass
            
            elif 'pii_detection_errors_total' in line and not line.startswith('#'):
                try:
                    value = float(line.split()[-1])
                    metrics['pii_errors'] = value
                except:
                    pass
            
            elif 'redis_connection_status' in line and not line.startswith('#'):
                try:
                    value = float(line.split()[-1])
                    metrics['redis_connected'] = value == 1.0
                except:
                    pass
        
        return metrics
    
    def collect_metrics(self):
        """Recopilar métricas del backend"""
        try:
            response = requests.get(f"{self.backend_url}/metrics", timeout=5)
            if response.status_code == 200:
                parsed_metrics = self.parse_prometheus_metrics(response.text)
                
                # Añadir timestamp
                parsed_metrics['timestamp'] = datetime.now()
                parsed_metrics['timestamp_unix'] = time.time()
                
                return parsed_metrics
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def monitor_loop(self, interval=1.0):
        """Loop de monitoreo"""
        print(f"📊 Iniciando monitoreo de métricas (intervalo: {interval}s)")
        
        while self.monitoring:
            metrics = self.collect_metrics()
            
            if "error" not in metrics:
                self.metrics_data.append(metrics)
                
                # Imprimir métricas en tiempo real
                cpu = metrics.get('cpu_usage_percent', 'N/A')
                memory = metrics.get('memory_usage_gb', 'N/A')
                requests = metrics.get('total_requests', 'N/A')
                redis = "✅" if metrics.get('redis_connected', False) else "❌"
                
                print(f"📈 CPU: {cpu}% | RAM: {memory:.1f}GB | Requests: {requests} | Redis: {redis}")
            else:
                print(f"❌ Error recopilando métricas: {metrics['error']}")
            
            time.sleep(interval)
    
    def start_monitoring(self, interval=1.0):
        """Iniciar monitoreo en hilo separado"""
        if self.monitoring:
            print("⚠️  Ya se está monitoreando")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 Monitoreo detenido")
    
    def save_metrics_report(self, filename=None):
        """Guardar reporte de métricas"""
        if not self.metrics_data:
            print("❌ No hay datos de métricas para guardar")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_report_{timestamp}.json"
        
        # Convertir timestamps a string para JSON
        metrics_for_json = []
        for metric in self.metrics_data:
            metric_copy = metric.copy()
            if 'timestamp' in metric_copy:
                metric_copy['timestamp'] = metric_copy['timestamp'].isoformat()
            metrics_for_json.append(metric_copy)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(metrics_for_json, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Métricas guardadas en: {filename}")
        return filename
    
    def create_metrics_chart(self, save_path=None):
        """Crear gráfico de métricas"""
        if len(self.metrics_data) < 2:
            print("❌ Necesitas más datos para crear un gráfico")
            return
        
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            # Preparar datos
            timestamps = [m['timestamp'] for m in self.metrics_data if 'timestamp' in m]
            cpu_data = [m.get('cpu_usage_percent', 0) for m in self.metrics_data]
            memory_data = [m.get('memory_usage_gb', 0) for m in self.metrics_data]
            requests_data = [m.get('total_requests', 0) for m in self.metrics_data]
            
            # Crear subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Métricas del Backend Durante Stress Test', fontsize=16)
            
            # CPU Usage
            ax1.plot(timestamps, cpu_data, 'b-', linewidth=2)
            ax1.set_title('CPU Usage (%)')
            ax1.set_ylabel('Porcentaje')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            
            # Memory Usage
            ax2.plot(timestamps, memory_data, 'g-', linewidth=2)
            ax2.set_title('Memory Usage (GB)')
            ax2.set_ylabel('Gigabytes')
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            
            # HTTP Requests Total
            ax3.plot(timestamps, requests_data, 'r-', linewidth=2)
            ax3.set_title('Total HTTP Requests')
            ax3.set_ylabel('Requests')
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            
            # Requests per second (derivada)
            if len(requests_data) > 1:
                rps_data = []
                for i in range(1, len(requests_data)):
                    time_diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                    req_diff = requests_data[i] - requests_data[i-1]
                    rps = req_diff / time_diff if time_diff > 0 else 0
                    rps_data.append(rps)
                
                ax4.plot(timestamps[1:], rps_data, 'orange', linewidth=2)
                ax4.set_title('Requests per Second')
                ax4.set_ylabel('RPS')
                ax4.grid(True, alpha=0.3)
                ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            
            # Ajustar layout
            plt.tight_layout()
            
            # Guardar gráfico
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"metrics_chart_{timestamp}.png"
            
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 Gráfico guardado en: {save_path}")
            
            # Mostrar gráfico si es posible
            try:
                plt.show()
            except:
                print("💡 Gráfico guardado (no se puede mostrar en este entorno)")
            
            return save_path
            
        except ImportError:
            print("❌ matplotlib no está instalado. Ejecuta: pip install matplotlib")
            return None
        except Exception as e:
            print(f"❌ Error creando gráfico: {e}")
            return None
    
    def print_summary(self):
        """Imprimir resumen de métricas"""
        if not self.metrics_data:
            print("❌ No hay datos de métricas")
            return
        
        print(f"\n📊 RESUMEN DE MÉTRICAS")
        print("=" * 40)
        
        # CPU
        cpu_values = [m.get('cpu_usage_percent') for m in self.metrics_data if m.get('cpu_usage_percent') is not None]
        if cpu_values:
            print(f"🖥️  CPU Usage:")
            print(f"   Promedio: {sum(cpu_values)/len(cpu_values):.1f}%")
            print(f"   Mínimo: {min(cpu_values):.1f}%")
            print(f"   Máximo: {max(cpu_values):.1f}%")
        
        # Memory
        memory_values = [m.get('memory_usage_gb') for m in self.metrics_data if m.get('memory_usage_gb') is not None]
        if memory_values:
            print(f"💾 Memory Usage:")
            print(f"   Promedio: {sum(memory_values)/len(memory_values):.2f}GB")
            print(f"   Mínimo: {min(memory_values):.2f}GB")
            print(f"   Máximo: {max(memory_values):.2f}GB")
        
        # Requests
        if len(self.metrics_data) > 1:
            first_requests = self.metrics_data[0].get('total_requests', 0)
            last_requests = self.metrics_data[-1].get('total_requests', 0)
            total_time = (self.metrics_data[-1]['timestamp'] - self.metrics_data[0]['timestamp']).total_seconds()
            
            print(f"🌐 HTTP Requests:")
            print(f"   Total procesados: {last_requests - first_requests:.0f}")
            print(f"   Tiempo monitoreo: {total_time:.1f}s")
            if total_time > 0:
                print(f"   RPS promedio: {(last_requests - first_requests) / total_time:.1f}")


def run_stress_test_with_monitoring():
    """Ejecutar stress test con monitoreo de métricas"""
    print("🚀 STRESS TEST CON MONITOREO DE MÉTRICAS")
    print("=" * 50)
    
    monitor = MetricsMonitor()
    
    try:
        # Iniciar monitoreo
        monitor.start_monitoring(interval=0.5)
        
        print("⏱️  Esperando 3 segundos para establecer baseline...")
        time.sleep(3)
        
        # Ejecutar stress test
        print("🚀 Iniciando stress test...")
        
        import subprocess
        
        # Buscar el script quick_stress_test.py
        script_path = os.path.join(os.path.dirname(__file__), "quick_stress_test.py")
        if not os.path.exists(script_path):
            # Buscar en el directorio padre (para compatibilidad)
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quick_stress_test.py")
        
        # Ejecutar quick stress test
        result = subprocess.run([
            sys.executable, script_path,
            "--threads", "10",
            "--requests", "20"
        ], capture_output=True, text=True)
        
        print("✅ Stress test completado")
        print("📊 Continuando monitoreo por 5 segundos más...")
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n⚠️  Monitoreo interrumpido por el usuario")
    except Exception as e:
        print(f"❌ Error durante el test: {e}")
    finally:
        # Detener monitoreo
        monitor.stop_monitoring()
        
        # Generar reportes
        print("\n📋 Generando reportes...")
        monitor.save_metrics_report()
        monitor.create_metrics_chart()
        monitor.print_summary()


if __name__ == "__main__":
    run_stress_test_with_monitoring()