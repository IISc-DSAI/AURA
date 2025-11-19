import streamlit as st
import requests
import base64
import json
import time

API = "http://3.108.237.37:8300" # your Django API root

# ------------------------------------------
# Helpers
# ------------------------------------------

def to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

def typing_animation(text):
    """Simulate streaming typing."""
    container = st.empty()
    out = ""
    for ch in text:
        out += ch
        container.markdown(out)
        time.sleep(0.002)

def fetch_user():
    """Check login state via Django session."""
    try:
        r = requests.get(f"{API}/auth/me", cookies=st.session_state.get("cookies"))
        return r.json()
    except:
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
    r = requests.get(f"{API}/chats", cookies=st.session_state["cookies"])
    return r.json()

def get_messages(chat_id):
    r = requests.get(f"{API}/chats/{chat_id}/messages",
                     cookies=st.session_state["cookies"])
    return r.json()

# ------------------------------------------
# Login / Signup Gate
# ------------------------------------------

user = fetch_user()

if not user.get("authenticated"):
    st.title("🔐 Login / Signup")

    tabs = st.tabs(["Login", "Signup"])

    # ---- Login ----
    with tabs[0]:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(email, password):
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    # ---- Signup ----
    with tabs[1]:
        name = st.text_input("Name")
        email2 = st.text_input("Email (Signup)")
        password2 = st.text_input("Password (Signup)", type="password")

        if st.button("Create Account"):
            if signup_user(name, email2, password2):
                st.success("Account created!")
                st.rerun()
            else:
                st.error("Signup failed")

    st.stop()

# ------------------------------------------
# Main UI Layout
# ------------------------------------------

st.set_page_config(page_title="AURA Chat", layout="wide")

st.sidebar.title("💬 Chats")

# Load chat list
if "chats" not in st.session_state:
    st.session_state["chats"] = list_chats()

# Chat Operations
if st.sidebar.button("➕ New Chat"):
    r = requests.post(f"{API}/chats", json={"title": "New Chat"},
                      cookies=st.session_state["cookies"])
    st.session_state["selected_chat"] = r.json()["id"]
    st.session_state["chats"] = list_chats()

# Sidebar Chat List
for c in st.session_state["chats"]:
    if st.sidebar.button(c["title"] or "Untitled", key=f"chat_{c['id']}"):
        st.session_state["selected_chat"] = c["id"]

# Rename / Delete chat
if "selected_chat" in st.session_state:
    with st.sidebar.expander("Chat Options"):
        new_name = st.text_input("Rename Chat")
        if st.button("Rename"):
            requests.patch(
                f"{API}/chats/{st.session_state['selected_chat']}",
                json={"title": new_name},
                cookies=st.session_state["cookies"]
            )
            st.session_state["chats"] = list_chats()
            st.rerun()

        if st.button("Delete Chat"):
            requests.delete(
                f"{API}/chats/{st.session_state['selected_chat']}",
                cookies=st.session_state["cookies"]
            )
            st.session_state["chats"] = list_chats()
            st.session_state.pop("selected_chat", None)
            st.rerun()

# ------------------------------------------------
# Chat Area
# ------------------------------------------------

if "selected_chat" not in st.session_state:
    st.info("Create or select a chat.")
    st.stop()

chat_id = st.session_state["selected_chat"]

# Load messages
msgs = get_messages(chat_id)

# Display messages
for m in msgs:
    if m["role"] == "user":
        st.markdown(
            f"""
            <div style='background:#DCF8C6;padding:10px;border-radius:10px;margin:5px;'>
            <b>You:</b><br>{m["content"]}
            </div>""",
            unsafe_allow_html=True
        )
    else:
        # AI message + links/citations/buttons
        with st.expander("AI Response", expanded=True):
            st.markdown(m["content"], unsafe_allow_html=True)

            google_links = m.get("google_links") or []
            if google_links:
                st.markdown("**🔍 Google Links**")
                for url in google_links:
                    st.markdown(f"- [{url}]({url})")

            youtube_links = m.get("youtube_links") or []
            if youtube_links:
                st.markdown("**📺 YouTube Links**")
                for url in youtube_links:
                    st.markdown(f"- [{url}]({url})")

            citations = m.get("citations") or []
            if citations:
                st.markdown("**📚 Citations**")
                for c in citations:
                    label = c.get("source") or str(c)
                    st.markdown(f"- {label} &mdash; `{c}`")

            if m.get("youtube_summary"):
                st.markdown("**📝 YouTube Summary**")
                st.markdown(m["youtube_summary"])

            st.button("Copy", key=f"copy_{m['id']}")
            st.button("Retry", key=f"retry_{m['id']}")

# ------------------------------------------------
# Input Area
# ------------------------------------------------

st.subheader("Your message")

message = st.text_area("")

uploaded_images = st.file_uploader(
    "Upload images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# Convert images → base64
images_b64 = []
for f in uploaded_images:
    images_b64.append(to_base64(f))

# Toggles
colA, colB, colC = st.columns(3)
rag_on = colA.toggle("Use RAG")
mcp_on = colB.toggle("Use MCP")
yt_on = colC.toggle("YouTube Summary")

# Voice Input
if st.button("🎤 Record Voice"):
    st.info("Voice input placeholder — depends on browser plugin.")

# Send message
if st.button("Send"):
    payload = {
        "chat_id": chat_id,
        "message": message,
        "images": images_b64,
        "settings": {
            "rag": int(rag_on),
            "mcp": int(mcp_on),
            "yt_summary": int(yt_on)
        }
    }

    r = requests.post(f"{API}/chat", json=payload,
                      cookies=st.session_state["cookies"])

    if r.status_code == 200:
        data = r.json()
        final_ans = data["final_response"]

        typing_animation(final_ans)     # fake streaming

        st.session_state["chats"] = list_chats()
        st.rerun()
    else:
        st.error("Error in backend")