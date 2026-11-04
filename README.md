# Sistema de antecedentes y alertas de calidad

## Contenido
- `app.py`: aplicación Streamlit para consultar materiales, órdenes SAP y desvíos.
- `requirements.txt`: dependencias.
- `BASE DE DATOS PARA PRUEBAS..xlsx`: archivo fuente original (copiar aquí para ejecutar la app).
- `Base_datos_calidad_mejorada.xlsx`: Excel con hoja ejecutiva y mejora de coincidencia exacta en la consulta.

## Ejecutar la aplicación
1. Instalar Python 3.10 o superior.
2. Abrir una terminal en esta carpeta.
3. Ejecutar:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Si el archivo fuente no está en la carpeta, cargarlo desde el panel lateral de la aplicación.

## Lógica de negocio
- Relación: `Ordenes procesadas[Número material]` con `Desvios[Código]`.
- Se normalizan espacios y se separan los códigos múltiples de desvíos.
- La búsqueda es por coincidencia exacta de cada código, evitando falsos positivos por coincidencias parciales.
- El sistema muestra antecedentes; no reemplaza la decisión ni la liberación formal de Calidad.

## Consideraciones para producción
- Validar separadores y formatos reales de códigos con el dueño del proceso.
- Definir catálogo oficial de estados y reglas para abiertos/cerrados.
- Agregar controles de calidad de datos, bitácora de actualización y permisos.
- Probar con casos conocidos por Calidad antes de utilizar como control operativo.
