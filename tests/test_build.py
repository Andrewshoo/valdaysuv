import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('site_builder', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.refs = []
        self.products = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'data-product-id' in attrs:
            self.products.append(attrs)
        for key in ('src', 'href'):
            if key in attrs:
                self.refs.append(attrs[key])


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.categories = builder.load(ROOT / 'content/settings/categories.json')['items']

    def test_new_product_has_stable_id_and_escaped_content(self):
        product = {'_file': 'new-product', 'name': '<script>alert(1)</script>',
                   'category': 'bells', 'number': 3, 'price': 1500, 'image': ''}
        first = builder.catalog_html([dict(product)], self.categories, 'test@example.com')
        second = builder.catalog_html([dict(product)], self.categories, 'test@example.com')
        self.assertEqual(first, second)
        self.assertNotIn('<script>alert', first)
        self.assertIn('&lt;script&gt;', first)
        self.assertIn('1 500 ₽', first)

    def test_legacy_cart_ids_preserved(self):
        products = builder.entries('products')
        markup = builder.catalog_html(products, self.categories, 'test@example.com')
        page = Page()
        page.feed(markup)
        self.assertEqual(sorted(int(p['data-product-id']) for p in page.products), list(range(1, 12)))

    def test_rejects_invalid_catalog(self):
        product = {'_file': 'test', 'name': 'Тест', 'id': 1, 'category': 'bells'}
        for change in ({'price': 0}, {'category': 'missing'}, {'number': -1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                builder.catalog_html([dict(product, **change)], self.categories, 'test@example.com')
        with self.assertRaises(ValueError):
            builder.catalog_html([dict(product), dict(product)], self.categories, 'test@example.com')

    def test_images_must_exist_and_stay_inside_image_directory(self):
        for value in ('../secrets.png', 'content/settings/site.json', 'img/does-not-exist.jpg', 'https://example.com/image.jpg'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                builder.image_path(value, required=True)
        self.assertEqual(builder.image_path('/img/nomer4.jpg'), 'img/nomer4.jpg')

    def test_drafts_excluded(self):
        original = builder.ROOT
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'content/products').mkdir(parents=True)
            (root / 'content/products/draft.json').write_text(json.dumps({'name': 'Draft', 'published': False}))
            try:
                builder.ROOT = root
                self.assertEqual(builder.entries('products'), [])
            finally:
                builder.ROOT = original

    def test_admin_is_netlify_only_and_removed_on_public_rebuild(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'site'
            builder.build(output, include_admin=True)
            self.assertTrue((output / 'admin/index.html').is_file())
            self.assertTrue((output / 'admin/config.yml').is_file())
            builder.build(output)
            self.assertFalse((output / 'admin').exists())
            self.assertTrue((ROOT / 'admin/index.html').is_file())

    def test_site_output_and_local_links(self):
        output = ROOT / 'dist'
        self.assertFalse((output / 'admin').exists())
        for private in ('content', 'templates', '.git', 'scripts', 'tests', 'SEO.md'):
            self.assertFalse((output / private).exists(), private)
        for filename in ('index.html', 'gallery.html', 'privacy.html'):
            text = (output / filename).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'{{\s*\w+\s*}}')
            page = Page()
            page.feed(text)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            for reference in page.refs:
                if reference.startswith(('http:', 'https:', 'mailto:', 'tel:')):
                    continue
                path, _, anchor = reference.partition('#')
                target = output / (path.lstrip('/') or filename)
                self.assertTrue(target.is_file(), reference)
                if anchor:
                    target_page = Page()
                    target_page.feed(target.read_text(encoding='utf-8'))
                    self.assertIn(anchor, target_page.ids)
            for block in re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', text):
                json.loads(block)


if __name__ == '__main__':
    unittest.main()
