"""
Unit test for extractor.py verification
"""
from extractor import (
    extract_emails_from_html,
    decode_cloudflare_email,
    select_primary_email
)

def test_extraction():
    html_sample = """
    <html>
      <head><title>Test Page</title></head>
      <body>
        <h1>Contact Us</h1>
        <p>Email our CEO directly: <a href="mailto:ceo@mycompany.com?subject=Inquiry">Email CEO</a></p>
        <p>General inquiries: info [at] mycompany [dot] com</p>
        <p>Support: support(at)mycompany(dot)com</p>
        <!-- Cloudflare protected email for contact@cloudflare-example.com -->
        <!-- key 0x5a, 'contact@mycompany.com' encoded -->
        <a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="31525e5f45505245715c48525e5c41505f481f525e5c">[email&#160;protected]</a>
        
        <!-- Form field -->
        <form action="/submit">
            <input type="hidden" name="recipient" value="webmaster@mycompany.com">
        </form>

        <!-- Dummy / Noise that must be filtered out -->
        <p>Do not contact: user@example.com</p>
        <p>Placeholder: yourname@domain.com</p>
        <img src="banner@2x.png" alt="banner">
      </body>
    </html>
    """

    found = extract_emails_from_html(html_sample, "https://mycompany.com")
    print(f"Extracted Emails ({len(found)}): {found}")
    
    # Assertions
    assert "ceo@mycompany.com" in found, "Failed to extract mailto"
    assert "info@mycompany.com" in found, "Failed to de-obfuscate [at] [dot]"
    assert "support@mycompany.com" in found, "Failed to de-obfuscate (at) (dot)"
    assert "webmaster@mycompany.com" in found, "Failed to extract from form input"
    assert "user@example.com" not in found, "Failed to filter dummy email"
    assert "yourname@domain.com" not in found, "Failed to filter template email"
    assert "banner@2x.png" not in found, "Failed to filter image extension"

    primary = select_primary_email(list(found), "mycompany.com")
    print(f"Primary selected email: {primary}")
    print("ALL TESTS PASSED!")

if __name__ == "__main__":
    test_extraction()
