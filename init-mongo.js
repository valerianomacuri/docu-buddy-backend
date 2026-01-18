// MongoDB initialization script for DocuBuddy
// This script runs when MongoDB container starts

// Switch to docubuddy database
db = db.getSiblingDB('docubuddy_db');

// Create collections (they will be created automatically by Beanie, but we can set indexes here)
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.conversations.createIndex({ "user_id": 1 });
db.conversations.createIndex({ "created_at": -1 });
db.messages.createIndex({ "conversation_id": 1 });

// Create initial user for development
db.users.insertOne({
    user_id: "default-user",
    created_at: new Date(),
    updated_at: new Date(),
    metadata: {
        source: "docker_init",
        version: "1.0.0"
    }
});

print('MongoDB initialized for DocuBuddy');
print('Created indexes and default user');