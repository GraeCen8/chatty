<script>
    import { onMount, onDestroy } from "svelte";
    import { token, user } from "../stores";

    let rooms = [];
    let selectedRoom = null;
    let messages = [];
    let newMessage = "";
    let newRoomName = "";
    let addUserUsername = "";
    let allUsers = [];
    let roomUsers = [];
    let ws;
    let error = "";

    $: if ($token && !selectedRoom) {
        loadRooms();
    }

    async function loadRooms() {
        try {
            const res = await fetch("http://localhost:8000/rooms", {
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (!res.ok) throw new Error("Failed to load rooms");
            rooms = await res.json();
            // Backend in main.py line 173: return rooms (List[RoomRead])
        } catch (e) {
            error = e.message;
        }
    }

    async function selectRoom(room) {
        selectedRoom = room;
        messages = [];
        await loadMessages(room.id);
        await loadRoomUsers(room.id);
        await loadAllUsers();
        connectWebSocket();
    }

    async function loadRoomUsers(roomId) {
        try {
            const res = await fetch(
                `http://localhost:8000/rooms/${roomId}/users`,
                {
                    headers: { Authorization: `Bearer ${$token}` },
                },
            );
            if (!res.ok) throw new Error("Failed to load room users");
            roomUsers = await res.json();
        } catch (e) {
            error = e.message;
        }
    }

    async function loadAllUsers() {
        try {
            const res = await fetch(`http://localhost:8000/users`, {
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (!res.ok) throw new Error("Failed to load users");
            allUsers = await res.json();
        } catch (e) {
            error = e.message;
        }
    }

    async function loadMessages(roomId) {
        try {
            const res = await fetch(
                `http://localhost:8000/rooms/${roomId}/messages`,
                {
                    headers: { Authorization: `Bearer ${$token}` },
                },
            );
            if (!res.ok) throw new Error("Failed to load messages");
            messages = await res.json();
            scrollToBottom();
        } catch (e) {
            error = e.message;
        }
    }

    function connectWebSocket() {
        if (ws) ws.close();

        ws = new WebSocket(
            `ws://localhost:8000/ws/${selectedRoom.id}?token=${$token}`,
        );

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (!selectedRoom) return;
            if (
                msg.type === "message" &&
                msg.data.room_id === selectedRoom.id
            ) {
                // Check for duplicates if we sent via REST and it already returned
                if (!messages.find((m) => m.id === msg.data.id)) {
                    messages = [...messages, msg.data];
                    scrollToBottom();
                }
            }
        };

        ws.onopen = () => {
            console.log("WebSocket connected");
            error = "";
        };

        ws.onerror = (e) => {
            console.error("WebSocket error:", e);
        };

        ws.onclose = () => {
            console.log("WebSocket closed");
        };
    }

    async function sendMessage() {
        if (!newMessage.trim()) return;
        const content = newMessage;
        newMessage = "";

        try {
            // Priority 1: WebSocket
            if (ws && ws.readyState === WebSocket.OPEN) {
                try {
                    ws.send(
                        JSON.stringify({
                            room_id: selectedRoom.id,
                            content: content,
                        }),
                    );
                    return; // Success
                } catch (e) {
                    console.warn("WS send failed, falling back to REST", e);
                }
            }

            // Priority 2: REST Fallback
            const res = await fetch("http://localhost:8000/messages/create", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${$token}`,
                },
                body: JSON.stringify({
                    room_id: selectedRoom.id,
                    content: content,
                }),
            });

            if (!res.ok)
                throw new Error("Failed to send message via REST fallback");

            const created = await res.json();
            if (!messages.find((m) => m.id === created.id)) {
                messages = [...messages, created];
                scrollToBottom();
            }
        } catch (e) {
            error = `Send failed: ${e.message}`;
            newMessage = content; // restore draft
        }
    }

    async function createRoom() {
        if (!newRoomName.trim()) return;
        try {
            const res = await fetch("http://localhost:8000/rooms/create", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${$token}`,
                },
                body: JSON.stringify({ name: newRoomName }),
            });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to create room");
            }
            newRoomName = "";
            await loadRooms();
        } catch (e) {
            error = e.message;
        }
    }

    async function deleteRoom(roomId, event) {
        if (event) event.stopPropagation();
        if (!confirm("Are you sure you want to delete this room?")) return;
        try {
            const res = await fetch(`http://localhost:8000/rooms/${roomId}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${$token}` },
            });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to delete room");
            }
            if (selectedRoom && selectedRoom.id === roomId) {
                leaveRoom();
            }
            await loadRooms();
        } catch (e) {
            error = e.message;
        }
    }

    async function addUserToRoom() {
        if (!addUserUsername) return;
        try {
            const res = await fetch(
                `http://localhost:8000/rooms/${selectedRoom.id}/add-user`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${$token}`,
                    },
                    body: JSON.stringify({ username: addUserUsername }),
                },
            );
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to add user");
            }
            await loadRoomUsers(selectedRoom.id);
            addUserUsername = "";
        } catch (e) {
            error = e.message;
        }
    }

    async function removeUserFromRoom(username) {
        if (!confirm(`Are you sure you want to remove ${username}?`)) return;
        try {
            const res = await fetch(
                `http://localhost:8000/rooms/${selectedRoom.id}/remove-user`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${$token}`,
                    },
                    body: JSON.stringify({ username }),
                },
            );
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to remove user");
            }
            await loadRoomUsers(selectedRoom.id);
        } catch (e) {
            error = e.message;
        }
    }

    function scrollToBottom() {
        setTimeout(() => {
            const el = document.querySelector(".messages");
            if (el) el.scrollTop = el.scrollHeight;
        }, 50);
    }

    function leaveRoom() {
        selectedRoom = null;
        messages = [];
        if (ws) {
            ws.close();
            ws = null;
        }
    }

    function logout() {
        token.set(null);
        user.set(null);
        if (ws) {
            ws.close();
            ws = null;
        }
    }

    onDestroy(() => {
        if (ws) ws.close();
    });
