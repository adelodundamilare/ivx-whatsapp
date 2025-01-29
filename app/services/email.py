import os
import smtplib
import ssl
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template, TemplateNotFound

from app.core.config import settings

template_folder = "app/templates"
templates = Environment(loader=FileSystemLoader(template_folder))

class EmailService:
    _template_env = None

    @classmethod
    def _get_template_env(cls):
        """
        Initialize Jinja2 template environment if not already initialized
        """
        if cls._template_env is None:
            # Dynamically find the templates directory
            template_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                'templates'
            )

            cls._template_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html'])
            )
        return cls._template_env

    @classmethod
    def render_template(cls, template_name: str, context: dict) -> str:
        """
        Render an email template

        :param template_name: Name of the template file
        :param context: Dictionary of template variables
        :return: Rendered HTML template
        """
        try:
            # Add default context variables
            default_context = {
                'company_name': 'Your Company',
                'current_year': datetime.now().year,
                **context
            }

            template_env = cls._get_template_env()
            template = template_env.get_template(template_name)
            return template.render(**default_context)
        except Exception as e:
            logging.error(f"Error rendering email template {template_name}: {e}")
            raise


    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        template_name: str,
        template_context: dict,
    ):
        """
        Send an email using a specified template.

        :param to_email: Recipient email address
        :param subject: Email subject
        :param template_name: Name of the template file
        :param template_context: Dictionary of template variables
        """
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.EMAILS_FROM_NAME
            msg['To'] = to_email

            # Render HTML content
            try:
                template = templates.get_template(template_name)
                html_content = template.render(template_context)
            except TemplateNotFound:
                logging.error(f"Template '{template_name}' not found.")
                raise ValueError(f"Template '{template_name}' does not exist.")

            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))

            # Create secure SSL context
            context = ssl.create_default_context()

            # Send email
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(msg['From'], [to_email], msg.as_string())

            logging.info(f"Email sent successfully to {to_email}")

        except smtplib.SMTPException as smtp_error:
            logging.error(f"SMTP error: {smtp_error}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise