from deep_translator import GoogleTranslator
import time

def translate_sentences(sentences, target_lang_name, progress_callback=None):
    """
    Translates a list of sentences into the target language.
    """
    # Mapping our UI language names to Google Translator ISO codes
    lang_map = {
        'English': 'en',
        'Indonesian': 'id',
        'Chinese': 'zh-CN',
        'Japanese': 'ja',
        'Korean': 'ko',
        'Arabic': 'ar',
        'Javanese': 'jv',
        'Other': 'en' # Fallback
    }
    
    target_code = lang_map.get(target_lang_name, 'en')
    
    translator = GoogleTranslator(source='auto', target=target_code)
    
    translated = []
    total = len(sentences)
    
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            translated.append("")
        else:
            try:
                # deep-translator handles retries, but we add a small sleep to avoid rate limits
                # if doing thousands of sentences
                if i > 0 and i % 50 == 0:
                    time.sleep(1) 
                    
                # deep-translator has a 5000 character limit. 
                # Scraped navigation menus sometimes don't have periods, causing huge "sentences".
                safe_sentence = sentence[:4900]
                
                res = translator.translate(safe_sentence)
                translated.append(res if res else safe_sentence)
            except Exception as e:
                print(f"Translation error on sentence {i} (Length {len(sentence)}): {e}")
                translated.append(sentence) # Fallback to original on error
                
        if progress_callback and i % max(1, total // 100) == 0:
            fraction = min(0.99, i / total)
            progress_callback(fraction, f"Translating: Sentence {i}/{total} to {target_lang_name}...")
            
    if progress_callback:
        progress_callback(1.0, "Translation complete!")
        
    return translated
