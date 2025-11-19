import base64
import json
import mimetypes
import os
from pathlib import Path

import boto3


def get_bedrock_client(region: str | None = None):
    """
    Returns a Bedrock Runtime client configured for the given region.

    Make sure you have AWS credentials configured (env vars, ~/.aws/credentials, or an IAM role)
    and install the dependency:

        pip install boto3

    """
    region_name = region or os.getenv("AWS_REGION") or "us-east-1"
    return boto3.client("bedrock-runtime", region_name=region_name)


def _image_to_bedrock_content(image_path: str) -> dict:
    """
    Reads an image file and turns it into the structure Bedrock expects.
    """
    path = Path(image_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    media_type, _ = mimetypes.guess_type(path.name)
    media_type = media_type or "image/png"

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": encoded,
        },
    }


def call_claude_sonnet(
    prompt: str, *, image_path: str | None = None, max_tokens: int = 512
) -> str:
    """
    Minimal example of calling Claude 3 Sonnet on Amazon Bedrock.

    Pass image_path to test the vision-language flow.
    """
    client = get_bedrock_client()

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }

    if image_path:
        body["messages"][0]["content"].append(_image_to_bedrock_content(image_path))

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body).encode("utf-8"),
    )

    # Bedrock returns a streaming-like structure in 'body'; we read and parse it.
    raw = response["body"].read()
    data = json.loads(raw)

    # Claude 3 responses are in data["content"][0]["text"]
    return data["content"][0]["text"]


if __name__ == "__main__":
    # Example text-only call:
    print(call_claude_sonnet("Give one sentence about why RAG is useful."))

    # Vision test with a local image named 'image.png' next to this file.
    default_image = Path(__file__).with_name("image.png")
    if default_image.exists():
        print(
            call_claude_sonnet(
                "Describe what you see in this picture.",
                image_path=str(default_image),
            )
        )
    else:
        print(
            "Place an image named 'image.png' in the same directory to run the vision test."
        )


