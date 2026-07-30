import qrcode
import io
import random
import utils.bot_config as cfg


async def make_upi_qr(amount: float, order_ref: str):
    """Generate UPI QR — reads UPI ID from DB settings dynamically."""
    upi_id   = await cfg.upi_id()
    upi_name = await cfg.upi_name()

    paise = random.randint(1, 9)
    exact = round(float(amount) + paise / 100, 2)

    upi_string = (
        f"upi://pay?"
        f"pa={upi_id}&"
        f"pn={upi_name.replace(' ', '%20')}&"
        f"am={exact:.2f}&"
        f"cu=INR&"
        f"tn=Ref{order_ref}"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#111111", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read(), exact, upi_id
