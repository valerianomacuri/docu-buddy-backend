#!/bin/bash

# Script simple para probar el fix de ChatService
echo "🔧 Testing ChatService fix..."

# Iniciar solo backend y mongodb
docker-compose up -d mongodb backend

# Esperar 10 segundos
echo "⏳ Waiting for services..."
sleep 10

# Probar el endpoint que estaba fallando
echo "🧪 Testing /api/conversations endpoint..."
response=$(curl -s http://localhost:8000/api/conversations)

if echo "$response" | grep -q "conversations"; then
    echo "✅ /api/conversations works!"
else
    echo "❌ /api/conversations failed"
    echo "Response: $response"
    exit 1
fi

# Probar latest-conversation
echo "🧪 Testing /api/latest-conversation..."
response=$(curl -s http://localhost:8000/api/latest-conversation)

if echo "$response" | grep -q "conversation_id"; then
    echo "✅ /api/latest-conversation works!"
else
    echo "❌ /api/latest-conversation failed"
    echo "Response: $response"
    exit 1
fi

echo "🎉 All endpoints working!"
echo "📝 You can now start the frontend:"
echo "   cd ../docu-buddy-frontend && npm run dev"