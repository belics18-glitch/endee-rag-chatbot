// Gets the input box from HTML
const input = document.getElementById("input");

// Gets the message area from HTML
const messagesDiv = document.getElementById("messages");

// Gets the status badge from HTML
const statusBadge = document.getElementById("statusBadge");

// Gets the send button from HTML
const sendBtn = document.getElementById("sendBtn");

// Backend URL for deployed Render backend
const BACKEND_URL = "https://YOUR_RENDER_BACKEND_URL.onrender.com";

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
        if (statusBadge) statusBadge.textContent = "Connecting...";

        addSystemMessage("Connecting to server...");

        const res = await fetch(`${BACKEND_URL}/health`, {
            method: "GET"
        });

        if (!res.ok) {
            throw new Error("Health check failed");
        }

        removeSystemMessage();

        if (statusBadge) statusBadge.textContent = "Online";

        addSystemMessage("Server connected successfully");

        setTimeout(removeSystemMessage, 1500);
    } catch (error) {
        removeSystemMessage();

        if (statusBadge) statusBadge.textContent = "Waking up...";
        addSystemMessage("Server is waking up. First reply may take a few seconds.");

        console.error("Wake-up error:", error);
    }
}

// Sends a user message to backend
async function send() {
    const msg = input.value.trim();

    if (!msg || isSending) return;

    isSending = true;
    sendBtn.disabled = true;

    addMessage("🧑 " + msg, "user");

    input.value = "";
    input.focus();

    addLoadingMessage("🤖 Thinking...");

    try {
        const res = await fetch(`${BACKEND_URL}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: msg })
        });

        const data = await res.json();

        removeLoadingMessage();

        if (!res.ok) {
            throw new Error(data.detail || "Something went wrong");
        }

        if (statusBadge) statusBadge.textContent = "Online";

        addMessage("🤖 " + (data.reply || "No reply received from server."), "bot");

        if (showContext && data.matched_chunks && data.matched_chunks.length > 0) {
            addContextBox(data.matched_chunks);
        }
    } catch (error) {
        removeLoadingMessage();

        if (statusBadge) statusBadge.textContent = "Error";

        addMessage("🤖 Sorry, I couldn't get a response from the server.", "bot");

        console.error("Chat error:", error);
    } finally {
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
    msgDiv.className = `message ${sender}`;
    msgDiv.textContent = text;

    if (id) {
        msgDiv.id = id;
    }

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

    chunks.forEach((chunk) => {
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