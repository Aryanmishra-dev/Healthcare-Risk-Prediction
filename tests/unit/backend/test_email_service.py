import pytest
from backend.app.services.email_service import (
    build_email,
    render_welcome,
    render_password_reset,
    render_email_verification,
    render_new_login,
    render_security_alert,
    render_generic,
    create_email_backend,
    DevelopmentEmailBackend,
    SMTPEmailBackend,
    email_backend
)
import backend.app.core.config

@pytest.mark.anyio
async def test_email_rendering():
    subject, html = render_welcome("John Doe", "http://test.com")
    assert "John Doe" in html
    assert subject == "Welcome to HealthPredict AI"

    subject, html = render_password_reset("http://reset.com")
    assert "http://reset.com" in html
    assert subject == "Reset your HealthPredict AI password"

    subject, html = render_email_verification("http://verify.com")
    assert "http://verify.com" in html
    assert subject == "Verify your HealthPredict AI email address"

    subject, html = render_new_login("127.0.0.1", "Browser", "http://test.com")
    assert "127.0.0.1" in html
    assert "Browser" in html
    assert subject == "New login detected — HealthPredict AI"

    subject, html = render_security_alert("Alert!", "Bad stuff", "http://test.com")
    assert "Alert!" in html
    assert "Bad stuff" in html
    assert subject == "Security Alert: Alert! — HealthPredict AI"

    subject, html = render_generic("Info", "Hello")
    assert "Info" in html
    assert "Hello" in html
    assert subject == "Info — HealthPredict AI"

@pytest.mark.anyio
async def test_build_email():
    subj, html = build_email("password_reset_request", "title", "msg", {"reset_url": "url"}, "base")
    assert "url" in html
    
    subj, html = build_email("email_verification", "title", "msg", {"verify_url": "url"}, "base")
    assert "url" in html
    
    subj, html = build_email("user_registration", "title", "msg", {"full_name": "Bob"}, "base")
    assert "Bob" in html
    
    subj, html = build_email("new_login", "title", "msg", {"ip_address": "8.8.8.8"}, "base")
    assert "8.8.8.8" in html
    
    subj, html = build_email("account_locked", "title", "msg", None, "base")
    assert "title" in html
    
    subj, html = build_email("other", "title", "msg", None, "base")
    assert "title" in html

@pytest.mark.anyio
async def test_providers():
    backend.app.core.config.settings.email_backend = "development"
    provider = create_email_backend()
    assert isinstance(provider, DevelopmentEmailBackend)
    await provider.send_email("to@example.com", "Subj", "Body")
    
    backend.app.core.config.settings.email_backend = "smtp"
    backend.app.core.config.settings.smtp_host = "test"
    backend.app.core.config.settings.smtp_username = "test"
    backend.app.core.config.settings.smtp_password = "test"
    backend.app.core.config.settings.email_from_address = "test@example.com"
    provider2 = create_email_backend()
    assert isinstance(provider2, SMTPEmailBackend)
    
    # Try sending with a mock
    await provider2.send_email("to@example.com", "Subj", "Body")

