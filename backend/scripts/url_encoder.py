import argparse
from urllib.parse import quote_plus

def main():
    """
    A simple command-line tool to URL-encode a string.
    """
    # Set up the argument parser to accept a string from the command line.
    parser = argparse.ArgumentParser(
        description="URL-encode a given string (e.g., a password).",
        epilog="Example: python url_encoder.py \"MyP@ssw#rd!\""
    )
    parser.add_argument(
        "string_to_encode",
        help="The string you want to URL-encode."
    )

    args = parser.parse_args()
    original_string = args.string_to_encode

    # Use quote_plus to encode the string, which also converts spaces to '+'
    encoded_string = quote_plus(original_string)

    print(f"\nOriginal:  {original_string}")
    print(f"Encoded:   {encoded_string}\n")

if __name__ == "__main__":
    main()