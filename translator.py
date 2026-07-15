from deep_translator import GoogleTranslator

def translate_text(text, src="auto", trg="en"):
    """
    Translate text using the free GoogleTranslator engine.
    Returns the translated text or an error indicator if translation fails.
    """
    if not text.strip() or not trg or not trg.strip():
        return ""
    try:
        # GoogleTranslator expects standard language codes (e.g. 'th', 'en', 'es', 'zh-CN')
        translator = GoogleTranslator(source=src, target=trg)
        return translator.translate(text)
    except Exception as e:
        print(f"Translation failed ({src} -> {trg}): {e}")
        return f"[Translation Error: {e}]"

def get_languages():
    """
    Retrieve dictionary of supported languages mapping name to code.
    E.g. {'thai': 'th', 'english': 'en', ...}
    Includes a minimal fallback list if the API fetch fails.
    """
    try:
        # Fetches dynamically from deep-translator
        return GoogleTranslator().get_supported_languages(as_dict=True)
    except Exception as e:
        print(f"Failed to fetch dynamic languages list: {e}. Using fallback list.")
        # Fallback list of common languages
        return {
            "english": "en",
            "thai": "th",
            "spanish": "es",
            "french": "fr",
            "german": "de",
            "chinese (simplified)": "zh-CN",
            "chinese (traditional)": "zh-TW",
            "japanese": "ja",
            "korean": "ko",
            "russian": "ru",
            "arabic": "ar",
            "hindi": "hi",
            "italian": "it",
            "portuguese": "pt",
            "vietnamese": "vi"
        }
