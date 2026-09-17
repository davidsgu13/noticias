# Radar CO — Mercado financiero colombiano

Panel web que se actualiza solo, todos los días, con noticias del mercado
financiero colombiano recopiladas desde varias fuentes (Valora Analitik,
El Tiempo - Economía, Portafolio, La República, Bloomberg Línea, y
búsquedas específicas en Google News sobre BVC, TRM/dólar, Banco de la
República, PIB/inflación y renta fija).

https://davidsgu13.github.io/noticias/

No hay servidor ni base de datos: un script de Python corre dentro de
**GitHub Actions**, arma `data/news.json`, lo sube al repositorio, y
**GitHub Pages** sirve el HTML que lee ese archivo. Todo gratis, sin que
tengas que tocar nada después de configurarlo una vez.

## Cómo se actualiza solo

1. GitHub Actions ejecuta `scripts/fetch_news.py` dos veces al día
   (5:00 a.m. y 3:00 p.m. hora Bogotá) según `.github/workflows/update-news.yml`.
2. El script descarga los feeds, quita duplicados, descarta lo que tiene
   más de 4 días, y guarda el resultado en `data/news.json`.
3. Si hay cambios, la acción hace commit y push automáticamente.
4. GitHub Pages siempre sirve la última versión de `index.html` +
   `data/news.json` — no necesitas reconstruir nada manualmente.

También puedes forzar una actualización en cualquier momento desde
**Actions → Actualizar noticias del mercado → Run workflow**.

## Puesta en marcha (una sola vez)

1. **Crea un repositorio nuevo en GitHub** (público, para poder usar
   GitHub Pages gratis) y sube todo este contenido:

   ```bash
   cd radar-co
   git init
   git add .
   git commit -m "Primera versión de Radar CO"
   git branch -M main
   git remote add origin https://github.com/davidsgu13/TU-REPO.git
   git push -u origin main
   ```

2. **Dale permiso de escritura a las Actions** (para que puedan hacer
   commit del JSON):
   `Settings → Actions → General → Workflow permissions` →
   selecciona **"Read and write permissions"** → Save.

3. **Activa GitHub Pages**:
   `Settings → Pages` → en *Build and deployment*, source:
   **"Deploy from a branch"** → branch: **main**, carpeta **/(root)** → Save.
   GitHub te dará una URL como `https://davidsgu13.github.io/TU-REPO/`.

4. **Corre el flujo una primera vez a mano** para llenar `data/news.json`
   sin esperar al cron: `Actions → Actualizar noticias del mercado →
   Run workflow`. Cuando termine (1–2 min), refresca la página de Pages.

Desde ahí, todo corre solo.

## Estructura

```
index.html              → la página (masthead, filtros, tarjetas de noticias)
assets/style.css         → estilos
assets/app.js             → lee data/news.json y pinta las tarjetas
data/news.json             → generado automáticamente, no lo edites a mano
scripts/fetch_news.py       → recolector: RSS directos + Google News
.github/workflows/update-news.yml → el cron que lo hace automático
requirements.txt
```

## Personalizar las fuentes o temas

Todo está en `scripts/fetch_news.py`:

- `DIRECT_FEEDS`: feeds RSS directos de medios. Si uno deja de funcionar
  (los medios cambian sus URLs de vez en cuando) simplemente se ignora;
  no rompe el resto. Puedes agregar o quitar entradas ahí.
- `GOOGLE_NEWS_QUERIES`: cada entrada es una búsqueda en Google News en
  español para Colombia. Es la fuente más confiable porque agrega
  automáticamente decenas de medios sin que dependas de que un sitio
  puntual mantenga vivo su RSS. Puedes ajustar las consultas (`"q"`) a
  los temas que más te interesen (p. ej. tu operación de MYLION —
  aranceles, importaciones, dólar — o valoración de empresas).
- `MAX_ITEMS` y `MAX_AGE_DAYS` controlan cuántas noticias se guardan y
  qué tan viejas pueden ser.

Después de editar el script, con un `git push` a `main` se dispara solo
(el workflow también corre en cada push a `scripts/fetch_news.py`).

## Notas

- Esto no es asesoría financiera, es un lector rápido de titulares.
- Si algún feed cambia de URL y deja de traer noticias, revisa los
  logs en la pestaña **Actions** — cada fuente rota imprime un aviso
  ahí, pero no detiene al resto.
