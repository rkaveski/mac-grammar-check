-- Paste this script into an Automator Quick Action.
-- Set `projectRoot` to the absolute path where this repo lives on your Mac.
-- Example: /Users/your-name/mac-grammar-check

property projectRoot : "__PROJECT_ROOT__"
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

		if correctedText is selectedText then
			display notification noChangesMessage with title notificationTitle
		else
			set the clipboard to correctedText
			my pasteClipboard()
			delay pasteRestoreDelaySeconds
			set the clipboard to originalClipboard
			display notification "Text corrected and pasted." with title notificationTitle
		end if
	on error errMsg number errNum
		try
			close access POSIX file tempInputPath
		end try
		do shell script "rm -f " & quoted form of tempInputPath
		if errNum is not -128 then
			my showErrorDialog(errMsg)
		end if
		return input
	end try

	try
		close access POSIX file tempInputPath
	end try
	do shell script "rm -f " & quoted form of tempInputPath
	return input
end run

on normalizeSelectedText(inputValue)
	if class of inputValue is list then
		if (count of inputValue) is 0 then return ""
		try
			return item 1 of inputValue as text
		on error
			return ""
		end try
	end if
	try
		return inputValue as text
	on error
		return ""
	end try
end normalizeSelectedText

on copySelectedText()
	set previousClipboard to my readClipboardSafely()
	tell application "System Events"
		keystroke "c" using command down
	end tell

	repeat copyPollAttempts times
		delay copyPollDelaySeconds
		set currentClipboard to my readClipboardSafely()
		if currentClipboard is not previousClipboard and currentClipboard is not "" then
			return currentClipboard
		end if
	end repeat

	error copyFailureMessage number 1001
end copySelectedText

on readClipboardSafely()
	try
		return the clipboard as text
	on error
		return ""
	end try
end readClipboardSafely

on pasteClipboard()
	tell application "System Events"
		keystroke "v" using command down
	end tell
end pasteClipboard

on showInfoDialog(messageText)
	display dialog messageText buttons {okButtonLabel} default button okButtonLabel with title notificationTitle
end showInfoDialog

on showErrorDialog(messageText)
	display dialog messageText buttons {okButtonLabel} default button okButtonLabel with title notificationTitle with icon caution
end showErrorDialog
