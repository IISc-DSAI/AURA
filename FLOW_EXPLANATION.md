# Complete Flow: User Prompt to AI Response

This document explains each step in detail, from when a user writes a prompt and clicks enter to getting a response on the website.

## Architecture Overview

The system consists of:
1. **Frontend**: Streamlit application (`frontend.py`)
2. **Backend API**: Django REST API (`Django/aura/views.py`)
3. **LangGraph Service**: FastAPI service (`final_langgraph.py`) running on port 8200
4. **Supporting Services**: 
   - Image description service (port 8600)
   - Query rewrite service (port 8100)
   - MCP service (port 8600)
   - RAG service

---

## Detailed Step-by-Step Flow

### STEP 1: User Interaction - Entering Prompt (Frontend)

**Location**: `frontend.py` lines 379-388

1. **User types in the chat input field**
   - The input is in a Streamlit form with `key="chat_input_form"`
   - Placeholder text: "Ask about vehicle maintenance, repairs, or specifications..."
   - Form has `clear_on_submit=True` to clear input after submission

2. **User clicks "Enter" or the submit button (➤)**
   - Streamlit form automatically submits on Enter key press
   - The `submit_button` variable becomes `True`

3. **Form validation** (line 395)
   ```python
   if submit_button and prompt:
   ```
   - Checks if both button was clicked AND prompt is not empty
   - If valid, proceeds to message handling

---

### STEP 2: Image Processing (Frontend)

**Location**: `frontend.py` lines 397-403

1. **Check for uploaded images**
   - Images are uploaded via sidebar file uploader (lines 228-232)
   - Supports: PNG, JPG, JPEG formats
   - Multiple files can be selected

2. **Convert images to base64** (if any uploaded)
   ```python
   images_b64 = []
   if uploaded_images:
       for f in uploaded_images:
           images_b64.append(to_base64(f))  # Helper function line 24-25
   ```
   - Each image is read and encoded to base64 string
   - Base64 encoding allows binary image data to be sent as JSON

3. **Store images temporarily**
   - All images are collected into `images_b64` list
   - This list will be sent to the backend API

---

### STEP 3: Call `handle_send_message()` Function

**Location**: `frontend.py` line 406, function defined at lines 81-143

**Function Flow**:

1. **Validate chat exists** (lines 82-84)
   ```python
   if "selected_chat" not in st.session_state:
       st.error("No chat selected...")
       return
   ```
   - Ensures user has selected/created a chat session
   - Chat ID stored in `st.session_state["selected_chat"]`

2. **Check if this is the first message** (lines 88-90)
   ```python
   existing_msgs = get_messages(chat_id)
   is_first_message = len(existing_msgs) == 0
   ```
   - Fetches existing messages from backend
   - Used later for auto-generating chat title

3. **Display user's message in UI** (lines 93-96)
   ```python
   with st.chat_message("user"):
       st.markdown(message)
       if images_b64:
           st.image([base64.b64decode(img) for img in images_b64], width=100)
   ```
   - Immediately shows user message in chat interface
   - Decodes and displays uploaded images
   - This provides instant feedback before API response

4. **Show loading spinner** (line 98)
   ```python
   with st.spinner("AURA is thinking..."):
   ```
   - Indicates processing is happening

---

### STEP 4: Build Request Payload

**Location**: `frontend.py` lines 99-108

1. **Collect settings from session state**
   - `rag_on`: RAG (Retrieval-Augmented Generation) toggle state
   - `mcp_on`: MCP (Model Context Protocol) toggle state
   - `yt_on`: YouTube summary toggle state
   - Default: RAG=ON, others=OFF

2. **Build JSON payload**
   ```python
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
   ```

3. **Prepare cookies for authentication**
   - Session cookies stored in `st.session_state["cookies"]`
   - Cookies contain Django session ID for user authentication

---

### STEP 5: HTTP POST Request to Django Backend

**Location**: `frontend.py` line 111

```python
r = requests.post(f"{API}/chat", json=payload, cookies=st.session_state["cookies"])
```

**Details**:
- **Endpoint**: `POST http://15.207.100.115:8300/chat`
- **Content-Type**: `application/json`
- **Authentication**: Session cookies included
- **Timeout**: Default requests timeout (usually 30 seconds, but LangGraph can take up to 120 seconds)

**Request Body Structure**:
```json
{
  "chat_id": 123,
  "message": "How do I replace brake pads on BMW X5?",
  "images": ["base64_string_1", "base64_string_2"],
  "settings": {
    "rag": 1,
    "mcp": 0,
    "yt_summary": 0
  }
}
```

---

### STEP 6: Django Backend Receives Request

**Location**: `Django/aura/views.py` (chat endpoint - inferred from URL routing)

