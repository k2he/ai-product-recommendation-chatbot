"""Email service for sending product information."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings
from app.models.product import Product

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Email service for sending product information to users."""

    @staticmethod
    def _create_product_email_html(
        user_name: str, product: Product
    ) -> str:
        """Create HTML email content for product information."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .content {{
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .product-card {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .product-image {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 4px;
                }}
                .price {{
                    font-size: 24px;
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .sale-price {{
                    font-size: 24px;
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .specs {{
                    margin: 15px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Product Information</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Here's the product information you requested:</p>
                    
                    <div class="product-card">
                        {f'<img src="{product.highResImage}" alt="{product.name}" class="product-image">' if product.highResImage else ''}
                        
                        <h2>{product.name}</h2>
                        <p><strong>Category:</strong> {product.categoryName}</p>
                        
                        <p style="margin: 10px 0; font-family: Arial, sans-serif;">
                            <span style="color: #0000FF; font-weight: bold; font-size: 1.2em;">${product.salePrice:.2f}</span> 
                            <span style="color: #888; text-decoration: line-through; margin-left: 10px;">${product.regularPrice:.2f}</span>
                        </p>
                        
                        {f'''<p style="color: #28a745; font-weight: bold; margin: 5px 0;">
                            Save ${product.regularPrice - product.salePrice:.2f} CAD
                        </p>''' if product.isOnSale else ''}
                    
                        <h3>Description</h3>
                        <p>{product.shortDescription}</p>
                    </div>

                    <p>If you have any questions or would like to make a purchase, please contact us.</p>
                </div>
                <div class="footer">
                    <p>This email was sent from the Product Recommendation Chatbot.</p>
                    <p>&copy; 2024 Product Recommendation Service. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    async def send_product_email(
        recipient_email: str, recipient_name: str, product: Product
    ) -> bool:
        """Send product information via email."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Product Information: {product.name}"
            msg["From"] = settings.smtp_from_email
            msg["To"] = recipient_email

            # Create HTML content
            html_content = EmailService._create_product_email_html(recipient_name, product)

            # Create plain text fallback
            text_content = f"""
            Hello {recipient_name},

            Here's the product information you requested:

            Product: {product.name}
            Category: {product.categoryName}
            Regular Price: ${product.regularPrice:.2f}
            Sale Price: ${product.salePrice:.2f}
            Savings: ${product.regularPrice - product.salePrice:.2f} ({'On Sale!' if product.isOnSale else 'No Sale'})
            
            Description: {product.shortDescription}

            If you have any questions or would like to make a purchase, please contact us.

            Best regards,
            Product Recommendation Chatbot
            """

            # Attach parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed. Check credentials: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False


# Global email service instance
email_service = EmailService()
