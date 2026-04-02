#!/usr/bin/env python
import json
import os
from pathlib import Path
import re
import sys

import requests


REQUEST_TIMEOUT_SECONDS = 120
MAX_OUTPUT_TOKENS = 6000
MAX_CHARS_PER_CHUNK = 12000
ENV_FILE_NAME = ".env"
ENV_ASSIGNMENT_SEPARATOR = "="
PARAGRAPH_SEPARATOR = "\n\n"
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")

FORMAT_OPENAI_RESPONSES = "openai_responses"
FORMAT_OPENAI_CHAT = "openai_chat"
FORMAT_ANTHROPIC_MESSAGES = "anthropic_messages"
SUPPORTED_API_FORMATS = {
    FORMAT_OPENAI_RESPONSES,
    FORMAT_OPENAI_CHAT,
    FORMAT_ANTHROPIC_MESSAGES,
}

ENV_KEY_AI_MODEL = "AI_MODEL"
ENV_KEY_AI_API_URL = "AI_API_URL"
ENV_KEY_AI_API_HEADERS = "AI_API_HEADERS"
ENV_KEY_AI_API_FORMAT = "AI_API_FORMAT"
ENV_KEY_AI_API_BODY = "AI_API_BODY"
ENV_KEY_OPENAI_API_KEY = "OPENAI_API_KEY"

ERROR_KEY = "error"
CHOICES_KEY = "choices"
MESSAGE_KEY = "message"
CONTENT_KEY = "content"
TEXT_KEY = "text"
OUTPUT_KEY = "output"
OUTPUT_TEXT_KEY = "output_text"
TYPE_KEY = "type"
STATUS_KEY = "status"
INCOMPLETE_STATUS = "incomplete"
INCOMPLETE_DETAILS_KEY = "incomplete_details"
OUTPUT_TEXT_TYPE = "output_text"
STOP_REASON_KEY = "stop_reason"
FINISH_REASON_KEY = "finish_reason"

INCOMPLETE_RESPONSE_MESSAGE = (
    "The grammar check response was incomplete. Try a shorter selection."
)
UNEXPECTED_RESPONSE_MESSAGE = "Unexpected response format from the AI API."
NETWORK_ERROR_MESSAGE = (
    "Could not reach the configured AI API. Check `AI_API_URL` and try again."
)
MISSING_API_URL_MESSAGE = "Missing `AI_API_URL` in `.env`."
MISSING_MODEL_MESSAGE = "Missing `AI_MODEL` in `.env`."
INVALID_HEADERS_MESSAGE = "`AI_API_HEADERS` must be a JSON object string."
INVALID_BODY_MESSAGE = "`AI_API_BODY` must be a JSON object string."
UNSUPPORTED_API_FORMAT_MESSAGE = (
    "Unsupported `AI_API_FORMAT`. Use `openai_responses`, `openai_chat`, or `anthropic_messages`."
)
INSTRUCTIONS = """You are a writing refinement engine specialized in correcting grammar, clarity, and flow while preserving the author’s original style.

Your task is to improve text written by a high-proficiency, non-native English speaker who prefers direct, efficient, and intent-driven communication.

Core behavior:
    - Preserve style. Do not rewrite into formal, polished, or "perfect" English if it changes the tone. Keep the author’s concise, slightly telegraphic structure when it remains clear.
    - Correct only what is necessary. Fix grammar, tense, articles, prepositions, and obvious phrasing issues. Avoid unnecessary rewording.
    - Maintain directness. Do not add filler, transitions, or softening language. Keep sentences compact and functional.
    - Preserve meaning exactly. Do not reinterpret, expand, or simplify ideas beyond grammatical correction.
    - Keep technical precision. Do not replace domain-specific terms with simpler or more generic alternatives.
    - Respect mixed formality. If the input is casual, keep it casual. If it is formal, keep it formal. Do not shift tone.

Fluency and punctuation rules:
    - Prefer human-like flow. Reduce rigid or overly segmented sentences when possible.
    - Use commas to improve readability and natural rhythm where appropriate.
    - Avoid excessive sentence fragmentation. Do not split ideas into multiple short sentences unless needed for clarity.
    - Avoid em dashes. Prefer commas or periods instead, unless an em dash is clearly intentional by the author.
    - Keep punctuation aligned with the author’s style and level of formality.

Transformation rules:
    - Fix grammatical errors (tense, agreement, articles, prepositions).
    - Improve sentence flow only when the original is hard to read.
    - Break or merge sentences only if it improves clarity without changing tone.
    - Normalize obvious typos and spelling errors.
    - Keep punctuation minimal and aligned with the original style.

Do not:
    - Add explanations, comments, or justifications.
    - Introduce new content, examples, or clarifications.
    - Change tone to be more polite, academic, or verbose.
    - Over-correct into native-level idiomatic expressions if it alters the author’s voice.

Output format:
    - Return only the corrected text.
    - Do not include quotes, annotations, or metadata.
    - If the input is already clear and correct, return it unchanged.

Quality target:
    - The result should read as the same author, but with cleaner grammar and slightly improved flow.
    - High signal, low ornamentation."""


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


