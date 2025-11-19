# import json
# import base64
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.contrib.auth.hashers import check_password, make_password

# from database.models import User, Chat, Message, Attachment
# from aura.chat_history import chat_history_retrieval
# from aura.langgraph_runner import run_langgraph   # your LangGraph call


# # ----------------------
# # AUTH ENDPOINTS
# # ----------------------

# @csrf_exempt
# def signup(request):
#     """Create a new user."""
#     data = json.loads(request.body)
#     email, name, password = data["email"], data["name"], data["password"]

#     if User.objects.filter(email=email).exists():
#         return JsonResponse({"error": "User exists"}, status=400)

#     u = User.objects.create(
#         email=email,
#         name=name,
#         password_hash=make_password(password)
#     )
#     request.session["user_id"] = u.id
#     return JsonResponse({"status": "ok"})


# @csrf_exempt
# def login(request):
#     """Login user and create session cookie."""
#     data = json.loads(request.body)
#     email, password = data["email"], data["password"]

#     try:
#         u = User.objects.get(email=email)
#     except User.DoesNotExist:
#         return JsonResponse({"error": "Invalid"}, status=400)

#     if not check_password(password, u.password_hash):
#         return JsonResponse({"error": "Invalid"}, status=400)

#     request.session["user_id"] = u.id
#     return JsonResponse({"status": "ok"})


# def me(request):
#     """Auto-login check for Streamlit frontend."""
#     uid = request.session.get("user_id")
#     if not uid:
#         return JsonResponse({"authenticated": False})
    
#     u = User.objects.get(id=uid)
#     return JsonResponse({
#         "authenticated": True,
#         "email": u.email,
#         "name": u.name
#     })


# # ----------------------
# # CHAT MANAGEMENT
# # ----------------------
# @csrf_exempt
# def chats(request):
#     """List all chats of logged-in user or create new chat."""
#     uid = request.session.get("user_id")
#     if not uid:
#         return JsonResponse({"error": "not logged in"}, status=401)

#     if request.method == "GET":
#         user_chats = Chat.objects.filter(user_id=uid).order_by("-updated_at")
#         return JsonResponse([
#             {"id": c.id, "title": c.title, "updated": c.updated_at.isoformat()}
#             for c in user_chats
#         ], safe=False)

#     if request.method == "POST":
#         data = json.loads(request.body)
#         title = data.get("title", "New Chat")
#         c = Chat.objects.create(user_id=uid, title=title)
#         return JsonResponse({"id": c.id, "title": c.title})


# @csrf_exempt
# def chat_detail(request, chat_id):
#     """Rename or delete chat."""
#     uid = request.session.get("user_id")
#     if not uid:
#         return JsonResponse({"error": "not logged in"}, 401)

#     c = Chat.objects.get(id=chat_id, user_id=uid)

#     if request.method == "PATCH":    # rename
#         data = json.loads(request.body)
#         c.title = data.get("title", c.title)
#         c.save()
#         return JsonResponse({"status": "ok"})

#     if request.method == "DELETE":
#         c.delete()
#         return JsonResponse({"status": "deleted"})


# def chat_messages(request, chat_id):
#     """Return messages for a chat."""
#     uid = request.session.get("user_id")
#     if not uid:
#         return JsonResponse({"error": "not logged in"}, 401)

#     msgs = Message.objects.filter(chat_id=chat_id).order_by("timestamp")
#     return JsonResponse([
#         {
#             "id": m.id,
#             "role": m.role,
#             "content": m.content,
#             "timestamp": m.timestamp.isoformat(),
#             "google_links": m.google_links,
#             "youtube_links": m.youtube_links,
#             "citations": m.citations,
#             "youtube_summary": m.youtube_summary,
#             "final_response": m.final_response,
#         }
#         for m in msgs
#     ], safe=False)


# # ----------------------
# # MAIN CHAT PIPELINE
# # ----------------------

# @csrf_exempt
# def chat(request):
#     """Main endpoint:
#     - Retrieves chat history
#     - Sends (query, images, toggles) to LangGraph
#     - Saves response + citations + attachments
#     """
#     uid = request.session.get("user_id")
#     if not uid:
#         return JsonResponse({"error": "not logged in"}, 401)

#     data = json.loads(request.body)

