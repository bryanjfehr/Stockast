import re
import sys

def strip_tags(html_content):
    # More robust regex to handle various HTML attributes and structures
    # Remove script and style elements
    clean_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
    clean_content = re.sub(r'<style.*?</style>', '', clean_content, flags=re.DOTALL)
    # Remove HTML tags
    clean_content = re.sub(r'<[^>]+>', '', clean_content)
    # Remove leftover CSS and JavaScript
    clean_content = re.sub(r'\{[^\}]*\}', '', clean_content)
    clean_content = re.sub(r'function\s*\w*\s*\([^\)]*\)\s*\{[^\}]*\}', '', clean_content)
    # Remove extra whitespace
    clean_content = re.sub(r'\s+', ' ', clean_content)
    # Decode HTML entities
    try:
        import html
        clean_content = html.unescape(clean_content)
    except ImportError:
        pass  # html module not available

    return clean_content.strip()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If a filename is provided as a command-line argument, read from that file
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            # Process the content and print the cleaned text
            cleaned_text = strip_tags(html_content)
            print(cleaned_text)
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}", file=sys.stderr)
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
    else:
        # If no filename is provided, read from standard input
        html_content = sys.stdin.read()
        # Process the content and print the cleaned text
        cleaned_text = strip_tags(html_content)
        print(cleaned_text)