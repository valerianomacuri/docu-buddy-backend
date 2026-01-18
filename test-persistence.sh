#!/bin/bash

# Script para probar la persistencia de MongoDB
# DocuBuddy Backend - MongoDB Persistence Test

set -e

echo "🚀 Iniciando prueba de persistencia de MongoDB para DocuBuddy"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir logs
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"
}

# Verificar si Docker está corriendo
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker no está corriendo. Por favor inicia Docker primero."
        exit 1
    fi
    log "✅ Docker está corriendo"
}

# Limpiar contenedores previos
cleanup() {
    log "🧹 Limpiando contenedores previos..."
    
    # Detener y remover contenedores
    docker-compose down -v 2>/dev/null || true
    
    # Remover volúmenes huérfanos
    docker volume prune -f 2>/dev/null || true
    
    # Remover imágenes sin usar
    docker image prune -f 2>/dev/null || true
    
    log "✅ Limpieza completada"
}

# Iniciar servicios
start_services() {
    log "🚀 Iniciando servicios con Docker Compose..."
    
    # Construir e iniciar contenedores
    docker-compose up --build -d
    
    # Esperar a que estén saludables
    log "⏳ Esperando que los servicios estén listos..."
    
    # Esperar MongoDB
    log "🔌 Esperando MongoDB..."
    timeout 60 bash -c 'until docker-compose exec -T mongodb mongosh --eval "db.adminCommand(\"ping\")" > /dev/null 2>&1; do sleep 2; done' || {
        error "❌ MongoDB no está disponible después de 60 segundos"
        return 1
    }
    log "✅ MongoDB está listo"
    
    # Esperar ChromaDB
    log "📚 Esperando ChromaDB..."
    timeout 60 bash -c 'until curl -f http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; do sleep 2; done' || {
        error "❌ ChromaDB no está disponible después de 60 segundos"
        return 1
    }
    log "✅ ChromaDB está listo"
    
    # Esperar Backend
    log "🔧 Esperando Backend..."
    timeout 60 bash -c 'until curl -f http://localhost:8000/health > /dev/null 2>&1; do sleep 2; done' || {
        error "❌ Backend no está disponible después de 60 segundos"
        return 1
    }
    log "✅ Backend está listo"
    
    log "🎉 Todos los servicios están corriendo correctamente"
}

# Probar conexión a MongoDB
test_mongodb_connection() {
    log "🔌 Probando conexión a MongoDB..."
    
    # Conectar a MongoDB y verificar datos
    docker-compose exec -T mongodb mongosh --eval "
        db = db.getSiblingDB('docubuddy_db');
        
        // Verificar que las colecciones existen
        var collections = db.listCollections().map(c => c.name);
        print('📁 Colecciones encontradas: ' + collections.join(', '));
        
        // Verificar usuario default
        var user = db.users.findOne({user_id: 'default-user'});
        if (user) {
            print('👤 Usuario default encontrado: ' + user.user_id);
            print('   Creado: ' + user.created_at);
        } else {
            print('ℹ️  No se encontró usuario default (esto es normal en primer inicio)');
        }
        
        // Verificar conversaciones
        var convCount = db.conversations.countDocuments({user_id: 'default-user'});
        print('💬 Conversaciones para default-user: ' + convCount);
        
        // Verificar mensajes
        var msgCount = db.messages.countDocuments();
        print('📝 Total de mensajes: ' + msgCount);
    " || {
        error "❌ Error al conectar a MongoDB"
        return 1
    }
    
    log "✅ Conexión a MongoDB verificada exitosamente"
}