**Note**: The actual `chat` function implementation appears to be missing from views.py, but based on URL routing and imports, it should:

1. **Extract session user** (similar to other endpoints)
   ```python
   uid = request.session.get("user_id")
   if not uid:
       return JsonResponse({"error": "not logged in"}, 401)
   ```

2. **Parse JSON payload**
   ```python
   data = json.loads(request.body)
   chat_id = data["chat_id"]
   message = data["message"]
   images_b64 = data.get("images", [])
   settings = data["settings"]
   ```

3. **Save user message to database**
   ```python
   Message.objects.create(
       chat_id=chat_id,
       role="user",
       content=message
   )
   ```
   - Stores the user's message permanently
   - Links to the chat session

4. **Retrieve chat history** (if needed)
   ```python
   from aura.chat_history import chat_history_retrieval
   history = chat_history_retrieval(chat_id, word_limit=3000)
   ```
   - Fetches previous messages (up to 3000 words)
   - Formats as: `User: "query"\nBot: "response"\n...`
   - Used for context in AI generation

5. **Prepare LangGraph payload**
   ```python
   langgraph_payload = {
       "query": message,
       "chat_history": history,
       "images_base_64": images_b64,
       "mcp": settings["mcp"],
       "rag": settings["rag"],
       "yt_summary": settings["yt_summary"]
   }
   ```

---

### STEP 7: Call LangGraph Service

**Location**: `Django/aura/langgraph_runner.py` lines 8-11

```python
def run_langgraph(payload: dict) -> dict:
    resp = requests.post(LANGGRAPH_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()
```

**Details**:
- **Endpoint**: `POST http://15.207.100.115:8200/process`
- **Timeout**: 120 seconds (long timeout for AI processing)
- **This is a synchronous blocking call** - Django waits for response

---

### STEP 8: LangGraph Pipeline Processing

**Location**: `final_langgraph.py` - `master_pipeline()` function (lines 70-180)

This is the **core AI processing pipeline** with 4 main phases:

#### PHASE 1: Preprocessing (lines 76-86)

1. **Query Rewriting** (line 76)
   ```python
   rewritten_query = rewrite_query(data.query)
   ```
   - Calls service at `http://localhost:8100/rewrite`
   - Improves query clarity and structure
   - Returns: Enhanced/rewritten query string

2. **Chat History Summarization** (line 77)
   ```python
   history_summary = summarise_conversation(data.chat_history)
   ```
   - Calls service at `http://localhost:8100/summarise`
   - Condenses long chat history into concise summary
   - Returns: Summarized conversation context

3. **Image Description** (lines 79-82)
   ```python
   if data.images_base_64:
       img_desc = describe_images_locally(data.images_base_64)
   ```
   - Calls service at `http://localhost:8600/describe`
   - Uses vision model (Qwen2.5-VL-3B-Instruct) to describe images
   - Returns: Text description of uploaded images

4. **Combine into Ultimate Prompt** (line 86)
   ```python
   ultimate_prompt = history_summary + "\n" + rewritten_query + "\n" + img_desc
   ```
   - Merges all context into single prompt
   - Format: `[history summary]\n[rewritten query]\n[image descriptions]`

#### PHASE 2: MCP Pipeline (if enabled) (lines 99-109)

**Location**: `ai_preprocessing.py` lines 28-39, 63-91

If `mcp == 1`:

1. **Generate MCP-specific prompt** (line 101)
   ```python
   proper_mcp_prompt = mcp_prompt(ultimate_prompt)
   ```
   - Calls `http://localhost:8600/mcp_prompt`
   - Optimizes prompt for web search context

2. **Run full MCP pipeline** (lines 102-105)
   ```python
   mcp_output = await run_mcp_async(proper_mcp_prompt, yt_summary=data.yt_summary)
   ```
   - **Web Search**: Searches Google/web for relevant information
   - **YouTube Search**: Finds relevant YouTube videos
   - **Answer Generation**: Creates initial answer from search results
   - **YouTube Summarization** (if enabled): Summarizes found videos

3. **Extract results** (lines 107-109)
   ```python
   youtube_links = mcp_output.get("youtube_videos", [])
   google_links = mcp_output.get("links", [])
   youtube_summary = mcp_output.get("summaries", None)
   ```

#### PHASE 3: RAG Pipeline (if enabled) (lines 114-119)

If `rag == 1`:

1. **Generate RAG-specific prompt** (line 115)
   ```python
   proper_rag_prompt = generate_rag_prompt(ultimate_prompt)
   ```
   - Calls `http://localhost:8600/rag_prompt`
   - Optimizes prompt for document retrieval

