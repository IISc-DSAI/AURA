# from django.db import models

# class User(models.Model):
#     email = models.CharField(max_length=255, unique=True)
#     name = models.CharField(max_length=255)
#     password_hash = models.CharField(max_length=255)
#     auth_key = models.CharField(max_length=255, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.email


# class Chat(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats')
#     title = models.CharField(max_length=300, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title or f"Chat {self.id}"


# class Message(models.Model):
#     chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
#     role = models.CharField(max_length=20, choices=[('user', 'user'), ('agent', 'agent')])
#     content = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.role}: {self.content[:30]}"



from django.db import models

# -----------------------------
# User model (simple + fast)
# -----------------------------
class User(models.Model):
    email = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    password_hash = models.CharField(max_length=255)   # hashed password
    auth_key = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email


# -----------------------------
# Each chat session
# -----------------------------
class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats")
    title = models.CharField(max_length=300, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Chat {self.id}"


# -----------------------------
# Messages inside a chat
# role = user / agent / system
# -----------------------------
class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "user"),
        ("agent", "agent"),
        ("system", "system"),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()       # text (markdown allowed)
    timestamp = models.DateTimeField(auto_now_add=True)

    google_links = models.JSONField(default=list, blank=True)
    youtube_links = models.JSONField(default=list, blank=True)
    citations = models.JSONField(default=list, blank=True)
    youtube_summary = models.TextField(blank=True, null=True)
    final_response = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class PipelineExecution(models.Model):
    """Stores intermediate pipeline steps for debugging/monitoring."""
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='pipeline_execution')
    
    # Step 1: Retrieved chat history
    retrieved_chat_history = models.TextField(blank=True, null=True)
    
    # Step 2: Query rewriting
    original_query = models.TextField()
    rewritten_query = models.TextField(blank=True, null=True)
    
    # Step 3: Chat history summarization
    chat_history_summary = models.TextField(blank=True, null=True)
    
    # Step 4: Image description
    image_description = models.TextField(blank=True, null=True)
    has_images = models.BooleanField(default=False)
    
    # Step 5: Prompt generation
    ultimate_prompt = models.TextField(blank=True, null=True)  # Combined prompt
    mcp_prompt = models.TextField(blank=True, null=True)
    rag_prompt = models.TextField(blank=True, null=True)
    
    # Step 6: Pipeline outputs
    mcp_output = models.JSONField(default=dict, blank=True)  # Store full MCP output
    rag_output = models.JSONField(default=dict, blank=True)  # Store full RAG output
    
    # Step 7: Final answer generation
    final_answer_before_polish = models.TextField(blank=True, null=True)
    
    # Pipeline settings
    mcp_enabled = models.BooleanField(default=False)
    rag_enabled = models.BooleanField(default=False)
    yt_summary_enabled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)


class Attachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
