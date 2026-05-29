import json
import os
import re

class RussianTextHumanizer:
    """
    Humanizes Russian text to make it more natural, emotional, and selling.
    Inspired by AI-Text-Humanizer-App but adapted for Russian astrology content.
    """
    
    def __init__(self):
        # Emotional amplifiers (like "Насти Войны" style)
        self.emotional_starters = [
            "Внимание!", "Срочно!", "Осторожно!", "Тайна!", 
            "Шок!", "Предупреждение!", "Слушай внимательно!",
            "Запомни!", "Не говори, что я не предупреждал!"
        ]
        
        # Trigger words for astrology content
        self.triggers = [
            "судьба", "звезды", "планеты", "космос", "энергия",
            "тайна", "опасность", "шанс", "успех", "провал",
            "срочно", "секрет", "блокировка", "открытие"
        ]
        
        # Sentence connectors (more natural than academic)
        self.connectors = [
            "Причем", "Кстати", "Более того", "Кроме того",
            "Но самое страшное", "А вот и главное", "И это еще не всё",
            "Представь", "Знаешь, что это значит?"
        ]
        
        # Ending hooks (CTA - Call to Action)
        self.endings = [
            "Узнай подробнее по ссылке!",
            "Жми на ссылку прямо сейчас!",
            "Переходи в бота, пока не заблокировали!",
            "Твоя судьба в твоих руках. Ссылка в описании!",
            "97% уже узнали. Ты следующий!"
        ]
    
    def humanize_text(self, text: str, style: str = "selling") -> str:
        """
        Make text more human-like, emotional, and selling.
        style: "selling" (for TikTok/YouTube) or "calm" (for narration)
        """
        if not text:
            return text
        
        result = text
        
        # 1. Add emotional starter (30% chance)
        import random
        if random.random() < 0.3 and not any(es in result[:30] for es in self.emotional_starters):
            starter = random.choice(self.emotional_starters)
            if not result.startswith(starter):
                result = f"{starter} {result[0].lower() + result[1:]}"
        
        # 2. Add trigger words (if missing)
        has_trigger = any(trigger in result.lower() for trigger in self.triggers)
        if not has_trigger and random.random() < 0.4:
            trigger = random.choice(self.triggers)
            # Insert before last sentence
            sentences = result.split('. ')
            if len(sentences) > 1:
                sentences[-1] = f"Это касается твоей {trigger}. {sentences[-1]}"
                result = '. '.join(sentences)
        
        # 3. Add natural connectors between sentences
        sentences = result.split('. ')
        if len(sentences) > 1 and random.random() < 0.5:
            idx = random.randint(1, len(sentences) - 1)
            connector = random.choice(self.connectors)
            sentences[idx] = f"{connector.lower()}, {sentences[idx][0].lower() + sentences[idx][1:]}"
            result = '. '.join(sentences)
        
        # 4. Fix common AI patterns (make more conversational)
        result = self._fix_ai_patterns(result)
        
        # 5. Add ending hook (for selling style)
        if style == "selling" and random.random() < 0.7:
            if not any(ending in result for ending in ["t.me", "ссылк", "переход", "узнай"]):
                ending = random.choice(self.endings)
                result = f"{result} {ending}"
        
        return result
    
    def _fix_ai_patterns(self, text: str) -> str:
        """Fix common AI-generated text patterns to sound more human"""
        result = text
        
        # Replace formal "необходимо" with more natural "нужно"
        result = re.sub(r'\необходимо\b', 'нужно', result, flags=re.IGNORECASE)
        
        # Replace "следует" with "стоит"
        result = re.sub(r'\следует\b', 'стоит', result, flags=re.IGNORECASE)
        
        # Add contractions (more natural in Russian)
        result = re.sub(r'\не (\w+)', r'не\1', result)  # Ensure spacing
        result = re.sub(r'\что (\w+)', r'что\1', result)
        
        # Replace "в данный момент" with "сейчас"
        result = re.sub(r'в данный момент', 'сейчас', result, flags=re.IGNORECASE)
        
        # Replace "осуществлять" with "делать"
        result = re.sub(r'\осуществлять\b', 'делать', result, flags=re.IGNORECASE)
        
        return result
    
    def add_stress_for_tts(self, text: str) -> str:
        """Add '+' before stressed vowels for Svetlana TTS"""
        stress_dict = {
            "началось": "начА+лось",
            "сегодня": "сегО+дня",
            "остановитесь": "остановИ+тесь",
            "внимание": "внимА+ние",
            "предупреждают": "предупреждА+ют",
            "возможность": "возмО+жность",
            "прислушайтесь": "прислушА+йтесь",
            "мгновение": "мгновЕ+ние",
            "опасность": "опА+сность",
            "успех": "успЕ+х",
            "внимание": "внимА+ние",
            "судьба": "судьбА+",
            "звезды": "звЁ+зды",
            "энергия": "энЕ+ргия",
            "тайна": "тА+йна",
            "срочно": "срО+чно"
        }
        
        result = text
        for word, stressed in stress_dict.items():
            result = re.sub(r'\b' + word + r'\b', stressed, result, flags=re.IGNORECASE)
        
        return result