def get_env(name, default=""):
    return os.environ.get(name, default).strip()


def require_env(name, message):
    value = get_env(name)
    if value:
        return value
    raise Exception(message)


def parse_json_object(name, value, empty_default):
    if not value:
        return empty_default

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise Exception(f"{name}: {error.msg}.")

    if not isinstance(parsed, dict):
        raise Exception(
            INVALID_HEADERS_MESSAGE if name == ENV_KEY_AI_API_HEADERS else INVALID_BODY_MESSAGE
        )

    return parsed


def get_api_format():
    load_env_file()
    api_format = get_env(ENV_KEY_AI_API_FORMAT, FORMAT_OPENAI_RESPONSES).lower()
    if api_format not in SUPPORTED_API_FORMATS:
        raise Exception(UNSUPPORTED_API_FORMAT_MESSAGE)
    return api_format


def get_api_url():
    return require_env(ENV_KEY_AI_API_URL, MISSING_API_URL_MESSAGE)


def get_model_name():
    return require_env(ENV_KEY_AI_MODEL, MISSING_MODEL_MESSAGE)


def substitute_header_values(headers):
    api_key = get_env(ENV_KEY_OPENAI_API_KEY)
    substituted_headers = {}
    for key, value in headers.items():
        if not isinstance(value, str):
            substituted_headers[key] = value
            continue

        substituted_headers[key] = (
            value.replace("${OPENAI_API_KEY}", api_key).replace("${AI_MODEL}", get_model_name())
        )

    return substituted_headers


def build_headers():
    headers = {"Content-Type": "application/json"}
    configured_headers = parse_json_object(
        ENV_KEY_AI_API_HEADERS,
        get_env(ENV_KEY_AI_API_HEADERS),
        {},
    )
    headers.update(substitute_header_values(configured_headers))
    return headers


def build_openai_responses_payload(text):
    return {
        "model": get_model_name(),
        "instructions": INSTRUCTIONS,
        "input": text,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }


