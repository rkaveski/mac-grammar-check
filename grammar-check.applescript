-- '/Users/rodrigodapazkaveski/Library/Services/Grammar Check.workflow'

property projectRoot : "/Users/rodrigodapazkaveski/Sites/grammar-check"
property venvPythonPath : projectRoot & "/venv/bin/python"
property checkerScriptPath : projectRoot & "/script.py"
property tempFileTemplate : "/tmp/grammar-check-input.XXXXXX"
property okButtonLabel : "OK"
property notificationTitle : "Grammar Check"
property noChangesMessage : "No corrections were made or the input was already correct."
property emptyInputMessage : "No text was selected."
property copyFailureMessage : "Could not read the current selection. In Automator, set the Quick Action to receive no input in any application."
property shellPrefix : "/bin/sh -c "
property copyPollAttempts : 20
property copyPollDelaySeconds : 0.1
property pasteRestoreDelaySeconds : 0.1

on run {input, parameters}
	set originalClipboard to my readClipboardSafely()
	set selectedText to my normalizeSelectedText(input)
	if selectedText is "" then
		set selectedText to my copySelectedText()
	end if
	if selectedText is "" then
		my showInfoDialog(emptyInputMessage)
		return input
	end if

	set tempInputPath to do shell script "mktemp " & quoted form of tempFileTemplate

	try
		set fileHandle to open for access POSIX file tempInputPath with write permission
		set eof fileHandle to 0
		write selectedText to fileHandle as «class utf8»
		close access fileHandle

		set shellCommand to quoted form of (venvPythonPath & space & quoted form of checkerScriptPath & " < " & quoted form of tempInputPath)
		set correctedText to do shell script shellPrefix & shellCommand

		if correctedText is not "" and correctedText is not selectedText then
			my pasteReplacementText(correctedText, originalClipboard)
		else
			my restoreClipboard(originalClipboard)
			my showInfoDialog(noChangesMessage)
		end if
	on error errorMessage number errorNumber
		try
			close access POSIX file tempInputPath
		end try
		my restoreClipboard(originalClipboard)
		display dialog errorMessage buttons {okButtonLabel} default button okButtonLabel with title notificationTitle
		return input
	end try

	try
		close access POSIX file tempInputPath
	end try
	do shell script "rm -f " & quoted form of tempInputPath

	return input
end run

on normalizeSelectedText(rawInput)
	if rawInput is missing value then return ""

	if class of rawInput is list then
		if rawInput is {} then return ""
		return my normalizeSelectedText(item 1 of rawInput)
	end if

	try
		return (rawInput as text)
	on error
		return ""
	end try
end normalizeSelectedText

on readClipboardSafely()
	try
		return the clipboard
	on error
		return missing value
	end try
end readClipboardSafely

on copySelectedText()
	set clipboardSentinel to do shell script "uuidgen"
	set the clipboard to clipboardSentinel

	tell application "System Events"
		keystroke "c" using command down
	end tell

	repeat with pollAttempt from 1 to copyPollAttempts
		delay copyPollDelaySeconds
		try
			set copiedText to the clipboard as text
			if copiedText is not clipboardSentinel and copiedText is not "" then
				return copiedText
			end if
		end try
	end repeat

	error copyFailureMessage
end copySelectedText

on pasteReplacementText(correctedText, originalClipboard)
	set the clipboard to correctedText
	tell application "System Events"
		keystroke "v" using command down
	end tell
	delay pasteRestoreDelaySeconds
	my restoreClipboard(originalClipboard)
end pasteReplacementText

on restoreClipboard(originalClipboard)
	if originalClipboard is missing value then return

	try
		set the clipboard to originalClipboard
	end try
end restoreClipboard

on showInfoDialog(messageText)
	display dialog messageText buttons {okButtonLabel} default button okButtonLabel with title notificationTitle
end showInfoDialog
