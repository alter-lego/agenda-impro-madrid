# Plan: Agenda Impro Madrid

**Objetivo:** Construir una agenda automatizada de shows, talleres y muestras de teatro de improvisación en Madrid ciudad, sin depender de que las escuelas o compañías envíen su información activamente.

---

## Contexto

Existe un referente en el ecosistema ([MadridImprovisa](https://madridimprovisa.com)) pero su modelo depende de que las propias escuelas le comuniquen sus eventos. Este proyecto elimina esa dependencia mediante scraping automatizado de fuentes primarias.

Alcance: **Madrid ciudad**. Se excluyen cursos regulares de duración superior a 3 semanas. Se incluyen shows, talleres, workshops y muestras de fin de curso.

---

## Arquitectura: tres capas de recolección

### Capa 1 — Espacios y salas (scraping semanal)

Fuente directa: los espacios donde se hace impro siempre publican su programación completa porque es su negocio principal. Son HTML estático, fáciles de raspar y muy estables.

**Fuentes iniciales (15):**

| Sala / Espacio | URL cartelera |
|---|---|
| La Escalera de Jacob | `laescaleradejacob.es/cartelera/buscador/improvisacion/` |
| Teatro Maravillas | `teatromaravillas.com` |
| Teatro Asura | `teatroasura.com/cartelera/` |
| Sala WIT | `wit.es` o sección de agenda |
| Collage Burlesque | agenda propia |
| La Sala de la Impro | agenda propia |
| Teatro Sofía | `teatrosofia.es` |
| SOJO Laboratorio Teatral | agenda propia |
| Espacio Broadway | agenda propia |
| Salto Escénico | `saltoescenico.com` |
| El Pasillo Verde | `elpasilloverdeteatro.com` |
| Teatro Victoria | agenda propia |
| La Íntegra Teatro | agenda propia |
| El Club de la Impro | `elclubdelaimpro.com` |
| ImproMadrid | `impromadrid.com/agenda` |

**Filtrado:** cada scraper filtra por palabras clave: `impro`, `improvisación`, `muestra`, `taller`, `workshop`.

**Cobertura estimada:** 70–80% del total de eventos.

---

### Capa 2 — Plataformas de venta de entradas (scraping semanal)

Búsqueda semanal con el término `impro` en Madrid ciudad en cada plataforma. Aporta datos ya estructurados (fecha exacta, precio, duración) y actúa de red de seguridad cuando un scraper de Capa 1 falla.

**Fuentes:**

| Plataforma | URL de búsqueda |
|---|---|
| Atrápalo | `atrapalo.com/entradas/madrid/madrid/teatro-y-danza/impro/` |
| Entradas.com | búsqueda por keyword `improvisación` + ciudad Madrid |
| Giglon | búsqueda por keyword |
| Billetweb | búsqueda por keyword |

**Ventaja clave:** HTML estático, estructura muy estable, precio e información de entradas incluida.

---

### Capa 3 — Instagram (scraping semanal)

Captura muestras de fin de curso, talleres puntuales y eventos que las escuelas anuncian solo en redes antes de abrir venta. Es la capa que cubre lo que las otras dos no ven.

**Cuentas a monitorizar:** las 15 escuelas identificadas más las compañías principales con actividad regular.

**Herramienta:** [Apify Instagram Scraper](https://apify.com/apidojo/instagram-scraper). Coste estimado: gratuito o ~2–3 €/mes con el plan free tier.

**Procesado:** los posts de cada cuenta se pasan por un LLM ligero (Claude Haiku) con un prompt que extrae: título del evento, fecha, lugar y tipo (show / taller / muestra). Solo se llama al LLM cuando hay posts nuevos, lo que minimiza el coste en tokens.

---

## Gestión dinámica de fuentes

El sistema no debe requerir intervención técnica para añadir o eliminar fuentes.

### Auto-descubrimiento

Un job semanal independiente raspa la [página de escuelas de MadridImprovisa](https://madridimprovisa.com/escuelas/) y la [página de compañías](https://madridimprovisa.com/companias/) y compara con las fuentes ya registradas. Si aparece una entrada nueva, el sistema:

1. Busca automáticamente su web e Instagram mediante una búsqueda en Google.
2. La añade al registro como candidata con estado `pendiente_validación`.
3. Envía una notificación para revisión humana opcional (no bloqueante).

Adicionalmente, cuando la Capa 2 detecta en Atrápalo un organizador nuevo que no está en el registro, lo añade como candidato de la misma manera.

### Registro de fuentes

Una hoja de cálculo (Google Sheets) con estas columnas:

| Campo | Descripción |
|---|---|
| `nombre` | Nombre de la sala / escuela / compañía |
| `tipo` | `sala`, `plataforma` o `instagram` |
| `url` | URL a raspar |
| `activa` | `sí` / `no` — desactivar sin borrar |
| `capa` | `1`, `2` o `3` |
| `notas` | Observaciones, cambios de URL, etc. |

Los scrapers leen esta hoja antes de ejecutarse. Añadir una fuente = añadir una fila. Desactivar = cambiar `activa` a `no`. Sin tocar código.

---

## Base de datos central

Todos los scrapers escriben en una única base de datos. Para el POC es suficiente con **Airtable** (plan gratuito, interfaz visual, API incluida). Para producción, una base PostgreSQL simple.

**Esquema de evento:**

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Hash del título + fecha (para deduplicación) |
| `titulo` | string | Nombre del evento |
| `tipo` | string | `show`, `taller`, `muestra`, `workshop` |
| `fecha_inicio` | date | |
| `fecha_fin` | date | Null si es fecha única |
| `hora` | time | Si se conoce |
| `sala` | string | |
| `direccion` | string | |
| `precio` | string | |
| `url_entradas` | string | Enlace de compra si existe |
| `url_info` | string | Enlace a más información |
| `fuente` | string | Qué scraper lo encontró |
| `creado_en` | datetime | |
| `actualizado_en` | datetime | |

**Deduplicación:** por hash de `normalize(título) + fecha_inicio`. Si el mismo evento aparece en varias fuentes, se enriquece el registro (p.ej. se añade precio desde Atrápalo si la Capa 1 no lo tenía).

---

## Stack técnico recomendado

| Componente | Tecnología | Justificación |
|---|---|---|
| Scrapers Capa 1 y 2 | Python + `requests` + `BeautifulSoup` | Ambas fuentes son HTML estático, sin JS rendering necesario |
| Scraper Capa 3 | Apify (servicio gestionado) | Evita gestionar autenticación de Instagram |
| Parsing posts Instagram | Claude Haiku via API | Más barato; solo para texto no estructurado |
| Registro de fuentes | Google Sheets | Sin código para operativa diaria |
| Base de datos | Airtable (POC) / PostgreSQL (prod) | |
| Scheduler | GitHub Actions (cron semanal) | Gratuito, sin infraestructura propia |
| Output POC | Archivo JSON + HTML estático | Sin servidor necesario |

---

## Fases del proyecto

### Fase 1 — POC (1–2 semanas)
- Scraper funcional para Atrápalo (Capa 2) completo.
- Scraper para 2–3 salas de Capa 1 (La Escalera de Jacob + una más).
- Deduplicación básica por título normalizado.
- Output: JSON + HTML estático con la agenda de la semana.
- **Criterio de éxito:** capturar >80% de los eventos visibles en MadridImprovisa sin intervención manual.

### Fase 2 — Cobertura completa (2–4 semanas)
- Scrapers para las 15 salas de Capa 1.
- Registro de fuentes en Google Sheets operativo.
- Auto-descubrimiento desde MadridImprovisa activado.
- Base de datos en Airtable.
- Scheduler semanal en GitHub Actions.

### Fase 3 — Capa 3 + enriquecimiento (2–3 semanas)
- Integración Apify para Instagram de las 15 escuelas.
- Parsing de posts con Claude Haiku.
- Clasificación automática de tipo de evento (show / taller / muestra).

### Fase 4 — Salida pública (a definir)
- Formato de difusión a decidir: web, newsletter, Telegram, Instagram, API/RSS.
- Sin capa editorial por ahora.

---

## Agente de auditoría

Antes de que cualquier scraper escriba en la base de datos central, un agente de auditoría independiente revisa el output generado. Su función es detectar problemas que el scraper no puede ver por sí mismo.

**Qué audita:**

| Comprobación | Descripción |
|---|---|
| Completitud | ¿El scraper devolvió 0 resultados? Puede indicar que la web cambió su estructura |
| Formato de fechas | Fechas mal parseadas, fechas en el pasado, rangos incoherentes |
| Campos obligatorios | Eventos sin título, sin sala o sin fecha |
| Duplicados | Entradas con el mismo hash antes de escribir en BD |
| Anomalías de precio | Precios negativos, formatos inesperados, ausencia masiva de precios |
| Eventos fuera de alcance | Eventos fuera de Madrid ciudad o cursos regulares (>3 semanas) que se hayan colado |

**Cuándo se ejecuta:** después de cada job de scraping, antes del paso de escritura en base de datos.

**Output del agente:** un archivo `audit.json` por ejecución con esta estructura:

```json
{
  "fecha_ejecucion": "2026-05-24T08:00:00",
  "fuente": "atrapalo",
  "eventos_recibidos": 40,
  "eventos_validos": 38,
  "alertas": [
    { "tipo": "fecha_pasada", "evento": "Jamming", "detalle": "fecha_inicio: 2026-04-01" },
    { "tipo": "campo_vacio", "evento": "Impro X", "detalle": "sala vacía" }
  ],
  "bloqueado": false
}
```

Si el número de alertas supera un umbral configurable, el agente bloquea la escritura en BD y notifica. Si son alertas menores, escribe igualmente pero las registra.

**Implementación:** función Python pura, sin LLM. Las comprobaciones son reglas deterministas: rápidas, baratas y predecibles.

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Una sala rediseña su web y rompe el scraper | Media | Capa 2 actúa de red de seguridad; alerta automática cuando un scraper devuelve 0 resultados |
| Instagram restringe el acceso | Alta | Apify abstrae esto; en último caso, revisión manual semanal de cuentas clave |
| Evento aparece duplicado | Media | Deduplicación por hash; revisión manual de casos ambiguos en Airtable |
| Escuela nueva no detectada | Baja | Auto-descubrimiento semanal desde MadridImprovisa |

---

## Output: web pública sin costes

### Propuesta

**GitHub Pages + GitHub Actions** es la opción más natural dado que el scheduler ya vive en GitHub Actions. El mismo flujo que ejecuta los scrapers genera el HTML y lo publica automáticamente. Coste: **0 €**.

### Cómo funciona

```
GitHub Actions (cron semanal)
  │
  ├── 1. Ejecuta scrapers (Capa 1 + 2 + 3)
  ├── 2. Ejecuta agente de auditoría → audit.json
  ├── 3. Genera agenda_impro_madrid.html + .json
  └── 4. Publica en rama gh-pages → web live
```

La web queda publicada automáticamente en:
`https://alter-lego.github.io/agenda-impro-madrid`

Sin servidor, sin base de datos en producción, sin factura.

### Stack de la web

| Elemento | Solución | Coste |
|---|---|---|
| Hosting | GitHub Pages | Gratis |
| CI/CD | GitHub Actions | Gratis |
| Dominio | `github.io` subdomain | Gratis |
| Framework web | HTML estático generado por el scraper | — |
| CSS | Hoja de estilos interna, sin dependencias externas | — |

### Estructura mínima de la web

Una sola página con:
- Cabecera con nombre, fecha de última actualización y número de eventos.
- Filtros simples: por tipo (show / taller / muestra) y por fecha (esta semana / próximo mes).
- Tabla o lista de eventos con: título, fecha, hora, sala, precio y enlace de entradas.
- Pie con enlace al JSON para quien quiera consumir los datos.

No requiere JavaScript para funcionar. Los filtros pueden implementarse con JS ligero o simplemente con páginas separadas generadas estáticamente.

### Flujo de actualización

Cada lunes a las 8:00 (o la hora que se configure), GitHub Actions:
1. Raspa las fuentes.
2. Audita el output.
3. Regenera el HTML.
4. Hace commit a `gh-pages` y la web se actualiza en segundos.

El repositorio puede ser privado (el código) con `gh-pages` público (solo la web).

---

## Lo que este sistema NO cubre (por diseño)

- Cursos regulares de duración superior a 3 semanas.
- Eventos fuera de Madrid ciudad.
- Capa editorial (resúmenes, recomendaciones, textos).
- Venta de entradas propia.
