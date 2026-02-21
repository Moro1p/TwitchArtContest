import qrcode
from PIL import Image, ImageDraw

def Create_QRCode(author_id, link):
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    ) 

    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img.save(f"./QRCodes/{author_id + 1}.png")
    return f"./QRCodes/{author_id + 1}.png"

