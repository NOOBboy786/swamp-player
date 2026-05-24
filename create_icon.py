import os
from PIL import Image, ImageDraw, ImageFont

def create_icon():
    os.makedirs('app/assets', exist_ok=True)
    img = Image.new('RGB', (256, 256), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw retro green borders and C
    draw.rectangle([10, 10, 246, 246], outline=(0, 255, 0), width=10)
    draw.text((80, 50), "C", fill=(0, 255, 0), font=ImageFont.load_default().font_variant(size=120))
    img.save('app/assets/icon.png')
    img.save('app/assets/icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Icon created!")

if __name__ == '__main__':
    create_icon()
