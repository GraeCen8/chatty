#!/bin/bash

# Base URL
BASE_URL="http://localhost:8001"
TIMESTAMP=$(date +%s)
USERNAME="testuser_$TIMESTAMP"
EMAIL="test_$TIMESTAMP@example.com"
PASSWORD="testpassword"

echo "1. Creating user ($USERNAME)..."
CREATE_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/users/create" \
     -H "Content-Type: application/json" \
     -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\", \"email\": \"$EMAIL\"}")
echo $CREATE_USER_RESPONSE | jq .

echo -e "\n2. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/users/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=$USERNAME&password=$PASSWORD")
echo $LOGIN_RESPONSE | jq .

TOKEN=$(echo $LOGIN_RESPONSE | jq -r .access_token)

if [ "$TOKEN" == "null" ]; then
    echo "Login failed, exiting."
    exit 1
fi

echo -e "\n3. Creating a room..."
ROOM_RESPONSE=$(curl -s -X POST "$BASE_URL/rooms/create" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"name": "Test Room '$TIMESTAMP'"}')
echo $ROOM_RESPONSE | jq .

ROOM_ID=$(echo $ROOM_RESPONSE | jq -r .id)

echo -e "\n4. Getting all rooms..."
curl -s -X GET "$BASE_URL/rooms" \
     -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n5. Joining the room (Room ID $ROOM_ID)..."
curl -s -X POST "$BASE_URL/rooms/$ROOM_ID/join" \
     -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n6. Creating a message (Room ID $ROOM_ID)..."
MESSAGE_RESPONSE=$(curl -s -X POST "$BASE_URL/messages/create" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d "{\"room_id\": $ROOM_ID, \"content\": \"Hello world from $USERNAME!\"}")
echo $MESSAGE_RESPONSE | jq .

MESSAGE_ID=$(echo $MESSAGE_RESPONSE | jq -r .id)

echo -e "\n7. Getting room users..."
curl -s -X GET "$BASE_URL/rooms/$ROOM_ID/users" \
     -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n8. Getting room messages..."
curl -s -X GET "$BASE_URL/rooms/$ROOM_ID/messages" \
     -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n9. Deleting message (ID $MESSAGE_ID)..."
curl -s -X DELETE "$BASE_URL/messages/$MESSAGE_ID" \
     -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n10. Leaving room..."
curl -s -X DELETE "$BASE_URL/rooms/$ROOM_ID/leave" \
     -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n11. Deleting room..."
curl -s -X DELETE "$BASE_URL/rooms/$ROOM_ID" \
     -H "Authorization: Bearer $TOKEN" | jq .
