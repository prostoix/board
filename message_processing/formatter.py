import re
from typing import List
from .math_processor import MathProcessor

class MessageFormatter:
    """Форматировщик сообщений"""
    
    def __init__(self):
        self.math_processor = MathProcessor()
    
    def format_message(self, text: str) -> str:
        """Отформатировать сообщение"""
        if not text:
            return text
        
        # Обработка математических выражений
        text = self.math_processor.process_math_expressions(text)
        
        result = []
        lines = text.split('\n')
        in_list = False
        in_code = False
        in_term = False
        list_type = 'ul'
        
        for line in lines:
            line = line.rstrip()
            
            is_header = line.startswith('# ') or line.startswith('## ') or line.startswith('### ')
            is_list_item = re.match(r'^[\-\*\•]\s+', line) or re.match(r'^\d+\.\s+', line)
            is_code_block = line.strip().startswith('```')
            is_term_line = line.strip().startswith('$ ') or line.strip().startswith('> ')
            is_empty = line.strip() == ''
            
            if is_code_block:
                in_code = not in_code
                result.append(f'<div class="code-block">' if in_code else '</div>')
                continue
            
            if in_code:
                safe_line = self.math_processor.escape_html(line)
                result.append(f'<span class="code-line">{safe_line}</span><br>')
                continue
            
            if is_term_line and not in_term:
                in_term = True
                result.append('<div class="terminal">')
            elif not is_term_line and in_term:
                in_term = False
                result.append('</div>')
            
            if is_list_item and not in_list:
                in_list = True
                list_type = 'ol' if re.match(r'^\d+\.\s+', line) else 'ul'
                result.append(f'<{list_type} class="message-list">')
            elif not is_list_item and in_list:
                in_list = False
                result.append('</ul>' if list_type == 'ul' else '</ol>')
            
            safe_line = self.math_processor.escape_html(line)
            
            if is_header:
                level = len(line.split()[0])
                content = line[level:].strip()
                result.append(f'<h{level} class="message-header">{content}</h{level}>')
            
            elif is_list_item:
                content = re.sub(r'^[\-\*\•]\s+', '', line)
                content = re.sub(r'^\d+\.\s+', '', content)
                result.append(f'<li class="message-list-item">{self._format_inline(content)}</li>')
            
            elif is_term_line:
                content = line[2:].strip() if line.startswith('$ ') else line[2:].strip()
                result.append(f'<div class="terminal-line"><span class="prompt">$</span> {self._format_inline(content)}</div>')
            
            elif is_empty:
                result.append('<div class="empty-line"><br></div>')
            
            else:
                if in_term:
                    result.append(f'<div class="terminal-output">{self._format_inline(line)}</div>')
                else:
                    result.append(f'<div class="message-line">{self._format_inline(line)}</div>')
        
        # Закрываем незакрытые блоки
        if in_list:
            result.append('</ul>' if list_type == 'ul' else '</ol>')
        if in_term:
            result.append('</div>')
        
        return '\n'.join(result)
    
    def _format_inline(self, text: str) -> str:
        """Форматирование inline элементов"""
        # Жирный текст
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        # Курсив
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        # Код inline
        text = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', text)
        # Ссылки
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="message-link">\1</a>', text)
        
        return text

# Синглтон форматировщика
message_formatter = MessageFormatter()