#     chat_id = data["chat_id"]
#     query = data["message"]
#     images_b64 = data.get("images", [])
#     settings = data.get("settings", {})   # {rag:0/1, mcp:0/1, yt_summary:0/1}

#     # --- format chat history for LangGraph ---
#     chat_history = chat_history_retrieval(chat_id)

#     # --- call your LangGraph pipeline ---
#     lg_payload = {
#         "query": query,
#         "chat_history": chat_history,
#         "images_base_64": images_b64,
#         "mcp": settings.get("mcp", 0),
#         "rag": settings.get("rag", 0),
#     }

#     if lg_payload["mcp"] == 1:
#         lg_payload["yt_summary"] = settings.get("yt_summary", 0)
#     else:
#         lg_payload["yt_summary"] = 0

#     llm_result = run_langgraph(lg_payload)

#     # llm_result must be:
#     # { final_response, youtube_links, google_links, citation, youtube_summary }

#     # --- Save user message ---
#     m_user = Message.objects.create(
#         chat_id=chat_id,
#         role="user",
#         content=query
#     )

#     # store images
#     for b64 in images_b64:
#         Attachment.objects.create(
#             message=m_user,
#             file_path=b64[:30],   # or actual storage url if you upload
#             mime_type="image/base64"
#         )

#     # --- Save AI message ---
#     main_text = llm_result.get("final_response", "")

#     Message.objects.create(
#         chat_id=chat_id,
#         role="agent",
#         content=main_text,
#         google_links=llm_result.get("google_links", []),
#         youtube_links=llm_result.get("youtube_links", []),
#         citations=llm_result.get("citation", []),
#         youtube_summary=llm_result.get("youtube_summary"),
#         final_response=llm_result.get("final_response"),
# )
#     # After saving the AI message, update the chat's updated_at
#     Chat.objects.filter(id=chat_id).update(updated_at=timezone.now())

#     return JsonResponse(llm_result)


import json
import base64
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from database.models import User, Chat, Message, Attachment, PipelineExecution
from aura.chat_history import chat_history_retrieval
from aura.langgraph_runner import run_langgraph   # FastAPI LangGraph call


# ----------------------
# AUTH ENDPOINTS
# ----------------------

@csrf_exempt
def signup(request):
    data = json.loads(request.body)
    email, name, password = data["email"], data["name"], data["password"]

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "User exists"}, status=400)

    u = User.objects.create(
        email=email,
        name=name,
        password_hash=make_password(password)
    )
    request.session["user_id"] = u.id
    return JsonResponse({"status": "ok"})


@csrf_exempt
def login(request):
    data = json.loads(request.body)
    email, password = data["email"], data["password"]

    try:
        u = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({"error": "Invalid"}, status=400)

    if not check_password(password, u.password_hash):
        return JsonResponse({"error": "Invalid"}, status=400)

    request.session["user_id"] = u.id
    return JsonResponse({"status": "ok"})


def me(request):
    uid = request.session.get("user_id")
    if not uid:
        return JsonResponse({"authenticated": False})

    u = User.objects.get(id=uid)
    return JsonResponse({
        "authenticated": True,
        "email": u.email,
        "name": u.name
    })


# ----------------------
# CHAT LIST + CRUD
# ----------------------

@csrf_exempt
def chats(request):
    uid = request.session.get("user_id")
    if not uid:
        return JsonResponse({"error": "not logged in"}, status=401)

    if request.method == "GET":
        user_chats = Chat.objects.filter(user_id=uid).order_by("-updated_at")
        return JsonResponse([
            {"id": c.id, "title": c.title, "updated": c.updated_at.isoformat()}
            for c in user_chats
        ], safe=False)

    if request.method == "POST":
        data = json.loads(request.body)
        title = data.get("title", "New Chat")
        c = Chat.objects.create(user_id=uid, title=title)
        return JsonResponse({"id": c.id, "title": c.title})


@csrf_exempt
def chat_detail(request, chat_id):
    uid = request.session.get("user_id")
    if not uid:
        return JsonResponse({"error": "not logged in"}, 401)

    c = Chat.objects.get(id=chat_id, user_id=uid)

    if request.method == "PATCH":
        data = json.loads(request.body)
        c.title = data.get("title", c.title)
        c.save()
        return JsonResponse({"status": "ok"})

    if request.method == "DELETE":
        c.delete()
        return JsonResponse({"status": "deleted"})


