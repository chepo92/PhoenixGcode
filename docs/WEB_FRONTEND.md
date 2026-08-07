# Frontend Oficial Web & Modelo de Workspace

## 1. Visión General
El frontend estático ubicado en `frontends/web/` constituye la implementación oficial del entorno web para **PhoenixGCode**.

Está diseñado para ejecutarse 100% en el cliente mediante **Pyodide (WebAssembly)** consumiendo el wheel oficial distribuido por la biblioteca, garantizando que todo procesamiento permanezca local y privado.

---

## 2. Modelo de Workspace
El **Workspace** representa una sesión de trabajo sobre un único archivo G-code. Define la organización lógica estándar que deberán compartir todos los frontends del proyecto (Web, Cura, OctoPrint, Print2Go):

```text
+-----------------------------------------------------------------------+
|                         PHOENIXGCODE WORKSPACE                        |
+-------------------+-------------------------------+-------------------+
|  1. ARCHIVO       |  2. INFORMACIÓN DEL CORE      |  3. BENCHMARK     |
|  - Drag & Drop    |  - Capas, Líneas, Z-Range     |  - Tiempos WASM   |
|  - Selector File  |  - Extrusión y Temperaturas   |  - Memoria RAM    |
+-------------------+-------------------------------+-------------------+
|  4. HERRAMIENTAS  |  5. CONSOLA DE EVENTOS        |  6. INSPECTOR API |
|  - Analyze        |  - Logs y Errores             |  - Árbol JSON     |
|  - Recover (Des)  |  - Exportar/Copiar            |    PhoenixGCode   |
+-------------------+-------------------------------+-------------------+


## 5. Recovery Workspace
La funcionalidad de **Recovery** permite reanudar una impresión 3D fallida desde una altura Z determinada.

### Flujo de Interacción
```text
[ Archivo Cargado ]
       │
       ▼ (1. Analyze)
[ PhoenixGCodeAPI.analyze_file ]
       │
       ▼ (2. Configurar Z)
[ PhoenixGCodeAPI.build_recovery_plan(target_z) ]
       │
       ▼ (3. Selección de Capa & Configuración)
[ PhoenixGCodeAPI.generate_recovery_gcode(...) ]
       │
       ▼ (4. Preview & Download)
[ Descarga de recovery_<filename>.gcode en el Navegador ]
