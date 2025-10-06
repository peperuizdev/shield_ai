import os
from pathlib import Path

def find_env_files():
    """Busca todos los archivos .env en el proyecto"""
    
    print("🔍 BUSCANDO ARCHIVOS .env EN EL PROYECTO")
    print("=" * 50)
    
    # Obtener directorio actual del script
    current_dir = Path(__file__).parent.absolute()
    print(f"📁 Directorio actual del script: {current_dir}")
    
    # Buscar hacia arriba hasta encontrar la raíz del proyecto
    search_paths = []
    current = current_dir
    
    # Buscar hasta 5 niveles hacia arriba
    for i in range(6):
        search_paths.append(current)
        parent = current.parent
        if parent == current:  # Llegamos a la raíz del sistema
            break
        current = parent
    
    print(f"\n🔍 Buscando en {len(search_paths)} ubicaciones:")
    
    env_files_found = []
    
    for path in search_paths:
        env_path = path / ".env"
        print(f"  📂 {path}")
        
        if env_path.exists():
            print(f"    ✅ .env ENCONTRADO: {env_path}")
            env_files_found.append(env_path)
            
            # Mostrar contenido (censurado)
            try:
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                
                print(f"    📄 Contenido ({len(lines)} líneas):")
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            censored = value[:6] + '*' * max(0, len(value) - 6)
                            print(f"      {line_num}: {key}={censored}")
                        else:
                            print(f"      {line_num}: {line}")
                    elif line.startswith('#'):
                        print(f"      {line_num}: {line}")
                        
            except Exception as e:
                print(f"    ❌ Error leyendo archivo: {e}")
        else:
            print(f"    ❌ .env no encontrado")
    
    if not env_files_found:
        print(f"\n❌ No se encontraron archivos .env")
        print(f"💡 Sugerencias:")
        print(f"   1. Crear .env en: {current_dir}")
        print(f"   2. O crear .env en: {search_paths[-1]} (raíz del proyecto)")
        
        return None
    else:
        print(f"\n✅ Se encontraron {len(env_files_found)} archivos .env")
        return env_files_found

def show_directory_structure():
    """Muestra la estructura de directorios actual"""
    
    print(f"\n📂 ESTRUCTURA DE DIRECTORIOS:")
    print("-" * 30)
    
    current = Path(__file__).parent.absolute()
    
    # Mostrar estructura hacia arriba
    levels = []
    temp = current
    for _ in range(5):
        levels.append(temp)
        parent = temp.parent
        if parent == temp:
            break
        temp = parent
    
    levels.reverse()
    
    for i, path in enumerate(levels):
        indent = "  " * i
        folder_name = path.name if path.name else str(path)
        
        # Marcar el directorio actual
        marker = " ← AQUÍ ESTÁ EL SCRIPT" if path == current else ""
        print(f"{indent}{folder_name}/{marker}")
        
        # Mostrar archivos importantes en el directorio actual del script
        if path == current:
            try:
                files = list(path.glob("*"))
                py_files = [f for f in files if f.suffix == '.py']
                env_files = [f for f in files if f.name == '.env']
                
                for f in py_files[:3]:  # Mostrar hasta 3 archivos .py
                    print(f"{indent}  └── {f.name}")
                
                for f in env_files:
                    print(f"{indent}  └── {f.name} ✅")
                    
            except:
                pass

def create_sample_env():
    """Crea un archivo .env de ejemplo"""
    
    print(f"\n💾 CREAR ARCHIVO .env DE EJEMPLO")
    print("-" * 35)
    
    current_dir = Path(__file__).parent.absolute()
    env_path = current_dir / ".env"
    
    env_content = """# Configuración de APIs para ShieldAI
GROK_API_KEY=gsk_tu_clave_de_groq_aqui

# APIs alternativas (opcionales)
# OPENAI_API_KEY=sk-tu_clave_de_openai_aqui
# ANTHROPIC_API_KEY=sk-ant-tu_clave_de_anthropic_aqui

# Otras configuraciones
# PII_MODEL=es
# USE_REGEX=true
# LOG_LEVEL=INFO
"""
    
    response = input(f"¿Crear .env en {env_path}? (y/n): ").lower().strip()
    
    if response in ['y', 'yes', 's', 'si']:
        try:
            with open(env_path, 'w') as f:
                f.write(env_content)
            print(f"✅ Archivo .env creado en: {env_path}")
            print(f"📝 Ahora edita el archivo y pon tu API key real de Groq")
            return env_path
        except Exception as e:
            print(f"❌ Error creando archivo: {e}")
            return None
    else:
        print("❌ No se creó el archivo .env")
        return None

if __name__ == "__main__":
    print("🛠️  DIAGNÓSTICO DE UBICACIÓN DE .env")
    print("=" * 60)
    
    # Mostrar estructura
    show_directory_structure()
    
    # Buscar archivos .env
    env_files = find_env_files()
    
    # Si no hay .env, ofrecer crear uno
    if not env_files:
        print(f"\n" + "=" * 60)
        create_sample_env()
    else:
        print(f"\n💡 Para usar uno de los .env encontrados:")
        print(f"   Asegúrate que contenga: GROK_API_KEY=tu_clave_real")