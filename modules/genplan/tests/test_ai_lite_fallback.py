"""05.11: Gemini упёрся в дневной лимит (429) → бот сам берёт gemini-flash-lite-latest."""
import io, json, os, unittest, urllib.error
from genplan import ai


class LiteFallback(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "test"
        os.environ.pop("GEMINI_MODEL", None)

    def test_429_goes_to_lite(self):
        seen = []

        def http(req):
            seen.append(req.full_url)
            if "flash-lite" not in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 429, "quota", {}, io.BytesIO(b"{}"))
            return {"candidates": [{"content": {"parts": [{"text": "ок"}]}}]}

        self.assertEqual(ai._gemini("s", "u", http), "ок")
        self.assertTrue(any("gemini-flash-lite-latest" in u for u in seen))

    def test_all_429_raises(self):
        def http(req):
            raise urllib.error.HTTPError(req.full_url, 429, "quota", {}, io.BytesIO(b"{}"))
        with self.assertRaises(urllib.error.HTTPError):
            ai._gemini("s", "u", http)


if __name__ == "__main__":
    unittest.main()
