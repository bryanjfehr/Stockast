import sys
import re
import html

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
        clean_content = html.unescape(clean_content)
    except ImportError:
        pass  # html module not available

    return clean_content.strip()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python converter.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        cleaned_text = strip_tags(html_content)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        print(f"Successfully converted {input_file} to {output_file}")
    except FileNotFoundError:
        print(f"Error: File not found at {input_file}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