2. **Run RAG retrieval** (line 116)
   ```python
   rag_output = await run_rag_async(proper_rag_prompt)
   ```
   - **Vector Search**: Searches embedded documents/PDFs
   - **Document Retrieval**: Finds relevant chunks from technical manuals
   - **Answer Generation**: Creates answer from retrieved documents

3. **Extract citations** (lines 118-119)
   ```python
   if rag_output.get("reference"):
       citation = [rag_output["reference"]]
   ```

#### PHASE 4: Final Answer Generation (lines 125-180)

**Location**: `genai_multimodal_helpers.py`

The system chooses one of 4 strategies based on enabled features:

**CASE 1: Nothing ON (MCP=0, RAG=0)** - lines 126-134
```python
final = prompt_only(ultimate_prompt, images_b64=data.images_base_64)
```
- Pure Claude (Bedrock) generation
- Uses only the ultimate prompt + images
- No external knowledge sources

**CASE 2: Only MCP (MCP=1, RAG=0)** - lines 137-149
```python
final = merge_with_polished(
    mcp_output.get("answer", ""),
    ultimate_prompt,
    data.images_base_64
)
```
- Merges MCP web search answer with user prompt
- Uses Claude to polish and combine
- Includes web/YouTube links

**CASE 3: Only RAG (MCP=0, RAG=1)** - lines 152-164
```python
final = merge_with_polished(
    rag_output.get("answer", ""),
    ultimate_prompt,
    data.images_base_64
)
```
- Merges RAG document answer with user prompt
- Uses Claude to polish and combine
- Includes document citations

**CASE 4: Both MCP + RAG (MCP=1, RAG=1)** - lines 167-180
```python
final = merge_two_polished(
    mcp_output.get("answer", ""),
    rag_output.get("answer", ""),
    ultimate_prompt,
    data.images_base_64
)
```
- Combines both MCP and RAG answers
- Uses Claude to intelligently merge both sources
- Includes web links, YouTube links, AND citations

**Final Response Structure**:
```python
{
    "final_response": final,              # The main AI answer (markdown)
    "youtube_links": youtube_links,      # List of YouTube URLs
    "google_links": google_links,        # List of web search URLs
    "citation": citation,                # List of document citations
    "youtube_summary": youtube_summary   # Summary of YouTube videos (if enabled)
}
```

---

### STEP 9: LangGraph Returns Response to Django

**Location**: `Django/aura/views.py` (chat endpoint - continuation)

1. **Receive LangGraph response**
   ```python
   langgraph_response = run_langgraph(langgraph_payload)
   ```

2. **Save assistant message to database**
   ```python
   Message.objects.create(
       chat_id=chat_id,
       role="agent",
       content=message,  # Original user message
       final_response=langgraph_response["final_response"],
       google_links=langgraph_response.get("google_links", []),
       youtube_links=langgraph_response.get("youtube_links", []),
       citations=langgraph_response.get("citation", []),
       youtube_summary=langgraph_response.get("youtube_summary")
   )
   ```

3. **Update chat timestamp**
   ```python
   chat = Chat.objects.get(id=chat_id)
   chat.save()  # Updates updated_at timestamp
   ```

4. **Return JSON response to frontend**
   ```python
   return JsonResponse({
       "final_response": langgraph_response["final_response"],
       "google_links": langgraph_response.get("google_links", []),
       "youtube_links": langgraph_response.get("youtube_links", []),
       "citations": langgraph_response.get("citation", []),
       "youtube_summary": langgraph_response.get("youtube_summary")
   })
   ```

---

### STEP 10: Frontend Receives Response

**Location**: `frontend.py` lines 113-135

1. **Check response status** (line 113)
   ```python
   if r.status_code == 200:
   ```
   - Success: Continue to display response
   - Error: Show error message (lines 138-143)

2. **Parse JSON response** (lines 114-115)
   ```python
   data = r.json()
   final_ans = data.get("final_response", "No response from AI.")
   ```

3. **Auto-generate chat title** (if first message) (lines 118-127)
   ```python
   if is_first_message:
       generated_title = generate_title(message)
       requests.patch(
           f"{API}/chats/{chat_id}",
           json={"title": generated_title},
           cookies=st.session_state["cookies"]
       )
   ```
   - Calls `http://localhost:8100/title_generation`
   - Creates a short, descriptive title from first message
   - Updates chat title in database

4. **Display AI response with typing animation** (lines 130-131)
   ```python
   with st.chat_message("assistant"):
       typing_animation(final_ans)
   ```
   - Shows response in assistant chat bubble
   - `typing_animation()` displays text character-by-character (lines 27-34)
   - Creates realistic typing effect with 0.002 second delay per character

---

### STEP 11: Display Additional Information

