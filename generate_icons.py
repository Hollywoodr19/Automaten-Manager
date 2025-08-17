#!/usr/bin/env python3
"""
Icon Generator für PWA
Erstellt alle benötigten Icon-Größen aus einem Basis-Icon
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon_base(size=512):
    """Erstellt ein Basis-Icon für den Automaten Manager"""
    # Neues Bild mit Gradient-Hintergrund
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Gradient Background (vereinfacht - einfarbig)
    bg_color = (102, 126, 234, 255)  # #667eea
    draw.rounded_rectangle(
        [0, 0, size, size],
        radius=size//8,
        fill=bg_color
    )
    
    # Icon Symbol (Automat stilisiert)
    icon_color = (255, 255, 255, 255)
    margin = size // 8
    
    # Hauptkörper
    body_rect = [margin, margin*2, size-margin, size-margin*2]
    draw.rounded_rectangle(body_rect, radius=size//16, fill=icon_color)
    
    # Display
    display_rect = [
        margin + size//8,
        margin*2 + size//8,
        size - margin - size//8,
        margin*2 + size//3
    ]
    draw.rectangle(display_rect, fill=bg_color)
    
    # Buttons (3 Reihen)
    button_size = size // 12
    button_margin = size // 16
    start_y = display_rect[3] + button_margin
    
    for row in range(3):
        for col in range(3):
            x = margin + size//8 + (button_size + button_margin) * col
            y = start_y + (button_size + button_margin) * row
            draw.rounded_rectangle(
                [x, y, x + button_size, y + button_size],
                radius=button_size//4,
                fill=bg_color
            )
    
    # Ausgabeschacht
    slot_rect = [
        margin + size//8,
        size - margin*2 + size//16,
        size - margin - size//8,
        size - margin - size//8
    ]
    draw.rectangle(slot_rect, fill=bg_color)
    
    # Text "AM" für Automaten Manager
    try:
        # Versuche Font zu laden, falls nicht verfügbar, nutze Default
        font_size = size // 6
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text = "AM"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (size - text_width) // 2
        text_y = display_rect[1] + (display_rect[3] - display_rect[1] - text_height) // 2
        
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    except:
        pass
    
    return img

def generate_icons():
    """Generiert alle benötigten Icon-Größen"""
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Erstelle icons Verzeichnis
    icon_dir = 'app/static/icons'
    os.makedirs(icon_dir, exist_ok=True)
    
    # Basis-Icon erstellen
    base_icon = create_icon_base(512)
    
    # Alle Größen generieren
    for size in sizes:
        resized = base_icon.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(f'{icon_dir}/icon-{size}x{size}.png', 'PNG')
        print(f'✓ Created icon-{size}x{size}.png')
    
    # Spezielle Icons
    # Apple Touch Icon
    apple_icon = base_icon.resize((180, 180), Image.Resampling.LANCZOS)
    apple_icon.save(f'{icon_dir}/apple-touch-icon.png', 'PNG')
    print('✓ Created apple-touch-icon.png')
    
    # Favicon
    favicon_sizes = [(16, 16), (32, 32), (48, 48)]
    favicon_images = []
    for size in favicon_sizes:
        favicon_images.append(base_icon.resize(size, Image.Resampling.LANCZOS))
    
    favicon_images[0].save(
        f'{icon_dir}/favicon.ico',
        format='ICO',
        sizes=favicon_sizes,
        save_all=True,
        append_images=favicon_images[1:]
    )
    print('✓ Created favicon.ico')
    
    # Maskable Icon (mit extra Padding für Android)
    maskable = Image.new('RGBA', (512, 512), (102, 126, 234, 255))
    icon_small = base_icon.resize((410, 410), Image.Resampling.LANCZOS)
    maskable.paste(icon_small, (51, 51), icon_small)
    maskable.save(f'{icon_dir}/maskable-icon-512x512.png', 'PNG')
    print('✓ Created maskable-icon-512x512.png')
    
    print(f'\n✅ All icons generated successfully in {icon_dir}/')

if __name__ == '__main__':
    generate_icons()
