# Grammar Check for macOS

This project lets you select text on your Mac, run a grammar and style cleanup with OpenAI, and paste the corrected version back into the app you are using.

It is built for everyday writing tasks like:

- emails
- messages
- notes
- short documents
- page-length text selections

It is not meant for book-length editing, but it is designed to handle much more than a single paragraph.

## What it does

- fixes grammar, spelling, punctuation, and spacing
- keeps the original meaning and paragraph structure
- makes the text sound more natural and casual when needed
- works with longer selections by splitting them into safe chunks behind the scenes

## What you need

- a Mac
- Python 3
- an OpenAI API key

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

7. Open `.env` and replace the placeholder with your real API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
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

- `script.py` sends the selected text to OpenAI using the Responses API
- `grammar-check.applescript` uses Quick Action input when available and otherwise copies the current selection directly
- longer text is split into chunks so page-length selections are more reliable

## Files in this project

- `script.py` - main grammar-check script
- `grammar-check.applescript` - AppleScript for macOS Quick Actions
- `requirements.txt` - Python dependencies
- `.env.example` - sample local config file for your API key

There are also a couple of older script files kept for reference.

## Troubleshooting

If nothing happens:

- make sure your virtual environment exists in `venv/`
- make sure `.env` contains a valid `OPENAI_API_KEY`
- make sure the file paths inside `grammar-check.applescript` match where this project is stored on your Mac
- make sure macOS has permission to let Automator or System Events control your keyboard

If you see an error dialog:

- check that your internet connection is working
- confirm your OpenAI API key is active
- try again with a smaller text selection if the input is unusually large
- if the dialog says `There was a problem with the input to the Service`, the Quick Action is probably configured to receive `text` or the current app is not exposing selected text to macOS Services
- re-open the workflow in Automator and set it to receive `no input` in `any application`, then paste in the latest `grammar-check.applescript`

If the wrong text gets pasted:

- make sure the current app allows standard `Command-C` and `Command-V` keyboard shortcuts

## Privacy note

Selected text is sent to the OpenAI API so it can be corrected. Do not use this workflow for sensitive text unless you are comfortable sending that content through your API account.

## Contributing

You do not need to be an expert to help improve this project.

Good first contributions:

- improve the README
- make the setup easier
- improve error messages
- make the AppleScript flow more reliable
- add small tests for chunking and response parsing

If you want to contribute code:

1. Create a branch.
2. Make a small focused change.
3. Test with both a short paragraph and a longer page-length sample.
4. Open a pull request with a simple explanation of what changed and why.

## License

This project uses the MIT License. That means people can use it, copy it, modify it, and share it freely, including in their own projects, as long as the license notice stays with the code.
