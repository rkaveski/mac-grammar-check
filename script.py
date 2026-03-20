#!/usr/bin/env python
import json
import os
from pathlib import Path
import re
import sys

import requests


API_URL = "https://api.openai.com/v1/responses"
MODEL_NAME = "gpt-4.1-nano"
REQUEST_TIMEOUT_SECONDS = 120
MAX_OUTPUT_TOKENS = 6000
MAX_CHARS_PER_CHUNK = 12000
ENV_FILE_NAME = ".env"
ENV_KEY_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_ASSIGNMENT_SEPARATOR = "="
PARAGRAPH_SEPARATOR = "\n\n"
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")
OUTPUT_TEXT_TYPE = "output_text"
OUTPUT_TEXT_KEY = "output_text"
MESSAGE_TYPE = "message"
ERROR_KEY = "error"
OUTPUT_KEY = "output"
CONTENT_KEY = "content"
TEXT_KEY = "text"
TYPE_KEY = "type"
STATUS_KEY = "status"
INCOMPLETE_STATUS = "incomplete"
INCOMPLETE_DETAILS_KEY = "incomplete_details"
INCOMPLETE_RESPONSE_MESSAGE = (
    "The grammar check response was incomplete. Try a shorter selection."
)
UNEXPECTED_RESPONSE_MESSAGE = "Unexpected response format from OpenAI."
NETWORK_ERROR_MESSAGE = (
    "Could not reach OpenAI. Check your internet connection and try again."
)
MISSING_API_KEY_MESSAGE = "Missing OPENAI_API_KEY. Add it to a local .env file or export it in your environment."
INSTRUCTIONS = (
    "You are a careful copy editor. Correct grammar, spelling, punctuation, and spacing while preserving the original meaning, structure, and paragraph breaks. "
    "Rewrite in a natural casual style only when needed to improve fluency. Return only the corrected text with no explanations, headings, bullets, or quotes. "
    "Do not use em dashes."
)


def load_env_file():
    env_file_path = Path(__file__).resolve().with_name(ENV_FILE_NAME)
    if not env_file_path.exists():
        return

    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        if ENV_ASSIGNMENT_SEPARATOR not in stripped_line:
            continue

        key, value = stripped_line.split(ENV_ASSIGNMENT_SEPARATOR, 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"').strip("'")
        if normalized_key and normalized_key not in os.environ:
            os.environ[normalized_key] = normalized_value


def get_api_key():
    load_env_file()
    api_key = os.environ.get(ENV_KEY_OPENAI_API_KEY, "").strip()
    if api_key:
        return api_key

    raise Exception(MISSING_API_KEY_MESSAGE)


def build_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}",
    }


def build_payload(text):
    return {
        "model": MODEL_NAME,
        "instructions": INSTRUCTIONS,
        "input": text,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }


def split_long_segment(text, max_chars):
    stripped_text = text.strip()
    if len(stripped_text) <= max_chars:
        return [stripped_text]

    sentences = SENTENCE_BOUNDARY_PATTERN.split(stripped_text)
    if len(sentences) == 1:
        return [
            stripped_text[index : index + max_chars].strip()
            for index in range(0, len(stripped_text), max_chars)
            if stripped_text[index : index + max_chars].strip()
        ]

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_length = len(sentence) + (1 if current_chunk else 0)
        if current_chunk and current_length + sentence_length > max_chars:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = [sentence]
            current_length = len(sentence)
            continue

        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(" ".join(current_chunk).strip())
                current_chunk = []
                current_length = 0
            chunks.extend(split_long_segment(sentence, max_chars))
            continue

        current_chunk.append(sentence)
        current_length += sentence_length

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks


