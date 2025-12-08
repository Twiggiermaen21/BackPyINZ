# calendar_export/utils.py

import re

def hex_to_rgb(hex_color):
    """Konwertuje kolor w formacie HEX na krotkę RGB."""
    # Usuń znak '#' jeśli istnieje
    hex_color = hex_color.lstrip("#")
    
    # Rozdziel na R, G, B i konwertuj na int
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    else:
        # Możesz dodać obsługę skróconego formatu #RGB na #RRGGBB, ale to jest uproszczona wersja
        raise ValueError("Nieprawidłowy format koloru HEX")

def get_gradient_css(start_color, end_color, direction):
    """Generuje string CSS dla gradientu."""
    return f"linear-gradient({direction or 'to bottom'}, {start_color}, {end_color})"