# ----------------------
# CHAT MESSAGES (WITH PIPELINE STEPS)
# ----------------------

def chat_messages(request, chat_id):
    uid = request.session.get("user_id")
    if not uid:
        return JsonResponse({"error": "not logged in"}, 401)

    msgs = Message.objects.filter(chat_id=chat_id).order_by("id")
    
    result = []
    for m in msgs:
        pe = getattr(m, "pipeline_execution", None)

        result.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
            "google_links": m.google_links,
            "youtube_links": m.youtube_links,
            "citations": m.citations,
            "youtube_summary": m.youtube_summary,
            "final_response": m.final_response,

            # pipeline execution block
            "pipeline_execution": {
                "retrieved_chat_history": pe.retrieved_chat_history,
                "original_query": pe.original_query,
                "rewritten_query": pe.rewritten_query,
                "chat_history_summary": pe.chat_history_summary,
                "image_description": pe.image_description,
                "has_images": pe.has_images,
                "ultimate_prompt": pe.ultimate_prompt,
                "mcp_prompt": pe.mcp_prompt,
                "rag_prompt": pe.rag_prompt,
                "mcp_output": pe.mcp_output,
                "rag_output": pe.rag_output,
                "final_answer_before_polish": pe.final_answer_before_polish,
                "mcp_enabled": pe.mcp_enabled,
                "rag_enabled": pe.rag_enabled,
                "yt_summary_enabled": pe.yt_summary_enabled,
            } if pe else None
        })

    return JsonResponse(result, safe=False)


# ----------------------
# MAIN CHAT PIPELINE
# ----------------------

@csrf_exempt
def chat(request):
    uid = request.session.get("user_id")
    if not uid:
        return JsonResponse({"error": "not logged in"}, 401)

    data = json.loads(request.body)

    chat_id = data["chat_id"]
    query = data["message"]
    images_b64 = data.get("images", [])
    settings = data.get("settings", {})

    # prepare chat history
    chat_history = chat_history_retrieval(chat_id)

    # construct payload for LangGraph
    lg_payload = {
        "query": query,
        "chat_history": chat_history,
        "images_base_64": images_b64,
        "mcp": settings.get("mcp", 0),
        "rag": settings.get("rag", 0),
        "yt_summary": settings.get("yt_summary", 0) if settings.get("mcp", 0) == 1 else 0,
    }

    # call LangGraph (FastAPI)
    llm_result = run_langgraph(lg_payload)

    # extract intermediate steps
    intermediate = llm_result.get("intermediate_steps", {})

    # save user message
    m_user = Message.objects.create(
        chat_id=chat_id,
        role="user",
        content=query
    )

    # save image attachments
    for b64 in images_b64:
        Attachment.objects.create(
            message=m_user,
            file_path=b64[:30],
            mime_type="image/base64"
        )

    # save AI message
    ai_message = Message.objects.create(
        chat_id=chat_id,
        role="agent",
        content=llm_result.get("final_response", ""),
        google_links=llm_result.get("google_links", []),
        youtube_links=llm_result.get("youtube_links", []),
        citations=llm_result.get("citation", []),
        youtube_summary=llm_result.get("youtube_summary"),
        final_response=llm_result.get("final_response"),
    )

    # save pipeline execution metadata
    PipelineExecution.objects.create(
        message=ai_message,
        retrieved_chat_history=intermediate.get("retrieved_chat_history"),
        original_query=intermediate.get("original_query", query),
        rewritten_query=intermediate.get("rewritten_query"),
        chat_history_summary=intermediate.get("chat_history_summary"),
        image_description=intermediate.get("image_description"),
        has_images=intermediate.get("has_images", False),
        ultimate_prompt=intermediate.get("ultimate_prompt"),
        mcp_prompt=intermediate.get("mcp_prompt"),
        rag_prompt=intermediate.get("rag_prompt"),
        mcp_output=intermediate.get("mcp_output", {}),
        rag_output=intermediate.get("rag_output", {}),
        final_answer_before_polish=intermediate.get("final_answer_before_polish"),
        mcp_enabled=intermediate.get("mcp_enabled", False),
        rag_enabled=intermediate.get("rag_enabled", False),
        yt_summary_enabled=intermediate.get("yt_summary_enabled", False),
    )

    Chat.objects.filter(id=chat_id).update(updated_at=timezone.now())

    return JsonResponse(llm_result)
