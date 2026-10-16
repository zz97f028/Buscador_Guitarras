<script lang="ts">
  import { onMount } from 'svelte'

  type Fuente = {
    id: string
    portal: string
    titulo: string
    url: string
  }

  type Respuesta = {
    respuesta: string
    fuentes: Fuente[]
  }

  type Turno = {
    id: number
    pregunta: string
    respuesta?: Respuesta
    error?: string
  }

  type Documento = {
    id: string
    titulo: string
    marca: string
    modelo: string
    anio: number | null
    tipo: string
    precio: number
    estado: string
    ciudad: string
    portal: string
    fecha: string
    fragmento: string
    url: string | null
    ficticio: boolean
  }

  type DocumentosResponse = {
    total: number
    documentos: Documento[]
  }

  let page: 'chat' | 'documents' = 'chat'
  let question = ''
  let turns: Turno[] = []
  let isAsking = false
  let chatError = ''

  let documents: Documento[] = []
  let totalDocuments = 0
  let corpusCount = 0
  let isLoadingDocuments = false
  let documentsError = ''
  let searchText = ''
  let brandFilter = ''
  let typeFilter = ''
  let portalFilter = ''
  let selectedDocument: Documento | null = null
  let documentRequestId = 0

  const suggestedQuestions = [
    'Busca una Gibson Les Paul usada y compara precios',
    '¿Qué Fender Stratocaster de segunda mano hay?',
    'Encuentra una guitarra acústica usada en Madrid',
  ]

  onMount(() => {
    void loadDocuments()
  })

  async function readError(response: Response): Promise<string> {
    try {
      const body: { detail?: string } = await response.json()
      if (body.detail) return body.detail
    } catch {
      return `La solicitud ha fallado (${response.status}).`
    }
    return `La solicitud ha fallado (${response.status}).`
  }

  function describeConnectionError(error: unknown, message: string): string {
    if (
      error instanceof TypeError &&
      (message.toLocaleLowerCase('en').includes('fetch') ||
        message.toLocaleLowerCase('en').includes('network'))
    ) {
      return (
        'No se pudo conectar con la API. Comprueba que servidor.py y la interfaz estén ' +
        'ejecutándose y que ambos usen el mismo ACORDE_API_PORT.'
      )
    }
    return message
  }

  async function askQuestion(event?: SubmitEvent): Promise<void> {
    event?.preventDefault()
    const currentQuestion = question.trim()
    if (!currentQuestion || isAsking) return

    const id = Date.now()
    const previousTurns = turns
    question = ''
    chatError = ''
    isAsking = true
    turns = [...turns, { id, pregunta: currentQuestion }]

    const historial = previousTurns.flatMap((turn) => {
      if (!turn.respuesta) return []
      return [
        { role: 'user' as const, content: turn.pregunta },
        { role: 'assistant' as const, content: turn.respuesta.respuesta },
      ]
    }).slice(-20)

    try {
      const response = await fetch('/api/preguntar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pregunta: currentQuestion, historial }),
      })
      if (!response.ok) throw new Error(await readError(response))

      const answer: Respuesta = await response.json()
      turns = turns.map((turn) => (turn.id === id ? { ...turn, respuesta: answer } : turn))
    } catch (error) {
      const rawMessage =
        error instanceof Error ? error.message : 'No se pudo conectar con el servidor.'
      const message = describeConnectionError(error, rawMessage)
      chatError = message
      turns = turns.map((turn) => (turn.id === id ? { ...turn, error: message } : turn))
    } finally {
      isAsking = false
    }
  }

  async function loadDocuments(event?: SubmitEvent): Promise<void> {
    event?.preventDefault()
    const requestId = ++documentRequestId
    const params = new URLSearchParams()
    if (searchText.trim()) params.set('q', searchText.trim())
    if (brandFilter) params.set('marca', brandFilter)
    if (typeFilter) params.set('tipo', typeFilter)
    if (portalFilter) params.set('portal', portalFilter)

    isLoadingDocuments = true
    documentsError = ''
    try {
      const query = params.size ? `?${params.toString()}` : ''
      const response = await fetch(`/api/documentos${query}`)
      if (!response.ok) throw new Error(await readError(response))

      const result: DocumentosResponse = await response.json()
      if (requestId !== documentRequestId) return
      documents = result.documentos
      totalDocuments = result.total
      if (params.size === 0) corpusCount = result.total
    } catch (error) {
      if (requestId !== documentRequestId) return
      const rawMessage =
        error instanceof Error ? error.message : 'No se pudieron cargar los documentos.'
      documentsError = describeConnectionError(error, rawMessage)
    } finally {
      if (requestId === documentRequestId) isLoadingDocuments = false
    }
  }

  function clearFilters(): void {
    searchText = ''
    brandFilter = ''
    typeFilter = ''
    portalFilter = ''
    void loadDocuments()
  }

  function formatPrice(price: number): string {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(price)
  }

  function formatDate(date: string): string {
    return new Intl.DateTimeFormat('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    }).format(new Date(`${date}T00:00:00Z`))
  }

</script>

<svelte:head>
  <title>Acorde · Anuncios de guitarras</title>
  <meta
    name="description"
    content="Consulta anuncios de guitarras y explora las fuentes de cada respuesta."
  />
</svelte:head>

<div class="workspace">
  <aside class="sidebar">
    <a class="brand" href="#consultar" onclick={() => (page = 'chat')}>
      <span class="brand-mark">A</span>
      <span>Acorde</span>
    </a>

    <p class="sidebar-label">Espacio de trabajo</p>
    <nav class="side-nav" aria-label="Navegación principal">
      <button
        class:active={page === 'chat'}
        class="side-link"
        aria-current={page === 'chat' ? 'page' : undefined}
        onclick={() => (page = 'chat')}
      >
        <span class="side-icon" aria-hidden="true">◉</span>
        Consultar
      </button>
      <button
        class:active={page === 'documents'}
        class="side-link"
        aria-current={page === 'documents' ? 'page' : undefined}
        onclick={() => (page = 'documents')}
      >
        <span class="side-icon" aria-hidden="true">▤</span>
        Documentos
      </button>
    </nav>

    <div class="sidebar-spacer"></div>
    <div class="corpus-state">
      <span class="state-dot"></span>
      <div>
        <strong>Biblioteca local</strong>
        {corpusCount} fichas · búsqueda web en Consultar
      </div>
    </div>
    <div class="user-chip">
      <span class="avatar user-avatar">LM</span>
      <span>Lucía M.<small>Cuenta personal</small></span>
    </div>
  </aside>

  <main class="app-main">
    <header class="app-topbar">
      <div class="app-title">
        <span>{page === 'chat' ? 'Conversación' : 'Biblioteca'}</span>
        <h1>{page === 'chat' ? 'Consulta tus próximas guitarras' : 'Fuentes y registros'}</h1>
      </div>
      <div class="topbar-actions">
        <span class="status-pill"><span></span> Fuentes activas</span>
        {#if page === 'chat'}
          <button class="button primary new-chat" onclick={() => document.getElementById('question-input')?.focus()}>
            <span aria-hidden="true">＋</span> Nueva consulta
          </button>
        {/if}
      </div>
    </header>

    {#if page === 'chat'}
      <section class="content chat-page" aria-label="Chat de consulta">
        <div class="notice">
          <span class="notice-icon" aria-hidden="true">i</span>
          <p>
            <strong>Fuentes verificables.</strong> Solo se muestran datos publicados en anuncios
            enlazados. Si un dato no aparece en la ficha original, no se completa.
          </p>
        </div>

        {#if turns.length === 0}
          <div class="welcome">
            <span class="welcome-mark" aria-hidden="true">A</span>
            <p class="eyebrow">Tu asistente de búsqueda</p>
            <h2>Encuentra una guitarra<br />con buenas referencias.</h2>
            <p class="welcome-copy">
              Pregunta por marca, tipo o estado. Cada respuesta incluye los anuncios que la
              respaldan.
            </p>
            <div class="suggestions" aria-label="Preguntas de ejemplo">
              {#each suggestedQuestions as suggestion}
                <button
                  class="suggestion"
                  onclick={() => {
                    question = suggestion
                    document.getElementById('question-input')?.focus()
                  }}
                >
                  <span aria-hidden="true">↗</span>{suggestion}
                </button>
              {/each}
            </div>
          </div>
        {:else}
          <div class="chat-thread" aria-live="polite">
            {#each turns as turn (turn.id)}
              <article class="exchange">
                <div class="turn user-turn">
                  <div class="bubble user-bubble">{turn.pregunta}</div>
                  <span class="avatar user-avatar" aria-label="Lucía">LM</span>
                </div>

                {#if turn.respuesta}
                  <div class="assistant-block">
                    <div class="turn assistant-turn">
                      <span class="avatar assistant-avatar" aria-hidden="true">A</span>
                      <div class:guardrail-bubble={turn.respuesta.fuentes.length === 0} class="bubble assistant-bubble">
                        {#if turn.respuesta.fuentes.length === 0}
                          <span class="guardrail-label">Sin resultados web verificables</span>
                        {/if}
                        <p>{turn.respuesta.respuesta}</p>
                      </div>
                    </div>

                    {#if turn.respuesta.fuentes.length === 0}
                      <div class="guardrail-card">
                        <span aria-hidden="true">↳</span>
                        <div>
                          <strong>No hay fuentes web citadas</strong>
                          <p>
                            No se encontraron anuncios web con fuentes suficientes para contrastar
                            la respuesta.
                          </p>
                        </div>
                      </div>
                    {:else}
                      <section class="sources" aria-label="Fuentes de la respuesta">
                        <h3>Fuentes web consultadas</h3>
                        <div class="source-list">
                          {#each turn.respuesta.fuentes as source (source.id)}
                            <details class="source-card">
                              <summary>
                                <span class="source-id">{source.id}</span>
                                <span class="source-portal">{source.portal}</span>
                                <span class="source-chevron" aria-hidden="true">⌄</span>
                              </summary>
                              <div class="source-content">
                                <strong>{source.titulo}</strong>
                                <a href={source.url} target="_blank" rel="noopener noreferrer">
                                  Ver anuncio original ↗
                                </a>
                              </div>
                            </details>
                          {/each}
                        </div>
                      </section>
                    {/if}
                  </div>
                {:else if turn.error}
                  <div class="turn assistant-turn">
                    <span class="avatar assistant-avatar" aria-hidden="true">A</span>
                    <div class="bubble error-bubble">
                      <strong>No se pudo obtener la respuesta</strong>
                      <p>{turn.error}</p>
                    </div>
                  </div>
                {:else}
                  <div class="turn assistant-turn">
                    <span class="avatar assistant-avatar" aria-hidden="true">A</span>
                    <div class="bubble loading-bubble" role="status">
                      <span class="loading-dots" aria-hidden="true"><i></i><i></i><i></i></span>
                      Buscando anuncios en la web…
                    </div>
                  </div>
                {/if}
              </article>
            {/each}
          </div>
        {/if}

        {#if chatError}
          <p class="inline-error" role="alert">{chatError}</p>
        {/if}

        <form class="composer" onsubmit={askQuestion}>
          <label class="visually-hidden" for="question-input">Buscar anuncios de guitarras en la web</label>
          <textarea
            id="question-input"
            bind:value={question}
            placeholder="Busca guitarras usadas en la web…"
            rows="1"
            maxlength="1000"
            disabled={isAsking}
            onkeydown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void askQuestion()
              }
            }}
          ></textarea>
          <button class="button primary send-button" type="submit" disabled={isAsking || !question.trim()}>
            {isAsking ? 'Consultando…' : 'Consultar'}
            <span aria-hidden="true">↗</span>
          </button>
          <span class="composer-hint">Búsqueda web en tiempo real · las respuestas incluyen fuentes</span>
        </form>
      </section>
    {:else}
      <section class="content documents-page" aria-label="Buscador de documentos">
        <div class="page-intro">
          <div>
            <p class="eyebrow">Biblioteca del corpus</p>
            <h2>Explora los anuncios</h2>
            <p>Fichas guardadas localmente. Para buscar anuncios actuales, usa Consultar.</p>
          </div>
          <span class="demo-badge"><span></span> Fichas guardadas</span>
        </div>

        <div class="metrics" aria-label="Resumen del corpus">
          <article class="metric-card">
            <span class="metric-icon" aria-hidden="true">▤</span>
            <div><strong>{totalDocuments}</strong><span>Anuncios guardados</span></div>
          </article>
          <article class="metric-card">
            <span class="metric-icon green" aria-hidden="true">⌕</span>
            <div><strong>Local</strong><span>Biblioteca de fuentes</span></div>
          </article>
          <article class="metric-card metric-note">
            <span class="metric-icon gold" aria-hidden="true">✳</span>
            <div><strong>Datos de prueba marcados</strong><span>Las fichas ficticias no enlazan a anuncios reales.</span></div>
          </article>
        </div>

        <form class="filters" onsubmit={loadDocuments}>
          <label class="search-field">
            <span>Buscar</span>
            <span class="input-wrap">
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <circle cx="8.8" cy="8.8" r="5.8"></circle>
                <path d="m13.2 13.2 4 4"></path>
              </svg>
              <input bind:value={searchText} type="search" placeholder="Buscar fichas guardadas" />
            </span>
          </label>
          <label>
            <span>Marca</span>
            <select bind:value={brandFilter}>
              <option value="">Todas las marcas</option>
              <option>Alhambra</option>
              <option>Cort</option>
              <option>Cordoba</option>
              <option>Fender</option>
              <option>Gibson</option>
              <option>Gretsch</option>
              <option>Ibanez</option>
              <option>Martin</option>
              <option>PRS</option>
              <option>Takamine</option>
              <option>Taylor</option>
              <option>Yamaha</option>
              <option>Epiphone</option>
              <option>Squier</option>
            </select>
          </label>
          <label>
            <span>Tipo</span>
            <select bind:value={typeFilter}>
              <option value="">Todos</option>
              <option value="acustica">Acústica</option>
              <option value="electrica">Eléctrica</option>
              <option value="clasica">Clásica</option>
            </select>
          </label>
          <label>
            <span>Portal</span>
            <select bind:value={portalFilter}>
              <option value="">Todos</option>
              <option>Datos ficticios</option>
              <option>Hispasonic / Mercasonic</option>
            </select>
          </label>
          <div class="filter-actions">
            <button class="button primary" type="submit" disabled={isLoadingDocuments}>
              Buscar
            </button>
            <button class="button button-quiet" type="button" onclick={clearFilters}>Limpiar</button>
          </div>
        </form>

        <div class="results-bar">
          <p>
            <strong>{totalDocuments}</strong>
            {totalDocuments === 1 ? 'registro encontrado' : 'registros encontrados'}
          </p>
          <span>Ordenados por relevancia</span>
        </div>

        {#if documentsError}
          <div class="empty-state error-state" role="alert">
            <span class="empty-icon" aria-hidden="true">!</span>
            <h3>No se pudieron cargar los documentos</h3>
            <p>{documentsError}</p>
            <button class="button primary" onclick={() => void loadDocuments()}>Reintentar</button>
          </div>
        {:else if isLoadingDocuments && documents.length === 0}
          <div class="empty-state" role="status">
            <span class="loading-dots" aria-hidden="true"><i></i><i></i><i></i></span>
            <p>Cargando anuncios…</p>
          </div>
        {:else if documents.length === 0}
          <div class="empty-state">
            <span class="empty-icon" aria-hidden="true">⌕</span>
            <h3>No hay coincidencias</h3>
            <p>Prueba a quitar algún filtro o a buscar otro modelo.</p>
            <button class="button button-quiet" onclick={clearFilters}>Restablecer filtros</button>
          </div>
        {:else}
          <div class="table-shell">
            <div class="table-scroll">
              <table>
                <caption class="visually-hidden">Anuncios guardados y fichas ficticias identificadas</caption>
                <thead>
                  <tr>
                    <th scope="col">Instrumento</th>
                    <th scope="col">Precio</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Ubicación</th>
                    <th scope="col">Portal · fecha</th>
                    <th scope="col"><span class="visually-hidden">Detalle</span></th>
                  </tr>
                </thead>
                <tbody>
                  {#each documents as document (document.id)}
                    <tr>
                      <td>
                        <div class="instrument-cell">
                          <span class="instrument-glyph" aria-hidden="true">♬</span>
                          <div>
                            <strong>{document.titulo}</strong>
                            <span>{document.anio ?? 'Año no indicado'} · {document.tipo} · {document.id}</span>
                            {#if document.ficticio}
                              <span class="fictional-badge">FICTICIO · DATOS DE PRUEBA</span>
                            {/if}
                          </div>
                        </div>
                      </td>
                      <td class="price-cell">{formatPrice(document.precio)}</td>
                      <td><span class="condition-badge">{document.estado}</span></td>
                      <td>{document.ciudad}</td>
                      <td><strong class="portal-name">{document.portal}</strong><span class="date-cell">{formatDate(document.fecha)}</span></td>
                      <td>
                        <button class="button button-quiet detail-button" onclick={() => (selectedDocument = document)}>
                          Ver ficha
                        </button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      </section>
    {/if}
  </main>
</div>

{#if selectedDocument}
  <div
    class="dialog-backdrop"
    role="presentation"
    onclick={(event) => {
      if (event.target === event.currentTarget) selectedDocument = null
    }}
    onkeydown={(event) => {
      if (event.key === 'Escape') selectedDocument = null
    }}
  >
    <div class="detail-dialog" role="dialog" aria-modal="true" aria-labelledby="detail-title" tabindex="-1">
      <div class="dialog-head">
        <div>
          <p class="eyebrow">
            {selectedDocument.ficticio ? 'Ficha ficticia de demostración' : 'Anuncio guardado'} · {selectedDocument.id}
          </p>
          <h2 id="detail-title">{selectedDocument.titulo}</h2>
        </div>
        <button class="close-button" aria-label="Cerrar ficha" onclick={() => (selectedDocument = null)}>×</button>
      </div>
      <div class="dialog-fields">
        <div><span>Precio</span><strong>{formatPrice(selectedDocument.precio)}</strong></div>
        <div><span>Estado</span><strong>{selectedDocument.estado}</strong></div>
        <div><span>Ubicación</span><strong>{selectedDocument.ciudad}</strong></div>
        <div><span>Portal</span><strong>{selectedDocument.portal}</strong></div>
      </div>
      <div class="original-fragment">
        <span>{selectedDocument.ficticio ? 'Descripción ficticia' : 'Resumen del anuncio'}</span>
        <blockquote>{selectedDocument.fragmento}</blockquote>
      </div>
      {#if selectedDocument.url}
        <a
          class="button button-quiet original-link"
          href={selectedDocument.url}
          target="_blank"
          rel="noopener noreferrer"
        >Abrir anuncio original ↗</a>
      {:else}
        <p class="fictional-notice">Esta ficha es inventada para pruebas; no existe un anuncio original.</p>
      {/if}
      <div class="dialog-footer">
        <span>{selectedDocument.ficticio ? 'Fecha de demostración' : 'Publicado el'} {formatDate(selectedDocument.fecha)}</span>
        <button
          class="button primary"
          onclick={() => {
            question = `Busca anuncios actuales de ${selectedDocument?.marca} ${selectedDocument?.modelo}`
            page = 'chat'
            selectedDocument = null
          }}>Buscar anuncios similares</button
        >
      </div>
    </div>
  </div>
{/if}
