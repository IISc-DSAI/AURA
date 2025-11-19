from database.models import Message

def chat_history_retrieval(chat_id, word_limit=3000):
    """
    Returns chat history in the form:
    User: "query"\nBot: "response"\n ...
    Ensures the 3000-word limit NEVER cuts a message mid-way.
    """

    msgs = Message.objects.filter(chat_id=chat_id).order_by("-timestamp")

    formatted_blocks = []
    total_words = 0

    for m in msgs:
        # Format one block
        role = "User" if m.role == "user" else "Assistant"
        block = f'{role}: "{m.content}"'
        block_words = len(block.split())

        # If adding this block crosses limit, STOP — but only if we already have some blocks
        if total_words + block_words > word_limit:
            # If this is the FIRST block exceeding limit, still include it fully
            if total_words == 0:
                formatted_blocks.append(block)
            break

        formatted_blocks.append(block)
        total_words += block_words

    return "\n".join(formatted_blocks)
