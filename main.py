import os
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv


def verificar_url_repositorio(url):
    """Verifica si el URL del repositorio es válido usando git ls-remote."""
    try:
        subprocess.run(["git", "ls-remote", url],
                       check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print("URL no válido o no se pudo conectar al repositorio.")
        return False


def obtener_nombre_y_archivos_repositorio(url):
    """Clona el repositorio en una carpeta temporal y obtiene su nombre y archivos."""
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(["git", "clone", "--depth",
                       "1", url, temp_dir], check=True)
        repo_name = Path(temp_dir).name
        archivos = [str(archivo.relative_to(temp_dir))
                    for archivo in Path(temp_dir).rglob('*') if archivo.is_file()]
        return repo_name, archivos


def seleccionar_carpeta_clonacion(default_dir):
    """Permite al usuario seleccionar la carpeta de clonación, usando la predeterminada o creando otra."""
    print(f"\nCarpeta de clonación predeterminada: {default_dir}")
    custom_dir = input(
        "¿Desea cambiar la carpeta de clonación? (s/n): ").strip().lower()

    if custom_dir == 's':
        user_dir = input("Ingrese la ruta de la carpeta deseada: ").strip()

        # Intentar crear la carpeta personalizada y manejar errores
        try:
            os.makedirs(user_dir, exist_ok=True)
            print(f"Carpeta de clonación configurada en: {user_dir}")
            return user_dir
        except PermissionError:
            print("Error: No tienes permisos para crear la carpeta en esa ubicación.")
            return None
        except OSError as e:
            print(
                f"Error: No se pudo crear la carpeta de clonación. Detalles: {e}")
            return None
    return default_dir


def clone_repository(repo_url, destination_folder):
    # Crear la carpeta de destino si no existe
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Ejecutar el comando de clonación de git
    try:
        result = subprocess.run(
            ["git", "clone", repo_url, destination_folder],
            capture_output=True,
            text=True,
            check=True
        )
        print("Repositorio clonado con éxito en:", destination_folder)
    except subprocess.CalledProcessError as e:
        print("Error al clonar el repositorio:", e.stderr)
        return False

    # Listar archivos principales como vista previa
    show_file_preview(destination_folder)
    return True


def show_file_preview(folder_path):
    print("\nVista previa de archivos en el proyecto:")
    for root, dirs, files in os.walk(folder_path):
        # Mostrar solo los archivos principales (en la raíz y carpetas clave)
        if root == folder_path or os.path.basename(root) in ["src", "lib"]:
            for file in files:
                print("- ", os.path.relpath(os.path.join(root, file), folder_path))
    print("\nFinal de la vista previa de archivos.")


def detect_dependencies(project_folder):
    print("\n--- Detectando dependencias ---")
    dependencies = {}

    # Detectar Node.js (buscando package.json)
    package_json_path = os.path.join(project_folder, 'package.json')
    if os.path.exists(package_json_path):
        dependencies['Node.js'] = 'package.json'
        print("Archivo de configuración Node.js detectado (package.json).")

    # Detectar Python (buscando requirements.txt o Pipfile)
    requirements_txt_path = os.path.join(project_folder, 'requirements.txt')
    pipfile_path = os.path.join(project_folder, 'Pipfile')
    if os.path.exists(requirements_txt_path):
        dependencies['Python'] = 'requirements.txt'
        print("Archivo de configuración de Python detectado (requirements.txt).")
    elif os.path.exists(pipfile_path):
        dependencies['Python'] = 'Pipfile'
        print("Archivo de configuración de Python detectado (Pipfile).")

    # Detectar entorno virtual (venv)
    venv_path = os.path.join(project_folder, 'venv')
    if os.path.exists(venv_path):
        dependencies['Python virtual environment'] = 'venv'
        print("Entorno virtual detectado (venv).")

    # Mostrar resumen de las dependencias
    if dependencies:
        print("\n--- Resumen de dependencias detectadas ---")
        for dep, config_file in dependencies.items():
            print(f"{dep} (configurado en: {config_file})")
    else:
        print("No se detectaron dependencias específicas en el proyecto.")

    return dependencies


def install_dependency(dependency_name, install_command, manual_instructions):
    """Intenta instalar una dependencia automáticamente o da instrucciones para instalarla manualmente."""
    print(f"\nSe necesita instalar {dependency_name}.")
    choice = input(f"¿Quieres instalar {
                   dependency_name} automáticamente? (s/n): ").lower()

    if choice == 's':
        try:
            print(f"Instalando {dependency_name}...")
            subprocess.run(install_command, check=True)
            print(f"{dependency_name} se instaló correctamente.")
        except subprocess.CalledProcessError:
            print(f"Error: No se pudo instalar {
                  dependency_name} automáticamente.")
    else:
        print(f"Instrucciones para instalar {dependency_name} manualmente:")
        print(manual_instructions)


def install_required_dependencies(dependencies):
    """Verifica e instala automáticamente las dependencias detectadas en el sistema."""

    # Verificar si git está instalado
    if not shutil.which("git"):
        print("Error: Git no está instalado. Por favor, instala Git y vuelve a intentarlo.")
        return

    # Verificar Node.js y npm
    if 'Node.js' in dependencies:
        if not shutil.which("node") or not shutil.which("npm"):
            install_dependency(
                "Node.js y npm",
                ["npm", "install", "-g", "node"],
                "Visita https://nodejs.org para descargar e instalar Node.js y npm."
            )
        else:
            print("Node.js y npm ya están instalados.")

    # Verificar Python
    if 'Python' in dependencies:
        if not shutil.which("python3"):
            install_dependency(
                "Python",
                ["apt-get", "install", "python3"],
                "Instala Python desde https://www.python.org/ para obtener la versión adecuada."
            )
        if not shutil.which("pip"):
            install_dependency(
                "pip",
                ["python3", "-m", "ensurepip", "--upgrade"],
                "Instala pip con el comando 'python3 -m ensurepip --upgrade' o descarga desde https://pip.pypa.io."
            )

    # Instalar dependencias específicas de Node.js o Python en el proyecto
    project_requirements = {
        "Node.js": ("npm install", "Ejecuta 'npm install' en el directorio del proyecto."),
        "Python": ("pip install -r requirements.txt", "Ejecuta 'pip install -r requirements.txt' en el entorno virtual.")
    }

    for dep, (command, manual_instruction) in project_requirements.items():
        if dep in dependencies:
            print(f"\nPara completar la instalación de {dep}:")
            choice = input(f"¿Quieres ejecutar '{
                           command}' automáticamente? (s/n): ").lower()
            if choice == 's':
                subprocess.run(command, shell=True, check=False)
                print(f"{dep} se configuró correctamente.")
            else:
                print(f"Instrucción: {manual_instruction}")


def setup_python_virtualenv():
    """Crea y activa un entorno virtual en Python si es necesario."""
    if not os.path.exists("venv"):
        print("Creando entorno virtual en Python...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("Entorno virtual creado.")
    else:
        print("El entorno virtual ya existe.")

    # Activar el entorno virtual según el sistema operativo
    if os.name == 'nt':  # Windows
        activate_script = r"venv\Scripts\activate.bat"
    else:  # Unix/macOS
        activate_script = "source venv/bin/activate"

    print(f"Para activar el entorno virtual, ejecute: {activate_script}")


def setup_environment_variables():
    """Configura las variables de entorno desde un archivo .env si está presente."""
    if os.path.exists(".env"):
        print("Cargando variables de entorno desde el archivo .env...")
        load_dotenv(".env")
        print("Variables de entorno configuradas.")
    else:
        print("No se encontró un archivo .env. Puedes crear uno para definir variables de entorno.")


def install_python_dependencies():
    """Instala las dependencias de Python si requirements.txt está presente."""
    if os.path.exists("requirements.txt"):
        print("Se detectó requirements.txt. Instalando dependencias de Python...")
        subprocess.run(["venv/bin/pip", "install", "-r",
                       "requirements.txt"], check=True)
        print("Dependencias de Python instaladas correctamente.")
    else:
        print("No se detectó requirements.txt. Saltando instalación de dependencias de Python.")


def install_node_dependencies():
    """Instala las dependencias de Node.js si package.json está presente."""
    if os.path.exists("package.json"):
        print("Se detectó package.json. Instalando dependencias de Node.js...")
        subprocess.run(["npm", "install"], check=True)
        print("Dependencias de Node.js instaladas correctamente.")
    else:
        print(
            "No se detectó package.json. Saltando instalación de dependencias de Node.js.")


def main():
    print("Bienvenido al asistente de configuración de su entorno de desarrollo.")

    # Paso 1: Solicitar el URL del repositorio
    url = input("Ingrese el URL del repositorio de Git: ").strip()

    # Paso 2: Verificar el URL
    if verificar_url_repositorio(url):
        print("\nURL verificado correctamente.")

        # Paso 3: Obtener el nombre y lista de archivos del repositorio
        nombre, archivos = obtener_nombre_y_archivos_repositorio(url)
        if nombre and archivos:
            print(f"\nNombre del repositorio: {nombre}")
            print("Archivos del repositorio (vista previa de 10 archivos):")
            for archivo in archivos[:10]:
                print(f"  - {archivo}")
        else:
            print(
                "No se pudieron obtener los detalles del repositorio. Proceso terminado.")
            return

        # Paso 4: Seleccionar carpeta de clonación
        carpeta_clonacion = seleccionar_carpeta_clonacion(os.getcwd())
        if carpeta_clonacion:
            print(f"\nEl repositorio se clonará en: {carpeta_clonacion}")
        else:
            print("Error al seleccionar la carpeta de clonación. Proceso terminado.")
            return

        # Paso 5: Confirmación final
        input("\nConfiguración inicial completada. Presione Enter para continuar con la clonación...")

        # Paso 6: Clonar el repositorio en la carpeta seleccionada
        if clone_repository(url, carpeta_clonacion):
            print("Repositorio clonado exitosamente.")

            # Paso 7: Detectar dependencias
            dependencies = detect_dependencies(carpeta_clonacion)

            # Paso 8: Instalar dependencias
            install_required_dependencies(dependencies)

            # Paso 9: Configuración de entorno virtual de Python (si es necesario)
            setup_python_virtualenv()

            # Paso 10: Cargar las variables de entorno desde un archivo .env si está presente
            setup_environment_variables()

            # Paso 11: Instalar las dependencias de Python si requirements.txt está presente
            install_python_dependencies()

            # Paso 12: Instalar las dependencias de Node.js si package.json está presente
            install_node_dependencies()

    else:
        print("Proceso terminado. Verifique el URL e intente de nuevo.")


if __name__ == "__main__":
    main()
