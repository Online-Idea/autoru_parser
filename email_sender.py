import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email import encoders


def send_email_to_client(client_email: str, file_path: str) -> None:
    """
    Отправляет письмо с файлом
    @param client_email: почты получателей, разделены запятой
    @param file_path: путь к файлу
    """
    # Инфо письма
    file_name_ext = os.path.basename(file_path)
    file_name = os.path.splitext(file_name_ext)[0]
    sender = os.environ['email_login']
    password = os.environ['email_password']
    recipients = [client.strip() for client in client_email.split(',')]
    # recipients.append('ruslansponline@gmail.com')  # Почта Руслана
    subject = file_name
    body = 'Добрый день,\n\n' \
           'В приложении сравнительный анализ конкурентов\n\n' \
           'Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.\n' \
           'Чтобы отписаться от рассылки напишите нам на: info@ra-online.ru'

    # Сообщение
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = client_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Прикрепляю файл
    with open(file_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype='xlsx')
        attachment.add_header('Content-Disposition', 'attachment', filename=file_name_ext)
        msg.attach(attachment)

    # Отправляю письмо
    with smtplib.SMTP_SSL('smtp.yandex.ru', 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, recipients, msg.as_string())
