# DocuBuddy Backend

Backend para el asistente de documentación con capacidades RAG (Retrieval-Augmented Generation).

## Características

- **Chat con RAG**: Respuestas basadas en documentación indexada
- **Memoria persistente**: Historial de conversaciones almacenado
- **Retrieval con ChromaDB**: Búsqueda semántica de documentación
- **Integración con OpenAI**: Generación de lenguaje avanzada
- **API REST**: Endpoints para chat y gestión de conversaciones
- **Soporte Docker**: Despliegue fácil con Docker Compose

## Estructura del Proyecto

```
docu-buddy-backend/
├── app/
│   ├── core/               # Configuración central
│   │   └── config.py       # Configuración de la aplicación
│   ├── memory/             # Gestión de memoria
│   │   └── conversation_memory.py  # Almacenamiento de conversaciones
│   ├── models/             # Modelos de datos
│   │   └── schemas.py      # Esquemas Pydantic
│   ├── retrieval/          # Sistema de recuperación
│   │   └── retrieval_service.py   # ChromaDB + embeddings
│   ├── routers/            # Rutas de la API
│   │   └── chat.py         # Endpoints de chat
│   ├── scraper/            # Procesamiento de documentos
│   │   └── document_scraper.py    # Parser de Markdown
│   ├── services/           # Lógica de negocio
│   │   └── chat_service.py         # Servicio principal de chat
│   └── main.py             # Aplicación FastAPI
├── tests/                  # Tests
├── memory/                 # Almacenamiento de conversaciones (creado en runtime)
├── chroma_db/             # Base de datos ChromaDB (creado en runtime)
├── Dockerfile             # Configuración Docker
├── docker-compose.yml     # Orquestación de servicios
├── pyproject.toml         # Dependencias y configuración
└── .env.example           # Variables de entorno ejemplo
```

## Configuración

1. **Copiar archivo de entorno**:
   ```bash
   cp .env.example .env
   ```

2. **Configurar variables de entorno**:
   ```bash
   # Editar .env con tus valores
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Instalación y Ejecución

### Opción 1: Docker Compose (Recomendado)

1. **Iniciar servicios**:
   ```bash
   docker-compose up -d
   ```

2. **Verificar estado**:
   ```bash
   docker-compose ps
   ```

Los servicios estarán disponibles en:
- Backend API: http://localhost:8000
- ChromaDB: http://localhost:8001

### Opción 2: Desarrollo Local

1. **Instalar dependencias**:
   ```bash
   uv sync
   ```

2. **Iniciar ChromaDB** (opcional, se puede usar Docker):
   ```bash
   docker run -p 8001:8000 chromadb/chroma
   ```

3. **Ejecutar aplicación**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## API Endpoints

### Chat
- `POST /api/chat` - Enviar mensaje y obtener respuesta
- `GET /api/history/{conversation_id}` - Obtener historial de conversación
- `DELETE /api/history/{conversation_id}` - Eliminar conversación
- `GET /api/conversations` - Listar todas las conversaciones
- `GET /api/stats` - Estadísticas del sistema

### Sistema
- `GET /` - Mensaje de bienvenida
- `GET /health` - Verificación de estado

## Ejemplos de Uso

### Enviar mensaje
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Cómo funciona la autenticación?",
    "conversation_id": null
  }'
```

### Obtener historial
```bash
curl "http://localhost:8000/api/history/conversation-id"
```

## Desarrollo

### Ejecutar tests
```bash
uv run pytest
```

### Formato de código
```bash
uv run black app/ tests/
```

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key de OpenAI | Requerido |
| `CHROMA_HOST` | Host de ChromaDB | localhost |
| `CHROMA_PORT` | Puerto de ChromaDB | 8001 |
| `DOCS_PATH` | Ruta a documentación | ../docu-buddy-frontend/docs |
| `OPENAI_MODEL` | Modelo OpenAI | gpt-4o-mini |
| `CHUNK_SIZE` | Tamaño de chunks | 1000 |
| `RETRIEVAL_TOP_K` | Resultados de retrieval | 5 |

## Integración con Frontend

El backend está diseñado para integrarse con el frontend en `../docu-buddy-frontend`. Asegúrate de que:

1. El frontend esté configurado para apuntar a `http://localhost:8000`
2. Los CORS estén configurados correctamente (ya incluido)
3. La ruta de documentación apunte a los archivos correctos

## Troubleshooting

### Problemas comunes

1. **Error de conexión a ChromaDB**:
   - Verifica que ChromaDB esté corriendo en el puerto correcto
   - Revisa las variables de entorno `CHROMA_HOST` y `CHROMA_PORT`

2. **Error de API de OpenAI**:
   - Confirma que `OPENAI_API_KEY` sea válida
   - Verifica que el modelo especificado esté disponible

3. **Documentación no encontrada**:
   - Revisa que `DOCS_PATH` apunte a la ubicación correcta
   - Verifica que los archivos tengan formato Markdown

## Logs

Los logs se imprimen en consola y incluyen:
- Indexación de documentos
- Procesamiento de queries
- Errores y advertencias

## Contribución

1. Crear feature branch
2. Implementar cambios con tests
3. Ejecutar `black` y `pytest`
4. Crear Pull Request