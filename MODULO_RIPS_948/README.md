# Módulo RIPS — Relación Resolución 948

Aplicación de escritorio local (sin internet ni base de datos) para:

1. Cargar uno o varios archivos RIPS en JSON (o una carpeta completa).
2. Validar estructura y reglas básicas conforme a la Resolución 948.
3. Completar datos administrativos (Caja, Radicado, fechas, Periodo, REL).
4. Exportar la relación a Excel con la plantilla oficial de columnas.

## Requisitos

- Python 3.10 o superior (recomendado 3.12).
- Windows 10/11 para el ejecutable; la app también corre en Linux/macOS para pruebas.

## Instalación

```bash
cd MODULO_RIPS_948
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_template.py
```

## Ejecución

```bash
python app.py
```

## Uso

1. **Buscar RIPS (JSON)** o **Buscar carpeta**: seleccione archivos `.json`.
2. **Validar**: muestra el resultado en el panel inferior y en *Resultado RIPS*.
3. **Ver resultado / errores**: ventana con detalle del informe.
4. Complete el encabezado administrativo y use **Aplicar a todos** o marque **Aplicar** en cada fila de la grilla.
5. **Exportar Excel**: genera el archivo con el orden de columnas de la plantilla.
6. **Descargar informe**: guarda el informe de validación en `.txt`.

## Configuración

En `config.json` puede mapear códigos IPS a nombre:

```json
{
  "nombre_ips_por_codigo": {
    "230010048201": "Nombre de la IPS"
  }
}
```

## Generar EXE (Windows)

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name ModuloRIPS948 app.py
```

El ejecutable queda en `dist/ModuloRIPS948/`. Copie junto a la carpeta `templates/` y `config.json`.

## Estructura de columnas Excel

CAJA, RADICADO, FECHA RADICADO, PERIODO FACTURADO, Fecha factura, FECHAING, FECHAFIN, CodIps, NombreIps, NroFac, TipoIde, NumIde, Nombre, VlorNeto, SERVICIO, REL, NACION.
