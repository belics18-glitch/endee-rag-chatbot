// Gets the input box from HTML
const input = document.getElementById("input");

// Gets the message area from HTML
const messagesDiv = document.getElementById("messages");

// Gets the status badge from HTML
const statusBadge = document.getElementById("statusBadge");

// Gets the send button from HTML
const sendBtn = document.getElementById("sendBtn");

// Backend URL for local development
const BACKEND_URL = "http://127.0.0.1:8000";

const toggleContextBtn = document.getElementById("toggleContextBtn");
let showContext = true;

// Prevents multiple requests while one message is being sent
let isSending = false;

// Runs when the page fully loads
window.addEventListener("load", async() => {
    addWelcomeMessage();
    await wakeUpBackend();
});

// Function to ping the backend when page opens
async function wakeUpBackend() {
    try {
        // Update status badge
        if (statusBadge) statusBadge.textContent = "Connecting...";

        // Show system message to user
        addSystemMessage("Connecting to server...");

        // Call backend health endpoint
        const res = await fetch(`${BACKEND_URL}/health`, {
            method: "GET"
        });

        // If response is not successful, throw error
        if (!res.ok) {
            throw new Error("Health check failed");
        }

        // Remove temporary system message
        removeSystemMessage();

        // Update badge to online
        if (statusBadge) statusBadge.textContent = "Online";

        addSystemMessage("Server connected successfully");

        // Remove system message after 1.5 seconds
        setTimeout(removeSystemMessage, 1500);

    } catch (error) {
        removeSystemMessage();

        // If backend is sleeping, show waking-up message
        if (statusBadge) statusBadge.textContent = "Waking up...";
        addSystemMessage("Server is waking up. First reply may take a few seconds.");

        console.error("Wake-up error:", error);
    }
}

// Sends a user message to backend
async function send() {
    // Removes extra spaces from input
    const msg = input.value.trim();

    // Prevents empty message or double sending
    if (!msg || isSending) return;

    isSending = true;
    sendBtn.disabled = true;

    // Adds user message to chat UI
    addMessage("🧑 " + msg, "user");

    // Clears input box
    input.value = "";
    input.focus();

    // Shows temporary loading message
    addLoadingMessage("🤖 Thinking...");

    try {
        // Sends POST request to backend /chat endpoint
        const res = await fetch(`${BACKEND_URL}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            // Converts JavaScript object into JSON string
            body: JSON.stringify({ message: msg })
        });

        // Converts backend response into JavaScript object
        const data = await res.json();

        // Removes loading message
        removeLoadingMessage();

        // If backend returns error
        if (!res.ok) {
            throw new Error(data.detail || "Something went wrong");
        }

        // Update status
        if (statusBadge) statusBadge.textContent = "Online";

        // Show bot reply
        addMessage("🤖 " + data.reply, "bot");

        if (showContext && data.matched_chunks && data.matched_chunks.length > 0) {
            addContextBox(data.matched_chunks);
        }

    } catch (error) {
        removeLoadingMessage();

        if (statusBadge) statusBadge.textContent = "Error";

        // Show user-friendly fallback message
        addMessage("🤖 Sorry, I couldn't get a response from the server.", "bot");

        console.error("Chat error:", error);
    } finally {
        // Re-enable sending after response
        isSending = false;
        sendBtn.disabled = false;
    }
}

// Adds a starting bot message when page loads
function addWelcomeMessage() {
    addMessage(
        "🤖 Hello 👋\nI am an Endee-powered RAG assistant.\nI retrieve relevant knowledge and generate accurate answers.\nAsk me anything about RAG, vector databases, or this project.",
        "bot"
    );
}

// Fills input box when suggestion chip is clicked
function fillPrompt(text) {
    input.value = text;
    input.focus();
}

// Clears the entire chat window
function clearChat() {
    messagesDiv.innerHTML = "";
    addWelcomeMessage();
}

function toggleContextVisibility() {
    showContext = !showContext;

    if (toggleContextBtn) {
        toggleContextBtn.textContent = showContext ? "Hide Context" : "Show Context";
    }
}

// General function to add any message to the chat area
function addMessage(text, sender, id = null) {
    const msgDiv = document.createElement("div");

    // Adds CSS classes like "message user" or "message bot"
    msgDiv.className = `message ${sender}`;

    // Inserts text inside the div
    msgDiv.textContent = text;

    // Optionally assigns an ID
    if (id) {
        msgDiv.id = id;
    }

    // Appends the new message into chat box
    messagesDiv.appendChild(msgDiv);

    scrollToBottom();
}

// Adds a loading message
function addLoadingMessage(text) {
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message bot loading";
    loadingDiv.id = "loading";
    loadingDiv.textContent = text;

    messagesDiv.appendChild(loadingDiv);
    scrollToBottom();
}

// Removes the loading message
function removeLoadingMessage() {
    const loading = document.getElementById("loading");
    if (loading) {
        loading.remove();
    }
}

// Adds a system info message
function addSystemMessage(text) {
    removeSystemMessage();

    const systemDiv = document.createElement("div");
    systemDiv.className = "message system";
    systemDiv.id = "system-message";
    systemDiv.textContent = text;

    messagesDiv.appendChild(systemDiv);
    scrollToBottom();
}

// Removes system message if it exists
function removeSystemMessage() {
    const systemMsg = document.getElementById("system-message");
    if (systemMsg) {
        systemMsg.remove();
    }
}

function addContextBox(chunks) {
    const contextDiv = document.createElement("div");
    contextDiv.className = "context-box";

    const title = document.createElement("div");
    title.className = "context-title";
    title.textContent = "📌 Retrieved from Knowledge Base";

    contextDiv.appendChild(title);

    chunks.forEach((chunk, index) => {
        const item = document.createElement("div");
        item.className = "context-item";
        item.textContent = `• ${chunk}`;
        contextDiv.appendChild(item);
    });

    messagesDiv.appendChild(contextDiv);
    scrollToBottom();
}

// Automatically scrolls chat to bottom
function scrollToBottom() {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Sends message when Enter key is pressed
input.addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        e.preventDefault();
        send();
    }
});