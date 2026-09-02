import socket
socket.getaddrinfo('localhost', 8080)

from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from web import mail

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.exception(f"Failed to send email '{msg.subject}' to {msg.recipients}: {e}")

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.html = html_body
    msg.body = text_body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def reset_email(user):
    token = user.generate_token(type='reset')
    send_email(
        ('[Russiantechnologies] . Reset Your Password'),
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user.email],
        text_body=render_template('email/forgot.txt', user=user, token=token),
        html_body=render_template('email/forgot.html', user=user, token=token)
               )

def verify_email(user):
    token = user.generate_token(exp=86400, type='verify')
    send_email(
        ('[Russiantechnologies] . Verifications'),
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user.email],
        text_body=render_template('email/verify.txt', user=user, token=token),
        html_body=render_template('email/verify.html', user=user, token=token)
               )

def send_notification_email(user, title, message, action_url=None, action_label='View in Workforce', badge='Notification'):
    """
    Generic branded notification email (used alongside the in-app
    Notification row) — e.g. a Daily Task assignment, a progress update,
    or anything else that should reach someone even if they aren't
    actively looking at the app right now.

    Fails quietly (logged, not raised) so a broken mail server never
    breaks the action that triggered the notification (assigning a task,
    logging progress, etc.) — the in-app notification still goes through
    either way.
    """
    if not user or not getattr(user, 'email', None):
        return
    try:
        send_email(
            f'[Workforce] {title}',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[user.email],
            text_body=render_template('email/task_notification.txt', user=user, title=title, message=message, action_url=action_url),
            html_body=render_template('email/task_notification.html', user=user, title=title, message=message,
                                       action_url=action_url, action_label=action_label, badge=badge, subject_title=title)
        )
    except Exception as e:
        current_app.logger.exception(f"Unhandled error sending notification email in web/utils/email.py: {e}")