</script>

<div class="chat-container">
    {#if !selectedRoom}
        <div class="room-page">
            <header>
                <h1>Rooms</h1>
                <button class="logout-btn" on:click={logout}>Logout</button>
            </header>

            {#if error}
                <p class="error">{error}</p>
            {/if}

            <div class="create-room">
                <input
                    type="text"
                    bind:value={newRoomName}
                    placeholder="New room name..."
                />
                <button on:click={createRoom}>Create</button>
            </div>

            <div class="room-list">
                {#each rooms as room}
                    <div class="room-card-wrapper">
                        <button
                            class="room-card"
                            on:click={() => selectRoom(room)}
                        >
                            <div class="room-info">
                                <h3># {room.name}</h3>
                                <p>Click to join</p>
                            </div>
                            <div class="arrow">→</div>
                        </button>
                        {#if room.owner_id === $user?.id}
                            <button
                                class="delete-room-btn"
                                on:click={(e) => deleteRoom(room.id, e)}
                                title="Delete Room"
                            >
                                ✕
                            </button>
                        {/if}
                    </div>
                {/each}
                {#if rooms.length === 0}
                    <p class="empty">No rooms available. Create one above!</p>
                {/if}
            </div>
        </div>
    {:else}
        <div class="message-page">
            <header>
                <button class="back-btn" on:click={leaveRoom}>←</button>
                <div class="title-section">
                    <h2># {selectedRoom.name}</h2>
                    <p class="member-count">{roomUsers.length} members</p>
                </div>
                <div class="header-actions">
                    <div class="add-user-form">
                        <select bind:value={addUserUsername}>
                            <option value="">Add Member...</option>
                            {#each allUsers.filter((u) => !roomUsers.find((ru) => ru.id === u.id)) as u}
                                <option value={u.username}>{u.username}</option>
                            {/each}
                        </select>
                        <button
                            on:click={addUserToRoom}
                            disabled={!addUserUsername}>Add</button
                        >
                    </div>
                    <div class="user-chip">{$user?.username || "User"}</div>
                </div>
            </header>

            <div class="chat-layout">
                <div class="messages">
                    {#each messages as msg}
                        <div
                            class="message {msg.sender.id === $user?.id
                                ? 'own'
                                : ''}"
                        >
                            <div class="msg-header">
                                <span class="sender">{msg.sender.username}</span
                                >
                                <span class="time"
                                    >{new Date(
                                        msg.timestamp,
                                    ).toLocaleTimeString([], {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    })}</span
                                >
                            </div>
                            <div class="msg-content">{msg.content}</div>
                        </div>
                    {/each}
                </div>

                <div class="sidebar">
                    <h3>Members</h3>
                    <div class="member-list">
                        {#each roomUsers as member}
                            <div class="member-item">
                                <span
                                    class={member.id === selectedRoom.owner_id
                                        ? "owner"
                                        : ""}
                                >
                                    {member.username}
                                    {#if member.id === selectedRoom.owner_id}
                                        <small>(owner)</small>
                                    {/if}
                                </span>
                                {#if selectedRoom.owner_id === $user?.id && member.id !== $user?.id}
                                    <button
                                        class="remove-btn"
                                        on:click={() =>
                                            removeUserFromRoom(member.username)}
                                        title="Remove Member">✕</button
                                    >
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            </div>

            <form class="input-area" on:submit|preventDefault={sendMessage}>
                <input
                    type="text"
                    bind:value={newMessage}
                    placeholder="Type a message..."
                />
                <button type="submit" disabled={!newMessage.trim()}>Send</button
                >
            </form>
        </div>
    {/if}
</div>

<style>
    .chat-container {
        height: 90vh;
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        background: rgba(17, 17, 26, 0.9);
        border-radius: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        overflow: hidden;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
    }

    header {
        padding: 1.5rem;
        background: rgba(26, 26, 40, 0.8);
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    h1,
    h2 {
        margin: 0;
        font-size: 1.5rem;
    }

    .logout-btn,
    .back-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #e8e8f0;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
    }

    .logout-btn:hover,
    .back-btn:hover {
        background: rgba(255, 101, 132, 0.1);
        color: #ff6584;
    }

    .room-list {
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        overflow-y: auto;
    }

    .room-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 1rem;
        padding: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: white;
        cursor: pointer;
        transition: all 0.2s;
        text-align: left;
    }

    .room-card:hover {
        background: rgba(108, 99, 255, 0.1);
        border-color: rgba(108, 99, 255, 0.3);
        transform: translateY(-2px);
    }

    .room-info h3 {
        margin: 0 0 0.25rem;
        font-size: 1.1rem;
    }

    .room-info p {
        margin: 0;
        font-size: 0.8rem;
        color: #6b6b8a;
    }

    .arrow {
        font-size: 1.2rem;
        color: #6c63ff;
    }

    .message-page {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .messages {
        flex: 1;
        overflow-y: auto;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .message {
        max-width: 80%;
        background: rgba(255, 255, 255, 0.05);
        padding: 0.8rem 1rem;
        border-radius: 1rem;
        border-bottom-left-radius: 0;
        align-self: flex-start;
    }

    .message.own {
        align-self: flex-end;
        background: linear-gradient(
            135deg,
            rgba(108, 99, 255, 0.2),
            rgba(108, 99, 255, 0.1)
        );
        border: 1px solid rgba(108, 99, 255, 0.2);
        border-bottom-left-radius: 1rem;
        border-bottom-right-radius: 0;
    }

    .msg-header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.25rem;
        font-size: 0.75rem;
    }

    .sender {
        font-weight: 700;
        color: #6c63ff;
    }

    .time {
        color: #6b6b8a;
    }

    .msg-content {
        word-break: break-word;
        line-height: 1.4;
    }

    .input-area {
        padding: 1.25rem;
        background: rgba(26, 26, 40, 0.8);
        display: flex;
        gap: 0.75rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    input {
        flex: 1;
        background: rgba(13, 13, 24, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 0.8rem 1rem;
        border-radius: 0.75rem;
        color: white;
    }

    button[type="submit"] {
        background: #6c63ff;
        color: white;
        border: none;
        padding: 0 1.5rem;
        border-radius: 0.75rem;
        font-weight: 700;
        cursor: pointer;
    }

    button[type="submit"]:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .user-chip {
        background: rgba(67, 232, 176, 0.1);
        color: #43e8b0;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(67, 232, 176, 0.2);
    }

    .create-room {
        padding: 0 1.5rem 1rem;
        display: flex;
        gap: 0.5rem;
    }

    .create-room input {
        flex: 1;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        color: white;
    }

    .create-room button {
        background: #6c63ff;
        color: white;
        border: none;
        padding: 0 1rem;
        border-radius: 0.5rem;
        font-weight: 600;
        cursor: pointer;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .add-user-form {
        display: flex;
        gap: 0.25rem;
    }

    .add-user-form button {
        background: rgba(108, 99, 255, 0.2);
        color: #6c63ff;
        border: 1px solid rgba(108, 99, 255, 0.3);
        padding: 0.25rem 0.5rem;
        border-radius: 0.4rem;
        font-size: 0.8rem;
        cursor: pointer;
    }

    .room-card-wrapper {
        position: relative;
        display: flex;
        align-items: center;
    }

    .room-card {
        flex: 1;
    }

    .delete-room-btn {
        position: absolute;
        right: 1.5rem;
        background: rgba(255, 101, 132, 0.1);
        color: #ff6584;
        border: 1px solid rgba(255, 101, 132, 0.2);
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
        opacity: 0;
    }

    .room-card-wrapper:hover .delete-room-btn {
        opacity: 1;
    }

    .delete-room-btn:hover {
        background: #ff6584;
        color: white;
        transform: scale(1.1);
    }

    .title-section {
        flex: 1;
        margin-left: 1rem;
    }

    .member-count {
        margin: 0;
        font-size: 0.8rem;
        color: #6b6b8a;
    }

    .add-user-form select {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 0.25rem 0.5rem;
        border-radius: 0.4rem;
        color: white;
        font-size: 0.8rem;
        outline: none;
    }

    .add-user-form select option {
        background: #1a1a28;
    }

    .chat-layout {
        display: flex;
        flex: 1;
        overflow: hidden;
    }

    .sidebar {
        width: 200px;
        background: rgba(0, 0, 0, 0.1);
        border-left: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .sidebar h3 {
        margin: 0;
        font-size: 0.9rem;
        color: #6b6b8a;
        text-transform: uppercase;
        letter-spacing: 0.05rem;
    }

    .member-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .member-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
        color: #e8e8f0;
    }

    .owner {
        color: #ffb86c;
    }

    .remove-btn {
        background: none;
        border: none;
        color: #6b6b8a;
        cursor: pointer;
        font-size: 0.75rem;
        opacity: 0;
        transition: opacity 0.2s;
    }

    .member-item:hover .remove-btn {
        opacity: 1;
    }

    .remove-btn:hover {
        color: #ff6584;
    }
</style>