def chunk_text(text, max_chars=MAX_CHARS_PER_CHUNK):
    stripped_text = text.strip()
    if not stripped_text:
        return []

    paragraphs = stripped_text.split(PARAGRAPH_SEPARATOR)
    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        paragraph_length = len(paragraph)
        separator_length = len(PARAGRAPH_SEPARATOR) if current_chunk else 0

        if paragraph_length > max_chars:
            if current_chunk:
                chunks.append(PARAGRAPH_SEPARATOR.join(current_chunk).strip())
                current_chunk = []
                current_length = 0
            chunks.extend(split_long_segment(paragraph, max_chars))
            continue

        if (
            current_chunk
            and current_length + separator_length + paragraph_length > max_chars
        ):
            chunks.append(PARAGRAPH_SEPARATOR.join(current_chunk).strip())
            current_chunk = [paragraph]
            current_length = paragraph_length
            continue

        current_chunk.append(paragraph)
        current_length += separator_length + paragraph_length

    if current_chunk:
        chunks.append(PARAGRAPH_SEPARATOR.join(current_chunk).strip())

    return chunks


def extract_output_text(response_data):
    direct_output_text = response_data.get(OUTPUT_TEXT_KEY)
    if isinstance(direct_output_text, str) and direct_output_text.strip():
        return direct_output_text.strip()

    output_items = response_data.get(OUTPUT_KEY)
    if not isinstance(output_items, list):
        raise Exception(UNEXPECTED_RESPONSE_MESSAGE)

    text_parts = []
    for output_item in output_items:
        if not isinstance(output_item, dict):
            continue

        content_items = output_item.get(CONTENT_KEY, [])
        if not isinstance(content_items, list):
            continue

        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue

            item_type = content_item.get(TYPE_KEY)
            item_text = content_item.get(TEXT_KEY)
            if (
                item_type == OUTPUT_TEXT_TYPE
                and isinstance(item_text, str)
                and item_text
            ):
                text_parts.append(item_text)

        if output_item.get(TYPE_KEY) == MESSAGE_TYPE and not content_items:
            continue

    corrected_text = "".join(text_parts).strip()
    if corrected_text:
        return corrected_text

    if response_data.get(STATUS_KEY) == INCOMPLETE_STATUS:
        incomplete_details = response_data.get(INCOMPLETE_DETAILS_KEY, {})
        if isinstance(incomplete_details, dict):
            reason = incomplete_details.get("reason")
            if isinstance(reason, str) and reason:
                raise Exception(f"{INCOMPLETE_RESPONSE_MESSAGE} Reason: {reason}.")
        raise Exception(INCOMPLETE_RESPONSE_MESSAGE)

    raise Exception(UNEXPECTED_RESPONSE_MESSAGE)


def correct_chunk(text):
    try:
        response = requests.post(
            API_URL,
            headers=build_headers(),
            json=build_payload(text),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise Exception(f"{NETWORK_ERROR_MESSAGE} {error}")

    try:
        response_data = response.json()
    except json.JSONDecodeError:
        response.raise_for_status()
        raise Exception("OpenAI returned a non-JSON response.")

    if response.status_code >= 400:
        api_error = response_data.get(ERROR_KEY, {})
        if isinstance(api_error, dict):
            error_message = api_error.get("message")
            if isinstance(error_message, str) and error_message:
                raise Exception(f"API Error: {error_message}")
        response.raise_for_status()

    api_error = response_data.get(ERROR_KEY)
    if isinstance(api_error, dict):
        error_message = api_error.get("message")
        if isinstance(error_message, str) and error_message:
            raise Exception(f"API Error: {error_message}")

    return extract_output_text(response_data)


def correct_grammar(text):
    chunks = chunk_text(text)
    if not chunks:
        return ""

    corrected_chunks = []
    for chunk in chunks:
        corrected_chunks.append(correct_chunk(chunk))

    return PARAGRAPH_SEPARATOR.join(corrected_chunks).strip()


def main():
    try:
        input_text = sys.stdin.read()
        if not input_text or not input_text.strip():
            return

        corrected_text = correct_grammar(input_text)
        if corrected_text:
            print(corrected_text)
    except Exception as error:
        sys.stderr.write(str(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
