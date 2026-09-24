"""Try the same translation service from the command line."""
import argparse
import json
from dotenv import load_dotenv
from src.translator import TranslationError, translate_note

load_dotenv()
parser = argparse.ArgumentParser(description='Translate text with the configured OpenRouter model')
parser.add_argument('text', help='Text to translate')
parser.add_argument('--to', default='简体中文', help='Target language')
args = parser.parse_args()
try:
    result = translate_note('', args.text, args.to)
    print(json.dumps(result, ensure_ascii=False, indent=2))
except TranslationError as exc:
    parser.exit(1, f'Translation failed: {exc}\n')
