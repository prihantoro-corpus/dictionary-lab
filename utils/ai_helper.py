"""
AI Helper Module for Dictionary Lab
Supports both local (Ollama) and cloud (Google Gemini) AI providers
"""

import requests
import json
from typing import List, Dict, Optional, Any

class AIHelper:
    """Unified AI interface for dictionary entry generation"""
    
    def __init__(self, provider: str = "ollama", api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize AI Helper
        
        Args:
            provider: "ollama" or "gemini"
            api_key: API key for cloud providers (required for Gemini)
            model: Model name (optional, uses defaults if not specified)
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or self._get_default_model()
        
        # Initialize Gemini if needed
        if self.provider == "gemini":
            if not api_key:
                raise ValueError("API key required for Gemini provider")
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.genai = genai
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    def _get_default_model(self) -> str:
        """Get default model for the provider"""
        if self.provider == "ollama":
            return "llama3.2"
        elif self.provider == "gemini":
            return "gemini-2.0-flash-exp"
        return "llama3.2"
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to AI provider"""
        try:
            if self.provider == "ollama":
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m.get('name') for m in models]
                    return {"success": True, "message": f"Connected to Ollama. Available models: {len(model_names)}", "models": model_names}
                else:
                    return {"success": False, "message": f"Ollama not responding (Status {response.status_code})"}
            
            elif self.provider == "gemini":
                # Test with a simple prompt
                model = self.genai.GenerativeModel(self.model)
                response = model.generate_content("Test")
                return {"success": True, "message": f"Connected to Gemini ({self.model})"}
                
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}
    
    def _call_ai(self, prompt: str, max_tokens: int = 500) -> str:
        """Call the configured AI provider"""
        try:
            if self.provider == "ollama":
                return self._call_ollama(prompt, max_tokens)
            elif self.provider == "gemini":
                return self._call_gemini(prompt, max_tokens)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
        except Exception as e:
            raise Exception(f"AI call failed: {str(e)}")
    
    def _call_ollama(self, prompt: str, max_tokens: int = 500) -> str:
        """Call local Ollama API"""
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            error_msg = error_data.get('error', response.text)
            if response.status_code == 404:
                raise Exception(f"Ollama model '{self.model}' not found. Please run 'ollama pull {self.model}' or check your model name.")
            else:
                raise Exception(f"Ollama error ({response.status_code}): {error_msg}")
        
        result = response.json()
        return result.get('response', '').strip()
    
    def _call_gemini(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Google Gemini API"""
        model = self.genai.GenerativeModel(
            self.model,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.7
            }
        )
        
        response = model.generate_content(prompt)
        return response.text.strip()
    
    def generate_definition(self, word: str, pos_tag: str, context_examples: Optional[List[Dict]] = None) -> str:
        """
        Generate a dictionary definition
        
        Args:
            word: The word to define
            pos_tag: Part of speech tag
            context_examples: Optional list of KWIC examples for context
            
        Returns:
            Generated definition string
        """
        # Build context from examples
        context = ""
        if context_examples:
            context = "\n\nCorpus Examples:\n"
            for i, ex in enumerate(context_examples[:5], 1):
                left = ex.get('left', '')
                right = ex.get('right', '')
                context += f"{i}. {left} **{word}** {right}\n"
        
        prompt = f"""You are a lexicographer creating dictionary definitions. Do not use conversational filler or greetings.

Word: {word}
POS: {pos_tag}{context}

Provide a concise, clear definition suitable for a learner's dictionary.
Format: [[DEFINITION]] Your definition here.

Definition:"""
        
        response = self._call_ai(prompt, max_tokens=200)
    def _extract_tag(self, text: str, tag_name: str) -> str:
        """Robustly extract content between [[TAG]] and the next tag or end of string."""
        start_tag = f"[[{tag_name}]]"
        if start_tag not in text:
            return ""
        content = text.split(start_tag, 1)[1]
        # End is either the next tag or end of string
        for next_tag in ["[[DEFINITION]]", "[[EXAMPLES]]", "[[COLLOCATES]]", "[[USAGE]]", "[[PRONUNCIATION]]", "[[NGRAMS]]", "[[KWIC]]", "[[COLLO_EX]]"]:
            if next_tag in content:
                content = content.split(next_tag, 1)[0]
        return content.strip()

    def generate_definition(self, word: str, pos_tag: str, context_examples: Optional[List[Dict]] = None) -> str:
        """
        Generate a dictionary definition
        
        Args:
            word: The word to define
            pos_tag: Part of speech tag
            context_examples: Optional list of KWIC examples for context
            
        Returns:
            Generated definition string
        """
        # Build context from examples
        context = ""
        if context_examples:
            context = "\n\nCorpus Examples:\n"
            for i, ex in enumerate(context_examples[:5], 1):
                left = ex.get('left', '')
                right = ex.get('right', '')
                context += f"{i}. {left} **{word}** {right}\n"
        
        prompt = f"""You are a lexicographer creating dictionary definitions. Do not use conversational filler or greetings.

Word: {word}
POS: {pos_tag}{context}

Provide a concise, clear definition suitable for a learner's dictionary.
Format: [[DEFINITION]] Your definition here.

Definition:"""
        
        response = self._call_ai(prompt, max_tokens=200)
        return self._extract_tag(response, "DEFINITION") or response.strip()
    
    def generate_examples(self, word: str, pos_tag: str, definition: Optional[str] = None, count: int = 3) -> List[Dict[str, str]]:
        """
        Generate example sentences
        
        Args:
            word: The word to exemplify
            pos_tag: Part of speech tag
            definition: Optional definition for context
            count: Number of examples to generate
            
        Returns:
            List of dicts with 'left', 'node', 'right' keys
        """
        def_context = f"\nDefinition: {definition}" if definition else ""
        
        prompt = f"""Generate {count} natural example sentences for:

Word: {word}
POS: {pos_tag}{def_context}

Format: [[EXAMPLES]]
left context | {word} | right context
left context | {word} | right context

Keep sentences simple and clear. No conversational filler.
Examples:"""
        
        response = self._call_ai(prompt, max_tokens=400)
        content = self._extract_tag(response, "EXAMPLES") or response.strip()
        
        # Parse response
        examples = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if '|' in line:
                # Remove numbering if present
                line = line.lstrip('0123456789.-) ')
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    examples.append({
                        'left': parts[0],
                        'node': parts[1],
                        'right': parts[2]
                    })
        
        return examples[:count]
    
    def suggest_collocates(self, word: str, pos_tag: str, count: int = 10) -> List[str]:
        """
        Suggest common collocates
        
        Args:
            word: The word
            pos_tag: Part of speech tag
            count: Number of collocates to suggest
            
        Returns:
            List of collocate words
        """
        prompt = f"""List {count} common words that frequently appear with "{word}" ({pos_tag}).

Provide only the words as a comma-separated list. No explanations.
Format: [[COLLOCATES]] word1, word2, word3

Collocates:"""
        
        response = self._call_ai(prompt, max_tokens=150)
        content = self._extract_tag(response, "COLLOCATES") or response.strip()
        
        # Parse comma-separated list
        collocates = [c.strip() for c in content.split(',')]
        return [c for c in collocates if c][:count]
    
    def generate_pronunciation(self, word: str, pos_tag: str) -> str:
        """Generate IPA pronunciation for a word."""
        prompt = f"""Provide the standard International Phonetic Alphabet (IPA) pronunciation for the word.
Do not include any conversational filler. Only provide the IPA symbols enclosed in slashes.

Word: {word}
POS: {pos_tag}

Format: [[PRONUNCIATION]] /ɪɡˈzæmpəl/

Pronunciation:"""
        response = self._call_ai(prompt, max_tokens=50)
        return self._extract_tag(response, "PRONUNCIATION") or response.strip()

    def generate_ngrams(self, word: str, pos_tag: str, n_type: str = "Bigrams") -> str:
        """Generate common n-grams formatted as 'item | frequency'"""
        count = 2 if n_type.lower() == "bigrams" else 3
        prompt = f"""List 5 common {n_type.lower()} (combinations of {count} words) containing the target word.
Do not include any conversational filler.
Provide them in this exact format:
[[NGRAMS]]
word1 word2 | 10
word3 word4 | 8

Word: {word}
POS: {pos_tag}

{n_type}:"""
        response = self._call_ai(prompt, max_tokens=150)
        return self._extract_tag(response, "NGRAMS") or response.strip()

    def generate_formatted_collocates(self, word: str, pos_tag: str) -> str:
        """Generate collocates formatted as 'word | score'"""
        prompt = f"""List 5 common words that frequently appear with "{word}".
Do not include any conversational filler.
Provide them in this exact format, with a made-up collocate score:
[[COLLOCATES]]
collocate1 | 5.4
collocate2 | 4.2

Word: {word}
POS: {pos_tag}

Collocates:"""
        response = self._call_ai(prompt, max_tokens=150)
        return self._extract_tag(response, "COLLOCATES") or response.strip()

    def generate_kwic_examples(self, word: str, pos_tag: str) -> str:
        """Generate KWIC examples formatted as 'left | node | right'"""
        prompt = f"""Generate 3 natural example sentences for the word, formatted as Keyword in Context (KWIC).
Do not include any conversational filler.
Provide them in this exact format:
[[KWIC]]
this is the left context | node | and this is the right context

Word: {word}
POS: {pos_tag}

Examples:"""
        response = self._call_ai(prompt, max_tokens=300)
        return self._extract_tag(response, "KWIC") or response.strip()

    def generate_collocate_examples(self, word: str, pos_tag: str) -> str:
        """Generate collocate examples formatted as 'collocate | left | node | right'"""
        prompt = f"""Generate 3 natural example sentences that show the target word used with a common collocate.
Do not include any conversational filler.
Provide them in this exact format:
[[COLLO_EX]]
collocate_word | this is the left | node | and right context

Word: {word}
POS: {pos_tag}

Examples:"""
        response = self._call_ai(prompt, max_tokens=300)
        return self._extract_tag(response, "COLLO_EX") or response.strip()

    def analyze_word(self, word: str, pos_tag: str, corpus_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate comprehensive word analysis
        
        Args:
            word: The word to analyze
            pos_tag: Part of speech tag
            corpus_data: Optional dict with frequency, examples, collocates, ngrams
            
        Returns:
            Dict with definition, examples, collocates, usage_notes
        """
        # Build corpus context
        context = ""
        if corpus_data:
            freq = corpus_data.get('frequency', 0)
            context += f"\nFrequency in corpus: {freq}"
            
            if corpus_data.get('collocates'):
                top_colls = [c.get('collocate', '') for c in corpus_data['collocates'][:5]]
                context += f"\nTop collocates: {', '.join(top_colls)}"
            
            if corpus_data.get('examples'):
                context += "\n\nCorpus Examples:"
                for i, ex in enumerate(corpus_data['examples'][:3], 1):
                    left = ex.get('left', '')
                    right = ex.get('right', '')
                    context += f"\n{i}. {left} **{word}** {right}"
        
        prompt = f"""Analyze this word based on corpus data. DO NOT include any conversational filler (like "Absolutely!", "Sure!", "Okay"). Use the exact format below.

Word: {word}
POS: {pos_tag}{context}

Format:
[[DEFINITION]] One clear sentence definition.
[[EXAMPLES]] 
left | {word} | right
left | {word} | right
left | {word} | right
[[COLLOCATES]] word1, word2, word3
[[USAGE]] Brief notes.

Response:"""
        
        response = self._call_ai(prompt, max_tokens=800)
        
        # Parse response (robust tag-based parsing)
        result = {
            'definition': '',
            'examples': '',
            'collocates': '',
            'usage_notes': '',
            'raw_response': response
        }
        
        result['definition'] = self._extract_tag(response, "DEFINITION")
        result['examples'] = self._extract_tag(response, "EXAMPLES")
        result['collocates'] = self._extract_tag(response, "COLLOCATES")
        result['usage_notes'] = self._extract_tag(response, "USAGE")

        # Fallback to heuristic parsing if tags were ignored by a small model
        if not any([result['definition'], result['examples'], result['collocates']]):
            lines = response.strip().split('\n')
            current_section = None
            for line_clean in lines:
                line_clean = line_clean.strip()
                if not line_clean: continue
                line_lower = line_clean.lower()
                
                # Filter out obvious conversational filler at the very start
                if not current_section and any(filler in line_lower[:15] for filler in ["sure", "absolutely", "certainly", "okay", "here is"]):
                    continue

                if any(h in line_lower for h in ['definition', 'meaning']) and ':' in line_clean:
                    current_section = 'definition'
                    result['definition'] = line_clean.split(':', 1)[1].strip()
                elif any(h in line_lower for h in ['example', 'sentence']) and ':' in line_clean:
                    current_section = 'examples'
                elif any(h in line_lower for h in ['collocate', 'partner']) and ':' in line_clean:
                    current_section = 'collocates'
                    result['collocates'] = line_clean.split(':', 1)[1].strip()
                elif any(h in line_lower for h in ['usage note', 'notes']) and ':' in line_clean:
                    current_section = 'usage_notes'
                    result['usage_notes'] = line_clean.split(':', 1)[1].strip()
                elif current_section == 'examples' and ('|' in line_clean or len(line_clean) > 10):
                    if result['examples']: result['examples'] += '\n'
                    result['examples'] += line_clean.lstrip('0123456789.-) ')
                elif current_section == 'definition' and not result['definition']:
                    result['definition'] = line_clean
        
        return result


def get_ai_helper(session_state: Dict) -> Optional[AIHelper]:
    """
    Create AIHelper instance from Streamlit session state
    
    Args:
        session_state: Streamlit session state dict
        
    Returns:
        AIHelper instance or None if AI is disabled
    """
    provider = session_state.get('ai_provider', 'None')
    
    if provider == 'None':
        return None
    elif provider == 'Local (Ollama)':
        model = session_state.get('ollama_model', 'llama3.2')
        if model == 'custom':
            model = session_state.get('ollama_custom_model', 'llama3.2')
        return AIHelper(provider="ollama", model=model)
    elif provider == 'Google Gemini':
        api_key = session_state.get('gemini_api_key')
        if not api_key:
            return None
        model = session_state.get('gemini_model', 'gemini-2.0-flash-exp')
        return AIHelper(provider="gemini", api_key=api_key, model=model)
    
    return None
