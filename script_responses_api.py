#!/usr/bin/env python
import sys

from script import correct_grammar


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
