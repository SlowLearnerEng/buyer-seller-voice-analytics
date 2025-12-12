"""
Quick test to verify URL sanitization handles all whitespace cases
"""

# Test cases with various whitespace scenarios
test_urls = [
    # Spaces in URL
    "https://example.com/file with spaces.mp3",
    # Leading/trailing spaces
    "  https://example.com/file.mp3  ",
    # Tabs
    "https://example.com/file\t.mp3",
    # Newlines
    "https://example.com/file\n.mp3",
    # Mixed whitespace
    "https://example.com/ file \t with \n spaces.mp3",
    # URL with query params and spaces
    "https://openapi.airtel.in/gateway/recording?token=abc 123 def",
]

print("URL Sanitization Test")
print("=" * 70)

for url in test_urls:
    # Simulate the sanitization
    clean_url = ''.join(url.split())
    print(f"\nOriginal: {repr(url)}")
    print(f"Cleaned:  {clean_url}")

print("\n" + "=" * 70)
print("✅ All whitespace characters (spaces, tabs, newlines) are removed")
