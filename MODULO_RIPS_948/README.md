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
4. Complete el encabezado (Caja, REL, Radicado, fechas, Periodo) → **Aplicar a todos**. La **Fecha factura** se edita por fila en la grilla.
5. Marque **Exportar** en las filas que irán al Excel.
6. **Exportar Excel**: solo registros marcados.

## Configuración

## Origen de los datos (Res. 948)

| Columna relación | Dónde está según norma |
|------------------|-------------------------|
| **Fecha factura** | No está en el objeto transacción RIPS (T01–T04). Se toma de la **FEV**: `informacion_documento.fecha_documento`, `facturas[].encabezado.fecha`, o del **XML** asociado (`IssueDate`). |
| **Nombre IPS** | No viene en el bloque `usuarios`. Se toma de metadatos del emisor en JSON (`razonSocial`, `nombrePrestador`, etc.) o del **XML FEV** (`RegistrationName` del prestador). |
| **Nombre paciente** | El bloque usuario RIPS (U01–U12) **no incluye nombre** en el Anexo Técnico 1. Si su software lo envía, se leen campos como `primerNombre`/`primerApellido` o objeto `nombre` tipo FEV. |

Coloque el **XML o JSON de la factura** en la misma carpeta que los RIPS, o use el botón **Cargar datos factura**. El cruce se hace por **número de factura** (`numFactura` en RIPS = `numero_documento` / `ID` en FEV).

### Orden recomendado

1. **Buscar RIPS (JSON)** — seleccione los archivos RIPS reales.
2. **Cargar datos factura** — seleccione XML/JSON de la FEV (misma carpeta o otra).
3. El estado muestra **Facturas (datos FEV): N** cuando hay metadatos indexados.
4. Validar y exportar.

## Generar EXE (Windows)

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name ModuloRIPS948 app.py
```

El ejecutable queda en `dist/ModuloRIPS948/`. Copie junto a la carpeta `templates/` y `config.json`.

## Estructura de columnas Excel

CAJA, RADICADO, FECHA RADICADO, PERIODO FACTURADO, Fecha factura, FECHAING, FECHAFIN, CodIps, NombreIps, NroFac, TipoIde, NumIde, Nombre, VlorNeto, SERVICIO, REL, NACION.
