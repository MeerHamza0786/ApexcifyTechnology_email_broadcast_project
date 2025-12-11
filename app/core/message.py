from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BroadcastMessage:
    subject: str
    body_text: str
    body_html: str

    @classmethod
    def default(cls) -> "BroadcastMessage":
        body = (
            "Hello,\n\n"
            "Here is a beautifully formatted broadcast generated from our Python "
            "studio. It proves that one email can reach hundreds of people at once.\n\n"
            "Warm regards,\nBroadcast Studio"
        )
        body_html = f"""
        <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; color:#1f2933;">
                <p>Hello,</p>
                <p>
                    Here is a <strong>beautifully formatted broadcast</strong> generated from our
                    Python studio. It proves that one email can reach hundreds of people at once.
                </p>
                <p style="margin-top:24px;">
                    Warm regards,<br/>
                    <span style="color:#2563eb; font-weight:600;">Broadcast Studio</span>
                </p>
            </body>
        </html>
        """
        return cls(
            subject="Broadcast Studio Demo",
            body_text=body,
            body_html=body_html,
        )


DEFAULT_MESSAGE = BroadcastMessage.default()
EMAIL_SUBJECT = DEFAULT_MESSAGE.subject
EMAIL_BODY = DEFAULT_MESSAGE.body_text

