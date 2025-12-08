import sys
import os

# Add the directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from deep_translator import GoogleTranslator
    print("✅ deep-translator imported successfully.")
    
    text = "This is a test sentence for translation."
    translated = GoogleTranslator(source='auto', target='ko').translate(text)
    print(f"Original: {text}")
    print(f"Translated: {translated}")
    
    if "테스트" in translated or "문장" in translated:
        print("✅ Translation works!")
    else:
        print("⚠️ Translation might be incorrect.")
        
except ImportError:
    print("❌ deep-translator not installed.")
except Exception as e:
    print(f"❌ Translation failed: {e}")
