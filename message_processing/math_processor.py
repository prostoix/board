import re
import html

class MathProcessor:
    """Обработчик математических выражений"""
    
    @staticmethod
    def process_math_expressions(text: str) -> str:
        """Обработать математические выражения в тексте"""
        if not text:
            return text
        
        # Обработка дробей: \frac{a}{b}
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', 
                     r'<span class="math-frac"><span class="numerator">\1</span><span class="denominator">\2</span></span>', 
                     text)
        
        # Обработка скобок: \left( content \right)
        text = re.sub(r'\\left\(([^)]+)\\right\)', 
                     r'<span class="math-brackets">(\1)</span>', 
                     text)
        
        # Обработка инлайн математики: \( content \)
        text = re.sub(r'\\\(([^)]+)\\\)', 
                     r'<span class="math-inline">\1</span>', 
                     text)
        
        # Обработка корней: \sqrt{content}
        text = re.sub(r'\\sqrt\{([^}]+)\}', 
                     r'√<span class="math-root">{\1}</span>', 
                     text)
        
        # Обработка степеней: a^{b}
        text = re.sub(r'([a-zA-Z0-9])\^\{([^}]+)\}', 
                     r'\1<sup>\2</sup>', 
                     text)
        
        # Обработка индексов: a_{b}
        text = re.sub(r'([a-zA-Z0-9])\_\{([^}]+)\}', 
                     r'\1<sub>\2</sub>', 
                     text)
        
        return text
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Экранировать HTML-символы"""
        return html.escape(text)