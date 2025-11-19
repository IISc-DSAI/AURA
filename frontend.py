import streamlit as st
import requests
import base64
import json
import time
from ai_preprocessing import *

# ------------------------------------------
# Page Config (MUST be the first st command)
# ------------------------------------------
st.set_page_config(
    page_title="AURA Chat", 
    layout="wide", 
    page_icon="", 
    initial_sidebar_state="auto"
)

API = "http://13.201.4.144:8000"     # Your Django API root

# ------------------------------------------
# Helper Functions
# ------------------------------------------

def to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

def typing_animation(text):
    text = str(text) if text is not None else ""
    container = st.empty()
    out = ""
    for ch in text:
        out += ch
        container.markdown(out)
        time.sleep(0.002)

def fetch_user():
    try:
        r = requests.get(f"{API}/auth/me", cookies=st.session_state.get("cookies"))
        if r.status_code == 200:
            return r.json()
    except requests.ConnectionError:
        st.error("Could not connect to backend API. Please check the connection.")
        return {"authenticated": False}
    except Exception as e:
        return {"authenticated": False}
    return {"authenticated": False}

def login_user(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        st.session_state["cookies"] = r.cookies.get_dict()
        return True
    return False

def signup_user(name, email, password):
    r = requests.post(f"{API}/auth/signup", json={
        "name": name, "email": email, "password": password
    })
    if r.status_code == 200:
        st.session_state["cookies"] = r.cookies.get_dict()
        return True
    return False

def list_chats():
    cookies = st.session_state.get("cookies")
    if not cookies:
        return []
    r = requests.get(f"{API}/chats", cookies=cookies)
    return r.json()

def get_messages(chat_id):
    cookies = st.session_state.get("cookies")
    if not cookies or not chat_id:
        return []
    r = requests.get(f"{API}/chats/{chat_id}/messages", cookies=cookies)
    return r.json()

# ------------------------------------------
# Central Message Sending Logic
# ------------------------------------------
def handle_send_message(message, images_b64):
    if "selected_chat" not in st.session_state:
        st.error("No chat selected. Please start a new chat first.")
        return

    chat_id = st.session_state["selected_chat"]

    # Detect if this is the first message
    existing_msgs = get_messages(chat_id)
    is_first_message = len(existing_msgs) == 0

    # Show user's message in UI
    with st.chat_message("user"):
        st.markdown(message)
        if images_b64:
            st.image([base64.b64decode(img) for img in images_b64], width=100)

    with st.spinner("AURA is thinking..."):
        payload = {
            "chat_id": chat_id,
            "message": message,
            "images": images_b64,
            "settings": {
                "rag": int(st.session_state.get("rag_on", True)),
                "mcp": int(st.session_state.get("mcp_on", False)),
                "yt_summary": int(st.session_state.get("yt_on", False)),
            }
        }

        try:
            r = requests.post(f"{API}/chat", json=payload, cookies=st.session_state["cookies"])

            if r.status_code == 200:
                data = r.json()
                final_ans = data.get("final_response", "No response from AI.")

                # ---------- AUTO TITLE GENERATION ----------
                if is_first_message:
                    try:
                        generated_title = generate_title(message)
                        requests.patch(
                            f"{API}/chats/{chat_id}",
                            json={"title": generated_title},
                            cookies=st.session_state["cookies"]
                        )
                    except Exception as e:
                        st.warning(f"Title generation failed: {e}")

                # Show AI answer
                with st.chat_message("assistant"):
                    typing_animation(final_ans)

                time.sleep(0.4)
                st.session_state["chats"] = list_chats()
                st.rerun()

            else:
                st.error(f"Error in backend: {r.status_code} - {r.text}")

        except requests.ConnectionError as e:
            st.error(f"Failed to connect to backend: {e}")
        except Exception as e:
            st.error(f"An unknown error occurred: {e}")

def send_suggestion(text):
    """
    Handles when a user clicks a suggestion button on the welcome screen.
    """
    # 1. Ensure a chat is active. If not, create one.
    if "selected_chat" not in st.session_state:
        try:
            r = requests.post(f"{API}/chats", json={"title": generate_title(text)},
                              cookies=st.session_state["cookies"])
            if r.status_code == 200:
                st.session_state["selected_chat"] = r.json()["id"]
                st.session_state["chats"] = list_chats() # Refresh list
            else:
                st.error("Failed to create a new chat.")
                return
        except Exception as e:
            st.error(f"Connection error: {e}")
            return
    
    # 2. Send the message
    handle_send_message(text, []) # Send suggestion with no images
    st.rerun()

# ------------------------------------------
# Login / Signup Gate
# ------------------------------------------
user = fetch_user()

if not user.get("authenticated"):
    st.set_page_config(page_title="Login - AURA Chat", layout="centered")
    _ , col2, _ = st.columns([0.5, 2, 0.5])
    with col2:
        st.title("Welcome to AURA Chat")
        tabs = st.tabs(["Login", "Signup"])
        
        with tabs[0]:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True):
                    if login_user(email, password):
                        st.success("Logged in!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

        with tabs[1]:
            with st.form("signup_form"):
                name = st.text_input("Name")
                email2 = st.text_input("Email")
                password2 = st.text_input("Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if signup_user(name, email2, password2):
                        st.success("Account created!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Signup failed. Email may already be in use.")
    st.stop()

# ------------------------------------------
# Main UI Sidebar
# ------------------------------------------
# Custom styled AURA title with fancy font
st.sidebar.markdown("""
<link href='https://fonts.googleapis.com/css2?family=Pacifico&family=Dancing+Script:wght@700&family=Lobster&display=swap' rel='stylesheet'>
<style>
    .aura-title {
        font-family: 'Bebas Neue', cursive;
        font-size: 6rem;
        font-weight: normal;
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
</style>
<h1 class="aura-title">AURA</h1>
""", unsafe_allow_html=True)
st.sidebar.caption(f"Welcome, {user.get('name', 'User')}!")

# Custom CSS for button styling (optional - uncomment to use)
# st.markdown("""
# <style>
#     div[data-testid="stButton"] > button[kind="primary"] {
#         background-color: #FF6B6B;
#         color: white;
#         border: none;
#     }
#     div[data-testid="stButton"] > button[kind="primary"]:hover {
#         background-color: #FF5252;
#     }
# </style>
# """, unsafe_allow_html=True)

if st.sidebar.button("New Chat", use_container_width=True, type="primary"):
    try:
        r = requests.post(f"{API}/chats", json={"title": "NEW CHAT"},
                          cookies=st.session_state["cookies"])
        if r.status_code == 200:
            st.session_state["selected_chat"] = r.json()["id"]
            st.session_state["chats"] = list_chats() # Refresh list
            st.rerun()
        else:
            st.sidebar.error("Failed to create chat.")
    except Exception as e:
        st.sidebar.error(f"Connection error: {e}")

st.sidebar.divider()

# File uploader moved to sidebar
uploaded_images = st.sidebar.file_uploader(
    "📎 Attachments",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

st.sidebar.divider()

# --- Chat History ---
st.sidebar.header("History")

if "chats" not in st.session_state:
    st.session_state["chats"] = list_chats()

for c in st.session_state["chats"]:
    is_selected = (c['id'] == st.session_state.get("selected_chat"))
    title = c["title"] or "Untitled Chat"

    row = st.sidebar.container()
    col1, col2 = row.columns([8, 1])

    # Chat Title Button
    if col1.button(title, key=f"title_{c['id']}", use_container_width=True):
        st.session_state["selected_chat"] = c["id"]
        st.rerun()

    # 3-Dots Menu
    with col2.popover("⋯"):
        new_name = st.text_input("Rename Chat", value=title, key=f"rename_{c['id']}")
        if st.button("Save", key=f"save_{c['id']}"):
            requests.patch(
                f"{API}/chats/{c['id']}",
                json={"title": new_name},
                cookies=st.session_state["cookies"]
            )
            st.session_state["chats"] = list_chats()
            st.rerun()

        st.write("---")
        if st.button("Delete Chat", key=f"delete_{c['id']}", type="secondary"):
            requests.delete(
                f"{API}/chats/{c['id']}",
                cookies=st.session_state["cookies"]
            )
            st.session_state["chats"] = list_chats()
            if st.session_state.get("selected_chat") == c['id']:
                st.session_state.pop("selected_chat", None)
            st.rerun()


# ------------------------------------------------
# Main Chat Area
# ------------------------------------------------

# --- Welcome Screen (if no chat is selected) ---
if "selected_chat" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'></h1>", unsafe_allow_html=True)
    st.title("Welcome to AURA")
    st.markdown(
        "<h4 style='text-align: center; color: #888;'>Your intelligent assistant for technical manuals and documentation</h4>", 
        unsafe_allow_html=True
    )
    
    st.divider()
    
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("How do I replace brake pads on BMW X5?", use_container_width=True):
                send_suggestion("How do I replace brake pads on BMW X5?")
            if st.button("Show me the engine specifications", use_container_width=True):
                send_suggestion("Show me the engine specifications")
        with col2:
            if st.button("What are the oil change intervals?", use_container_width=True):
                send_suggestion("What are the oil change intervals?")
            if st.button("How to reset the service indicator?", use_container_width=True):
                send_suggestion("How to reset the service indicator?")
    st.stop()


# --- Main Chat Interface (if a chat is selected) ---
chat_id = st.session_state["selected_chat"]

# Display messages
msgs = get_messages(chat_id)
for m in msgs:
    role = m["role"] if m["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(m.get("content", ""))
        
        # Display links/citations from your logic
        if role == "assistant":
            google_links = m.get("google_links")
            if google_links and isinstance(google_links, list) and len(google_links) > 0:
                st.markdown("**🔍 Google Links**")
                for url in google_links:
                    if url:  # Check if url is not empty/None
                        st.markdown(f"- [{url}]({url})")
            
            youtube_links = m.get("youtube_links")
            if youtube_links and isinstance(youtube_links, list) and len(youtube_links) > 0:
                st.markdown("**📺 YouTube Links**")
                for url in youtube_links:
                    if url:  # Check if url is not empty/None
                        st.markdown(f"- [{url}]({url})")
            
            citations = m.get("citations")
            if citations and isinstance(citations, list) and len(citations) > 0:
                st.markdown("**📚 Citations**")
                for c in citations:
                    if c:  # Check if citation is not empty/None
                        source = c.get('source') if isinstance(c, dict) else c
                        st.markdown(f"- {source or str(c)}")
            
            youtube_summary = m.get("youtube_summary")
            if youtube_summary and youtube_summary.strip():
                st.markdown("**📝 YouTube Summary**")
                st.markdown(youtube_summary)

# Disclaimer below chat, above input
st.caption("AURA can make mistakes. Verify important information from source manuals.")


# --- Custom (Non-Pinned) Chat Input Bar ---
# NOTE: This bar is NOT pinned to the bottom of the screen.
# This is a tradeoff to get the 'Tools' button on the same line.
# We use a form to make the 'Enter' key submit thx`e text.

# with st.form(key="chat_input_form", clear_on_submit=True):
#     cols = st.columns([1, 10, 1]) # [Popover, Text Input, Send Button]
    
#     with cols[0]:
#         with st.popover("⚙️"):
#             st.toggle("RAG", value=True, key="rag_on", help="Enable Retrieval-Augmented Generation")
#             st.toggle("MCP", key="mcp_on", help="Enable MCP")

#             if st.session_state.get("mcp_on"):
#                 st.toggle("YouTube", key="yt_on", help="Enable YouTube Summary")


#     with cols[1]:
#         prompt = st.text_input(
#             "Ask about vehicle maintenance...", 
#             label_visibility="collapsed",
#             placeholder="Ask about vehicle maintenance, repairs, or specifications...",
#             key="chat_text_input"
#         )

#     with cols[2]:
#         submit_button = st.form_submit_button(label="➤")

# Popover must be OUTSIDE the form
cols = st.columns([1, 10, 1])

# Now the form
with st.form(key="chat_input_form", clear_on_submit=True):
    form_cols = st.columns([1, 10, 1])

    with form_cols[0]: 
        with st.popover("⚙️"): 
            st.toggle("RAG", value=True, key="rag_on", help="Enable Retrieval-Augmented Generation") 
            st.toggle("MCP", key="mcp_on", help="Enable MCP") 
            st.toggle("YouTube", key="yt_on", help="Enable YouTube Summary")

    with form_cols[1]:
        prompt = st.text_input(
            "Ask about vehicle maintenance...",
            label_visibility="collapsed",
            placeholder="Ask about vehicle maintenance, repairs, or specifications...",
            key="chat_text_input"
        )

    with form_cols[2]:
        submit_button = st.form_submit_button(label="➤")





# --- Handle Sending Logic (now outside the input) ---
if submit_button and prompt: # 'prompt' is from the st.text_input
    # 1. Process sidebar file uploads
    images_b64 = []
    if uploaded_images:
        for f in uploaded_images:
            images_b64.append(to_base64(f))
        # Clear the uploader after processing
        # This is a bit of a hack, but necessary
        st.session_state["file_uploader_key"] = str(time.time()) 
    
    # 2. Send the message
    handle_send_message(prompt, images_b64)
    # The form's 'clear_on_submit=True' handles clearing the text on rerun.