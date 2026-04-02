# Grammar Check for macOS

This project lets you select text on your Mac, send it to any configured language-model API, and paste the corrected version back into the app you are using.

The workflow is provider-agnostic in code:

- the AppleScript only captures and pastes text
- the Python script only reads `.env`, sends one HTTP request, and parses the configured API format
- provider details such as URL, headers, model, and request format live in `.env`

It is built for everyday writing tasks like:

- emails
- messages
- notes
- short documents
- page-length text selections

## What it does

- fixes grammar, spelling, punctuation, and spacing
- keeps the original meaning and paragraph structure
- makes the text sound more natural when needed
- works with longer selections by splitting them into safe chunks behind the scenes

## What you need

- a Mac
- Python 3
- any model API endpoint you want to use
- the endpoint URL, auth headers if needed, model name, and API format

## Supported API formats

The script is API-endpoint agnostic, but it still needs to know the request and response shape.

Supported formats:

- `openai_responses`
- `openai_chat`
- `anthropic_messages`

That covers common setups such as:

- OpenAI
- Anthropic Claude
- DeepSeek
- OpenRouter
- LM Studio
- vLLM
- Ollama local or remote through its OpenAI-compatible endpoint
- any other gateway that matches one of those wire formats

## Quick setup

1. Download or clone this project.
2. Open Terminal and go into the project folder.
3. Create a Python virtual environment:

```bash
python3 -m venv venv
```

4. Activate it:

```bash
source venv/bin/activate
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Create a local `.env` file from the example:

```bash
cp .env.example .env
```

7. Edit `.env` with your own API details.

OpenAI example:

```env
AI_MODEL=gpt-4.1-nano
AI_API_FORMAT=openai_responses
AI_API_URL=https://api.openai.com/v1/responses
AI_API_HEADERS={"Authorization":"Bearer YOUR_API_KEY"}
```

Claude example:

```env
AI_MODEL=claude-3-7-sonnet-latest
AI_API_FORMAT=anthropic_messages
AI_API_URL=https://api.anthropic.com/v1/messages
AI_API_HEADERS={"x-api-key":"YOUR_API_KEY","anthropic-version":"2023-06-01"}
```

DeepSeek or another OpenAI-compatible endpoint:

```env
AI_MODEL=deepseek-chat
AI_API_FORMAT=openai_chat
AI_API_URL=https://api.deepseek.com/chat/completions
AI_API_HEADERS={"Authorization":"Bearer YOUR_API_KEY"}
```

Ollama on the same machine:

```env
AI_MODEL=llama3.1
AI_API_FORMAT=openai_chat
AI_API_URL=http://localhost:11434/v1/chat/completions
AI_API_HEADERS={}
```

Ollama on another machine or in Docker:

```env
AI_MODEL=llama3.1
AI_API_FORMAT=openai_chat
AI_API_URL=http://192.168.1.20:11434/v1/chat/completions
AI_API_HEADERS={}
```

Optional request extras:

```env
AI_API_BODY={"temperature":0.2}
```

## Basic test

Before connecting it to a macOS shortcut, test it in Terminal:

```bash
printf '%s' 'this are a test email. i hope you is well.' | venv/bin/python script.py
```

You should get back a corrected version of the text.

## Use it on your Mac with a Quick Action

The included AppleScript file is `grammar-check.applescript`.

You can use it in Automator as a Quick Action:

1. Open Automator.
2. Create a new `Quick Action`.
3. Set it to receive `no input` in `any application`.
4. Add a `Run AppleScript` action.
5. Replace the default script with the contents of `grammar-check.applescript`.
6. Save it with a name like `Grammar Check`.
7. In macOS keyboard settings, assign a shortcut if you want one.

After that, the usual flow is:

1. Select text in any app.
2. Run the Quick Action.
3. Wait a moment.
4. The corrected text is pasted back automatically.

## How it works

- `script.py` reads the endpoint config from `.env`
- `script.py` sends the selected text to the configured API URL
- `grammar-check.applescript` uses Quick Action input when available and otherwise copies the current selection directly
- longer text is split into chunks so page-length selections are more reliable

## Files in this project

- `script.py` - main grammar-check script
- `script_responses_api.py` - compatibility wrapper that calls `script.py`
- `grammar-check.applescript` - AppleScript for macOS Quick Actions
- `.env.example` - sample config for different API styles
- `requirements.txt` - Python dependencies

## Troubleshooting

If nothing happens:

- make sure your virtual environment exists in `venv/`
- make sure `.env` contains `AI_MODEL`, `AI_API_FORMAT`, `AI_API_URL`, and `AI_API_HEADERS`
- make sure the file paths inside `grammar-check.applescript` match where this project is stored on your Mac
- if macOS says the workflow is not allowed to send keystrokes, open `System Settings > Privacy & Security > Accessibility` and enable the app where you are trying to use this service

If you see an error dialog:

- check that your configured API URL is reachable from this Mac
- check that your headers are valid JSON
- check that your API format matches the endpoint you are calling
- check that your model name is valid for that endpoint
- try again with a smaller text selection if the input is unusually large
- if the dialog says `There was a problem with the input to the Service`, the Quick Action is probably configured to receive `text` or the current app is not exposing selected text to macOS Services

If the wrong text gets pasted:

- make sure the current app allows standard `Command-C` and `Command-V` keyboard shortcuts

## Privacy note

Selected text is sent to whichever API you configure in `.env`. If you use a remote service, do not use this workflow for sensitive text unless you are comfortable sending that content to that service. If you use a local endpoint, the text stays on the machine or network where that endpoint runs.

## License

This project uses the MIT License.