def generate_humanized_script(sign: str, total_duration: int = 15, clip_duration: int = 3):
    """
    Generate script with humanized, emotional, selling text.
    Uses RussianTextHumanizer to make text more natural and viral.
    """
    from auto_script_generator import SIGN_DATA, generate_script_for_sign
    
    # Get base script from original generator
    base_script = generate_script_for_sign(sign, total_duration, clip_duration)
    
    if not base_script:
        return None
    
    humanizer = RussianTextHumanizer()
    
    # Humanize each clip's text
    for clip in base_script:
        original_text = clip["text"]
        
        # Humanize for selling style
        humanized = humanizer.humanize_text(original_text, style="selling")
        
        # Add stress marks for TTS
        humanized_stressed = humanizer.add_stress_for_tts(humanized)
        
        clip["text_original"] = original_text
        clip["text_humanized"] = humanized
        clip["text_stressed"] = humanized_stressed
    
    return base_script


def save_humanized_script(sign: str, script: list, total_duration: int, clip_duration: int):
    """Save humanized script in all formats"""
    os.makedirs("scripts", exist_ok=True)
    
    # 1. JSON with humanized text
    json_path = f"scripts/{sign}_{total_duration}s_humanized.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"[OK] Humanized JSON: {json_path}")
    
    # 2. TTS text (ready for Svetlana)
    tts_path = f"scripts/{sign}_{total_duration}s_tts_humanized.txt"
    with open(tts_path, "w", encoding="utf-8") as f:
        f.write(f"=== ГУМАНИЗИРОВАННЫЙ ТЕКСТ ДЛЯ ОЗВУЧКИ ({sign.upper()}, {total_duration}с) ===\n\n")
        f.write("Стиль: 'Насти Войны' (эмоциональный, продающий)\n\n")
        for clip in script:
            f.write(f"[{clip['time']}]\n")
            f.write(f"{clip['text_stressed']}\n\n")
    print(f"[OK] Humanized TTS text: {tts_path}")
    
    # 3. Comparison file (original vs humanized)
    compare_path = f"scripts/{sign}_{total_duration}s_comparison.txt"
    with open(compare_path, "w", encoding="utf-8") as f:
        f.write(f"=== СРАВНЕНИЕ: ОРИГИНАЛ vs ГУМАНИЗИРОВАННЫЙ ({sign.upper()}) ===\n\n")
        for clip in script:
            f.write(f"[{clip['time']}]\n")
            f.write(f"ОРИГИНАЛ: {clip['text_original']}\n")
            f.write(f"ГУМАНИЗИРОВАННЫЙ: {clip['text_humanized']}\n")
            f.write(f"ДЛЯ ОЗВУЧКИ: {clip['text_stressed']}\n\n")
    print(f"[OK] Comparison file: {compare_path}")
    
    return json_path, tts_path, compare_path


def generate_full_humanized_package(sign: str):
    """Generate complete humanized script package"""
    print("="*60)
    print(f"ГУМАНИЗАЦИЯ ТЕКСТА (стиль 'Насти Войны')")
    print(f"Знак: {sign.upper()}")
    print("="*60)
    
    # Generate humanized script
    script = generate_humanized_script(sign, total_duration=15, clip_duration=3)
    
    if script:
        paths = save_humanized_script(sign, script, 15, 3)
        
        print("\n" + "="*60)
        print(f"ГОТОВО! ГУМАНИЗИРОВАННЫЙ ПАКЕТ ДЛЯ {sign.upper()}")
        print("="*60)
        print(f"1. Структура (JSON): {paths[0]}")
        print(f"2. Текст для Светланы: {paths[1]}")
        print(f"3. Сравнение текстов: {paths[2]}")
        print("\nПРЕИМУЩЕСТВА:")
        print("- Более эмоционально и натурально")
        print("- Продающие триггеры (ужас, любопытство)")
        print("- Готово для озвучки Светланой (ударения '+'")
        print("- Стиль 'Насти Войны' (виральность)")
        print("="*60)
        
        return paths
    return None


if __name__ == "__main__":
    import sys
    
    sign = sys.argv[1] if len(sys.argv) > 1 else "aries"
    
    print("RUSSIAN TEXT-HUMANIZER")
    print("Makes text emotional and selling")
    print("Style: 'Nastya's Wars' (astrological esoteric)")
    print("="*60 + "\n")
    
    generate_full_humanized_package(sign)