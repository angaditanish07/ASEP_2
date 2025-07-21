import smtplib
from email.mime.text import MIMEText

def send_test_email(smtp_server, smtp_port, username, password, sender, recipient):
    msg = MIMEText("This is a test email from your Flask app's SMTP configuration.")
    msg['Subject'] = 'Test Email'
    msg['From'] = sender
    msg['To'] = recipient

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()
        print("Test email sent successfully.")
    except Exception as e:
        print(f"Failed to send test email: {e}")

if __name__ == "__main__":
    # Replace these values with your actual SMTP settings and email addresses
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    USERNAME = "tanishangadi07@gmail.com"
    PASSWORD = "YOUR_APP_PASSWORD_HERE"
    SENDER = "tanishangadi07@gmail.com"
    RECIPIENT = "your_email@example.com"  # Replace with your email to receive the test

    send_test_email(SMTP_SERVER, SMTP_PORT, USERNAME, PASSWORD, SENDER, RECIPIENT)