**Location**: `frontend.py` lines 312-332 (message display section)

When messages are loaded, the frontend displays:

1. **Main response** (already shown via typing animation)

2. **Google Links** (lines 321-323)
   ```python
   if m.get("google_links"):
       st.markdown("**🔍 Google Links**")
       for url in m["google_links"]: 
           st.markdown(f"- [{url}]({url})")
   ```

3. **YouTube Links** (lines 324-326)
   ```python
   if m.get("youtube_links"):
       st.markdown("**📺 YouTube Links**")
       for url in m.get("youtube_links"): 
           st.markdown(f"- [{url}]({url})")
   ```

4. **Citations** (lines 327-329)
   ```python
   if m.get("citations"):
       st.markdown("**📚 Citations**")
       for c in m.get("citations"): 
           st.markdown(f"- {c.get('source') or str(c)}")
   ```

5. **YouTube Summary** (lines 330-332)
   ```python
   if m.get("youtube_summary"):
       st.markdown("**📝 YouTube Summary**")
       st.markdown(m["youtube_summary"])
   ```

---

### STEP 12: Refresh UI

**Location**: `frontend.py` lines 133-135

1. **Wait briefly** (line 133)
   ```python
   time.sleep(0.4)
   ```
   - Allows typing animation to complete
   - Gives UI time to render

2. **Refresh chat list** (line 134)
   ```python
   st.session_state["chats"] = list_chats()
   ```
   - Fetches updated chat list from backend
   - Ensures new title (if generated) appears in sidebar

3. **Rerun Streamlit app** (line 135)
   ```python
   st.rerun()
   ```
   - Triggers full page rerender
   - Displays all messages including the new one
   - Resets form (clears input due to `clear_on_submit=True`)
   - Updates sidebar with latest chat title

---

## Complete Request/Response Flow Diagram

```
User Types → Enter Key
    ↓
Frontend: Validate & Process Images
    ↓
Frontend: Build Payload
    ↓
HTTP POST → Django API (/chat)
    ↓
Django: Authenticate & Save User Message
    ↓
Django: Retrieve Chat History
    ↓
Django: Build LangGraph Payload
    ↓
HTTP POST → LangGraph Service (/process)
    ↓
┌─────────────────────────────────────┐
│  LangGraph Pipeline:                │
│  1. Rewrite Query                   │
│  2. Summarize History               │
│  3. Describe Images                 │
│  4. Combine → Ultimate Prompt       │
│                                     │
│  IF MCP:                            │
│    - Web Search                     │
│    - YouTube Search                 │
│    - Generate Answer                │
│                                     │
│  IF RAG:                            │
│    - Vector Search                  │
│    - Retrieve Documents             │
│    - Generate Answer                │
│                                     │
│  5. Merge & Polish with Claude      │
│  6. Return Final Response           │
└─────────────────────────────────────┘
    ↓
LangGraph → Django (JSON Response)
    ↓
Django: Save Assistant Message
    ↓
Django → Frontend (JSON Response)
    ↓
Frontend: Display Response
    ↓
Frontend: Generate Title (if first message)
    ↓
Frontend: Refresh UI
    ↓
User Sees Complete Response
```

---

## Key Technologies & Services

1. **Frontend**: Streamlit (Python web framework)
2. **Backend API**: Django REST Framework
3. **Database**: SQLite (via Django ORM)
4. **AI Pipeline**: FastAPI (LangGraph service)
5. **AI Models**:
   - **Claude 3.5 Sonnet**: Main LLM (via AWS Bedrock)
   - **Qwen2.5-VL-3B-Instruct**: Vision model for images
6. **Vector Database**: For RAG (document embeddings)
7. **External APIs**: Google Search, YouTube API (via MCP)

---

## Error Handling

Throughout the flow, errors are handled at multiple levels:

1. **Frontend**: Try/except blocks catch connection errors
2. **Django**: Returns appropriate HTTP status codes
3. **LangGraph**: Raises exceptions for service failures
4. **User Experience**: Error messages displayed in UI

---

## Performance Considerations

- **Typing Animation**: Adds ~0.002s per character (visual polish)
- **LangGraph Timeout**: 120 seconds (allows for complex AI processing)
- **Chat History Limit**: 3000 words (prevents context overflow)
- **Parallel Processing**: MCP and RAG can run concurrently if both enabled
- **Caching**: Session state prevents redundant API calls

---

## Summary

The complete flow takes a user's prompt, processes it through multiple AI services (query rewriting, RAG retrieval, web search, image analysis), combines all context into a coherent response using Claude, and displays it back to the user with proper citations and links. The entire process is designed to provide accurate, well-sourced answers for vehicle maintenance and technical documentation queries.