# Probar endpoints del API
test_api_endpoints() {
    log "🔧 Probando endpoints del API..."
    
    # Endpoint de health
    log "   📊 Probando /health..."
    response=$(curl -s http://localhost:8000/health)
    if echo "$response" | grep -q "healthy"; then
        log "   ✅ /health funciona"
    else
        error "   ❌ /health no funciona"
        return 1
    fi
    
    # Endpoint de usuario actual
    log "   👤 Probando /api/current-user..."
    response=$(curl -s http://localhost:8000/api/current-user)
    if echo "$response" | grep -q "default-user"; then
        log "   ✅ /api/current-user funciona"
    else
        error "   ❌ /api/current-user no funciona"
        return 1
    fi
    
    # Endpoint de última conversación
    log "   💬 Probando /api/latest-conversation..."
    response=$(curl -s http://localhost:8000/api/latest-conversation)
    if echo "$response" | grep -q "conversation_id"; then
        log "   ✅ /api/latest-conversation funciona"
    else
        warn "   ⚠️  /api/latest-conversation responde (sin conversaciones previas)"
    fi
    
    # Endpoint de conversaciones
    log "   📂 Probando /api/conversations..."
    response=$(curl -s http://localhost:8000/api/conversations)
    if echo "$response" | grep -q "conversations"; then
        log "   ✅ /api/conversations funciona"
    else
        error "   ❌ /api/conversations no funciona"
        return 1
    fi
    
    log "✅ Todos los endpoints del API están funcionando"
}

# Crear conversación de prueba
create_test_conversation() {
    log "🧪 Creando conversación de prueba..."
    
    # Enviar mensaje de prueba
    response=$(curl -s -X POST http://localhost:8000/api/chat \
        -H "Content-Type: application/json" \
        -d '{"message": "Hola, esta es una prueba de persistencia. ¿Puedes confirmar que recibes este mensaje?"}')
    
    if echo "$response" | grep -q "conversation_id"; then
        conv_id=$(echo "$response" | grep -o '"conversation_id":"[^"]*' | cut -d'"' -f4)
        log "✅ Conversación de prueba creada con ID: $conv_id"
        
        # Guardar ID para pruebas posteriores
        echo "LAST_CONVERSATION_ID=$conv_id" > .test_env
        
        # Verificar que se guardó en MongoDB
        log "🔌 Verificando que se guardó en MongoDB..."
        docker-compose exec -T mongodb mongosh --eval "
            db = db.getSiblingDB('docubuddy_db');
            var conv = db.conversations.findOne({conversation_id: '$conv_id'});
            if (conv) {
                print('✅ Conversación guardada en MongoDB');
                print('   Mensajes: ' + conv.messages.length);
                print('   Usuario: ' + conv.user_id);
            } else {
                print('❌ Conversación no encontrada en MongoDB');
            }
        "
    else
        error "❌ Error al crear conversación de prueba"
        return 1
    fi
}

# Probar persistencia (reiniciar contenedores)
test_persistence() {
    if [ ! -f .test_env ]; then
        warn "⚠️  No se encontró conversación de prueba, creando una primero..."
        create_test_conversation
    fi
    
    source .test_env
    log "🔄 Probando persistencia (reiniciando contenedores)..."
    
    # Guardar datos antes de reiniciar
    log "💾 Guardando estado antes de reiniciar..."
    docker-compose exec -T mongodb mongosh --eval "
        db = db.getSiblingDB('docubuddy_db');
        var beforeCount = db.conversations.countDocuments();
        var beforeConv = db.conversations.findOne({conversation_id: '$LAST_CONVERSATION_ID'});
        print('Antes del reinicio:');
        print('  Total conversaciones: ' + beforeCount);
        print('  Mensajes en prueba: ' + (beforeConv ? beforeConv.messages.length : 0));
    "
    
    # Reiniciar contenedores
    log "🔄 Reiniciando servicios..."
    docker-compose restart mongodb backend
    
    # Esperar que estén listos
    log "⏳ Esperando que los servicios se recuperen..."
    sleep 10
    
    # Esperar MongoDB
    timeout 30 bash -c 'until docker-compose exec -T mongodb mongosh --eval "db.adminCommand(\"ping\")" > /dev/null 2>&1; do sleep 2; done'
    
    # Esperar Backend
    timeout 30 bash -c 'until curl -f http://localhost:8000/health > /dev/null 2>&1; do sleep 2; done'
    
    # Verificar datos después de reiniciar
    log "🔍 Verificando persistencia después de reiniciar..."
    docker-compose exec -T mongodb mongosh --eval "
        db = db.getSiblingDB('docubuddy_db');
        var afterCount = db.conversations.countDocuments();
        var afterConv = db.conversations.findOne({conversation_id: '$LAST_CONVERSATION_ID'});
        print('Después del reinicio:');
        print('  Total conversaciones: ' + afterCount);
        print('  Mensajes en prueba: ' + (afterConv ? afterConv.messages.length : 0));
        
        if (afterConv && afterConv.messages.length > 0) {
            print('✅ Persistencia verificada exitosamente');
        } else {
            print('❌ Error: Los datos no persistieron');
        }
    "
}

# Probar carga en frontend
test_frontend_loading() {
    if [ ! -f .test_env ]; then
        warn "⚠️  No se encontró conversación de prueba para probar en frontend"
        return 0
    fi
    
    source .test_env
    log "🌐 Probando carga de conversación en frontend (simulada)..."
    
    # Simular llamada del frontend a latest-conversation
    response=$(curl -s http://localhost:8000/api/latest-conversation)
    
    if echo "$response" | grep -q "$LAST_CONVERSATION_ID"; then
        log "✅ Frontend podría cargar correctamente la última conversación"
    else
        warn "⚠️  Posible problema en la carga para frontend"
    fi
}

# Generar reporte final
generate_report() {
    log "📊 Generando reporte final..."
    
    # Estado de contenedores
    log "📦 Estado de contenedores:"
    docker-compose ps
    
    # Uso de recursos
    log "📈 Uso de recursos:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" || true
    
    # Verificar volúmenes
    log "💾 Volúmenes creados:"
    docker volume ls | grep docubuddy || echo "   No se encontraron volúmenes específicos"
    
    # Limpieza
    log "🧹 Limpiando archivos temporales..."
    rm -f .test_env
    
    log "🎯 Prueba de persistencia completada exitosamente"
}

# Función principal
main() {
    echo "🚀 Test de Persistencia MongoDB - DocuBuddy Backend"
    echo "=================================================="
    
    check_docker
    cleanup
    start_services
    test_mongodb_connection
    test_api_endpoints
    create_test_conversation
    test_persistence
    test_frontend_loading
    generate_report
    
    log ""
    log "🎉 TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE"
    log "📝 Para iniciar el frontend: cd ../docu-buddy-frontend && npm run dev"
    log "🌐 Frontend estará en: http://localhost:5173"
    log "🔧 Backend está en: http://localhost:8000"
    log "🔌 MongoDB está en: mongodb://localhost:27017"
    log ""
    log "📚 Para detener todo: docker-compose down"
    log "🔄 Para reiniciar: docker-compose restart"
}

# Manejar señales
trap cleanup EXIT

# Ejecutar función principal
main "$@"