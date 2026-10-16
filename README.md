# Acorde · buscador de guitarras usadas

Acorde permite consultar anuncios de guitarras de segunda mano mediante un chat con fuentes web y explorar una biblioteca local en la pestaña **Documentos**. La búsqueda web usa OpenAI Responses API desde el servidor; la clave permanece en `.env` y no se envía al navegador.

## Datos

La búsqueda del chat consulta la web en tiempo real y presenta las citas recibidas. La biblioteca local contiene un anuncio de Hispasonic y 20 fichas ficticias, identificadas como demostración. Estas fichas no son anuncios reales ni resultados de búsqueda.

## Arranque en Windows

Configura `OPENAI_API_KEY` en `.env`. En una terminal, arranca la API:

```powershell
$env:ACORDE_API_PORT = "8001"
uv run servidor.py
```

En otra terminal, arranca Svelte/Vite:

```powershell
cd web
npm install  # solo la primera vez
$env:ACORDE_API_PORT = "8001"
npm run dev
```

Abre <http://localhost:5173>. La variable `ACORDE_API_PORT` debe coincidir en ambas terminales; aquí se usa 8001 porque el puerto 8000 está ocupado.

## Consultas de comprobación

Las tres consultas de ejemplo de las maquetas:

- `Quiero buscar finalmente una guitarra electrica gibson en buen estado`
- `Quiero buscar finalmente una guitarra acustica martin en buen estado`
- `Quiero buscar finalmente una guitarra electrica fender en buen estado.`

Caso que la maqueta presenta como fuera de alcance: `¿Qué tiempo hará mañana en Madrid?`. La prueba automatizada verifica el comportamiento sin fuentes mediante una respuesta simulada sin citas; una consulta web en vivo puede encontrar fuentes y responder, por lo que no se garantiza que esa pregunta concreta quede sin respuesta.

## Entregable

[Informe A4 de validación (PDF)](entregable.pdf)
