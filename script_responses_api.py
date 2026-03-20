#!/usr/bin/env python
import os
from pathlib import Path
import sys

import requests


ENV_FILE_NAME = ".env"
ENV_KEY_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_ASSIGNMENT_SEPARATOR = "="
MISSING_API_KEY_MESSAGE = "Missing OPENAI_API_KEY. Add it to a local .env file or export it in your environment."


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


def correct_grammar(text):
    api_key = get_api_key()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    instructions = (
        "You are a helpful assistant. Your only task is to correct grammar errors and transform the following text to a casual style. "
        "Ensure that all spacing and punctuation are correct. Do not add any extra text or formatting."
    )

    payload = {
        "model": "gpt-5-mini",
        "input": text,
        "instructions": instructions,
        "max_output_tokens": 1000,
    }

    response = requests.post(
        "https://api.openai.com/v1/responses", headers=headers, json=payload
    )

    response_data = response.json()
    # Remove debug lines for production use
    # print(f"DEBUG - Response status: {response.status_code}", file=sys.stderr)
    # print(f"DEBUG - Response data: {response_data}", file=sys.stderr)

    if response_data.get("error") is not None:
        raise Exception(f"API Error: {response_data['error']['message']}")

    # Extract text from the message output (skip reasoning output)
    if "output" in response_data and response_data["output"]:
        # Find the message type output (not reasoning type)
        for output_item in response_data["output"]:
            if output_item["type"] == "message":
                corrected_text = output_item["content"][0]["text"]
                break
        else:
            raise Exception(f"No message output found in response")
    else:
        raise Exception(f"Unexpected response format: {response_data}")

    return corrected_text.strip()


def main():
    input_text = sys.stdin.read()
    corrected_text = correct_grammar(input_text)
    print(corrected_text)


if __name__ == "__main__":
    main()