def build_openai_chat_payload(text):
    return {
        "model": get_model_name(),
        "messages": [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": text},
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
    }


def build_anthropic_messages_payload(text):
    return {
        "model": get_model_name(),
        "system": INSTRUCTIONS,
        "messages": [{"role": "user", "content": text}],
        "max_tokens": MAX_OUTPUT_TOKENS,
    }


def build_payload(api_format, text):
    if api_format == FORMAT_OPENAI_RESPONSES:
        payload = build_openai_responses_payload(text)
    elif api_format == FORMAT_OPENAI_CHAT:
        payload = build_openai_chat_payload(text)
    elif api_format == FORMAT_ANTHROPIC_MESSAGES:
        payload = build_anthropic_messages_payload(text)
    else:
        raise Exception(UNSUPPORTED_API_FORMAT_MESSAGE)

    extra_body = parse_json_object(
        ENV_KEY_AI_API_BODY,
        get_env(ENV_KEY_AI_API_BODY),
        {},
    )
    payload.update(extra_body)
    return payload


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


def extract_openai_responses_text(response_data):
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


def extract_openai_chat_text(response_data):
    choices = response_data.get(CHOICES_KEY)
    if not isinstance(choices, list) or not choices:
        raise Exception(UNEXPECTED_RESPONSE_MESSAGE)

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise Exception(UNEXPECTED_RESPONSE_MESSAGE)

    message = first_choice.get(MESSAGE_KEY, {})
    if not isinstance(message, dict):
        raise Exception(UNEXPECTED_RESPONSE_MESSAGE)

    content = message.get(CONTENT_KEY)
    if isinstance(content, str) and content.strip():
        return content.strip()

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if not isinstance(item, dict):
                continue

            item_text = item.get(TEXT_KEY)
            if isinstance(item_text, str) and item_text.strip():
                text_parts.append(item_text.strip())

        if text_parts:
            return "".join(text_parts).strip()

    if first_choice.get(FINISH_REASON_KEY) == "length":
        raise Exception(INCOMPLETE_RESPONSE_MESSAGE)

    raise Exception(UNEXPECTED_RESPONSE_MESSAGE)


def extract_anthropic_messages_text(response_data):
    content_items = response_data.get(CONTENT_KEY)
    if not isinstance(content_items, list):
        raise Exception(UNEXPECTED_RESPONSE_MESSAGE)

    text_parts = []
    for item in content_items:
        if not isinstance(item, dict):
            continue

        if item.get(TYPE_KEY) != TEXT_KEY:
            continue

        item_text = item.get(TEXT_KEY)
        if isinstance(item_text, str) and item_text.strip():
            text_parts.append(item_text.strip())

    corrected_text = "".join(text_parts).strip()
    if corrected_text:
        return corrected_text

    if response_data.get(STOP_REASON_KEY) == "max_tokens":
        raise Exception(INCOMPLETE_RESPONSE_MESSAGE)

    raise Exception(UNEXPECTED_RESPONSE_MESSAGE)


def extract_error_message(response_data):
    api_error = response_data.get(ERROR_KEY)
    if isinstance(api_error, dict):
        message = api_error.get(MESSAGE_KEY)
        if isinstance(message, str) and message:
            return message

    if isinstance(api_error, str) and api_error:
        return api_error

    message = response_data.get(MESSAGE_KEY)
    if isinstance(message, str) and message:
        return message

    if response_data.get(TYPE_KEY) == ERROR_KEY:
        error_message = response_data.get(ERROR_KEY, response_data.get(MESSAGE_KEY))
        if isinstance(error_message, str) and error_message:
            return error_message

    return ""


def extract_output_text(api_format, response_data):
    if api_format == FORMAT_OPENAI_RESPONSES:
        return extract_openai_responses_text(response_data)

    if api_format == FORMAT_OPENAI_CHAT:
        return extract_openai_chat_text(response_data)

    if api_format == FORMAT_ANTHROPIC_MESSAGES:
        return extract_anthropic_messages_text(response_data)

    raise Exception(UNSUPPORTED_API_FORMAT_MESSAGE)


def correct_chunk(text):
    api_format = get_api_format()

    try:
        response = requests.post(
            get_api_url(),
            headers=build_headers(),
            json=build_payload(api_format, text),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise Exception(f"{NETWORK_ERROR_MESSAGE} {error}")

    try:
        response_data = response.json()
    except json.JSONDecodeError:
        response.raise_for_status()
        raise Exception("The AI API returned a non-JSON response.")

    if response.status_code >= 400:
        error_message = extract_error_message(response_data)
        if error_message:
            raise Exception(f"API Error: {error_message}")
        response.raise_for_status()

    error_message = extract_error_message(response_data)
    if error_message and response_data.get(ERROR_KEY) is not None:
        raise Exception(f"API Error: {error_message}")

    return extract_output_text(api_format, response_data)


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
