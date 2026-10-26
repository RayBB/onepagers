"""Tests for scrape_page.py URL cleaning — pure functions, no network."""

import unittest

from scrape_page import clean_url_for_domains, unwrap_linkedin_redirect


class TestUnwrapLinkedInRedirect(unittest.TestCase):
    """LinkedIn outbound-redirect URLs carry the real destination in `url`."""

    def test_safety_go_encoded_destination(self):
        url = (
            "https://www.linkedin.com/safety/go?url="
            "https%3A%2F%2Fow.ly%2F1y7950PGZbq%3Ftrk%3Dfeed_main-feed-card-text"
        )
        self.assertEqual(
            unwrap_linkedin_redirect(url),
            "https://ow.ly/1y7950PGZbq?trk=feed_main-feed-card-text",
        )

    def test_redir_redirect_with_urlhash(self):
        url = (
            "https://www.linkedin.com/redir/redirect?url="
            "https%3A%2F%2Fexample%2Ecom%2Fcert%2F9hJUZz&urlhash=D0OT"
        )
        self.assertEqual(
            unwrap_linkedin_redirect(url), "https://example.com/cert/9hJUZz"
        )

    def test_trailing_slash_variant(self):
        url = "https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fexample.com%2F"
        self.assertEqual(unwrap_linkedin_redirect(url), "https://example.com/")

    def test_unencoded_destination(self):
        url = "https://www.linkedin.com/safety/go?url=https://example.com/x"
        self.assertEqual(unwrap_linkedin_redirect(url), "https://example.com/x")

    def test_url_appears_after_other_params(self):
        url = (
            "https://www.linkedin.com/safety/go?trk=abc&url="
            "https%3A%2F%2Fexample.com%2F&lipi=123"
        )
        self.assertEqual(unwrap_linkedin_redirect(url), "https://example.com/")

    def test_missing_url_param_unchanged(self):
        url = "https://www.linkedin.com/safety/go?urlhash=D0OT"
        self.assertEqual(unwrap_linkedin_redirect(url), url)

    def test_empty_url_param_unchanged(self):
        url = "https://www.linkedin.com/safety/go?url="
        self.assertEqual(unwrap_linkedin_redirect(url), url)

    def test_destination_without_scheme_unchanged(self):
        url = "https://www.linkedin.com/redir/redirect?url=www%2Eefset%2Eorg%2Fcert"
        self.assertEqual(unwrap_linkedin_redirect(url), url)

    def test_javascript_destination_unchanged(self):
        url = "https://www.linkedin.com/redir/redirect?url=javascript%3Aalert(1)"
        self.assertEqual(unwrap_linkedin_redirect(url), url)

    def test_non_linkedin_host_unchanged(self):
        url = "https://www.linkedin.com.evil.example/safety/go?url=https%3A%2F%2Fx.com"
        self.assertEqual(unwrap_linkedin_redirect(url), url)

    def test_linkedin_non_redirect_path_unchanged(self):
        url = "https://www.linkedin.com/posts/foo?trk=bar"
        self.assertEqual(unwrap_linkedin_redirect(url), url)


class TestCleanUrlForDomains(unittest.TestCase):
    """clean_url_for_domains unwraps LinkedIn redirects, strips tracking."""

    def test_linkedin_safety_go_keeps_destination(self):
        url = (
            "https://www.linkedin.com/safety/go?url="
            "https%3A%2F%2Fow.ly%2F1y7950PGZbq%3Ftrk%3Dfeed_main-feed-card-text"
        )
        self.assertEqual(
            clean_url_for_domains(url),
            "https://ow.ly/1y7950PGZbq?trk=feed_main-feed-card-text",
        )

    def test_linkedin_permalink_strips_query(self):
        url = "https://www.linkedin.com/posts/foo?trk=bar&lipi=123"
        self.assertEqual(
            clean_url_for_domains(url), "https://www.linkedin.com/posts/foo"
        )

    def test_other_domain_strips_utm(self):
        url = "https://example.com/article?utm_source=x&utm_medium=y&id=5"
        self.assertEqual(clean_url_for_domains(url), "https://example.com/article?id=5")

    def test_other_domain_keeps_fragment(self):
        url = "https://example.com/page?utm_source=x#section"
        self.assertEqual(clean_url_for_domains(url), "https://example.com/page#section")


if __name__ == "__main__":
    unittest.main()
