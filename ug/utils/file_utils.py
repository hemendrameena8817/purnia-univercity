import os
import base64
import io
import logging

def image_to_base64(path):
    """
    Convert an image file to a base64 string.
    
    Args:
        path: Absolute file path to the image
        
    Returns:
        str: Base64 encoded string of the image, or empty string if file not found
    """
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    return ""

def generate_qrcode_base64(text):
    """
    Generate a QR code from text and return it as a base64 string.
    """
    import qrcode
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        logging.getLogger(__name__).error(f"QR Code generation failed: {str(e)}")
        return ""
