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
        self.assertIn('data-price-kopecks="150000"', first)
        product['price'] = 1499.05
        fractional = builder.catalog_html([dict(product)], self.categories, 'test@example.com')
        self.assertIn('data-price-kopecks="149905"', fractional)
        self.assertIn('1 499,05 ₽', fractional)
        product['price'] = None
        unpriced = builder.catalog_html([dict(product)], self.categories, 'test@example.com')
        self.assertIn('data-price-kopecks=""', unpriced)
        self.assertIn('Цена по запросу', unpriced)

    def test_legacy_cart_ids_preserved(self):
        products = builder.entries('products')
        markup = builder.catalog_html(products, self.categories, 'test@example.com')
        page = Page()
        page.feed(markup)
        self.assertEqual(sorted(int(p['data-product-id']) for p in page.products), list(range(1, 12)))

    def test_multiple_product_photos_and_confirmed_number(self):
        no4 = builder.load(ROOT / 'content/products/3.json')
        no5 = builder.load(ROOT / 'content/products/4.json')
        self.assertEqual(no4['image'], '/img/shop/nomer4.jpg')
        self.assertNotIn('/img/shop/nomer4.jpg', [photo['image'] for photo in no5['photos']])
        self.assertEqual(no5['number'], 5)
        self.assertEqual(no5['image'], '/img/shop/nomer5slojvld.png')
        product = dict(no5, _file='4', image='/img/shop/nomer4.jpg', photos=[
            {'image': '/img/shop/nomer4.jpg', 'caption': 'Первый ракурс'},
            {'image': '/img/gallery/gerbvalday.jpg', 'caption': 'Тестовый второй ракурс'},
        ])
        inscriptions = builder.load(ROOT / 'content/settings/site.json')['inscriptions']
        product['inscription_stock'] = [
            {'text': inscriptions[0], 'status': 'В наличии'},
            {'text': inscriptions[1], 'status': 'Нет в наличии'},
        ]
        markup = builder.catalog_html([product], self.categories, 'test@example.com', inscriptions)
        self.assertIn('class="product-photo-link" href="img/shop/nomer4.jpg" data-product-details="4"', markup)
        self.assertNotIn('Рассмотреть изделие', markup)
        for text in inscriptions[:-1]:
            self.assertIn(f'<dt>«{text}»</dt>', markup)
        self.assertNotIn(f'<dt>«{inscriptions[-1]}»</dt>', markup)
        self.assertIn('С изображением Иверского монастыря', markup)
        self.assertIn('stock-available">В наличии', markup)
        self.assertIn('stock-unavailable">Нет в наличии', markup)
        self.assertIn('stock-unknown">Уточнить</span>', markup)
        self.assertIn('href="#custom-order"', markup)
        self.assertNotIn('Ваше оформление', markup)
        self.assertEqual(markup.count('class="product-photo-button"'), 2)
        self.assertIn('data-caption="Первый ракурс"', markup)
        self.assertEqual(markup.split('<template')[0].count('aria-pressed="true"'), 1)
        product['photos'] = [{'image': '../outside.jpg'}]
        with self.assertRaises(ValueError):
            builder.catalog_html([product], self.categories, 'test@example.com')

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
        self.assertEqual(builder.image_path('/img/shop/nomer4.jpg'), 'img/shop/nomer4.jpg')

    def test_shop_and_gallery_media_are_separate(self):
        config = builder.load(ROOT / 'admin/config.yml')
        collections = {entry['name']: entry for entry in config['collections']}
        self.assertEqual(collections['products']['media_folder'], '/img/shop')
        self.assertEqual(collections['works']['media_folder'], '/img/gallery')
        for product in builder.entries('products'):
            if product.get('image'):
                self.assertTrue(product['image'].startswith('/img/shop/'))
            for photo in product.get('photos', []):
                self.assertTrue(photo['image'].startswith('/img/shop/'))
                self.assertTrue((ROOT / photo['image'].lstrip('/')).is_file())
        self.assertFalse(list((ROOT / 'img').glob('*.jpg')))
        self.assertFalse((ROOT / 'dist/img/nomer4.jpg').exists())

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
            config = builder.load(output / 'admin/config.yml')
            products = next(item for item in config['collections'] if item['name'] == 'products')
            stock = next(field for field in products['fields'] if field['name'] == 'inscription_stock')
            variants = next(field for field in stock['fields'] if field['name'] == 'text')
            self.assertEqual(
                [option['value'] for option in variants['options']],
                builder.load(ROOT / 'content/settings/site.json')['inscriptions'],
            )
            self.assertTrue((output / 'admin/config.yml').is_file())
            builder.build(output)
            self.assertFalse((output / 'admin').exists())
            self.assertTrue((ROOT / 'admin/index.html').is_file())

    def test_site_output_and_local_links(self):
        output = ROOT / 'dist'
        self.assertFalse((output / 'admin').exists())
        for private in ('content', 'templates', '.git', 'scripts', 'tests', 'SEO.md'):
            self.assertFalse((output / private).exists(), private)
        for filename in ('index.html', 'gallery.html', 'privacy.html', 'designer.html'):
            text = (output / filename).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'{{\s*\w+\s*}}')
            page = Page()
            page.feed(text)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            for reference in page.refs:
                if reference.startswith(('http:', 'https:', 'mailto:', 'tel:')):
                    continue
                path, _, anchor = reference.partition('#')
                target = output / (path.split('?', 1)[0].lstrip('/') or filename)
                self.assertTrue(target.is_file(), reference)
                if anchor:
                    target_page = Page()
                    target_page.feed(target.read_text(encoding='utf-8'))
                    self.assertIn(anchor, target_page.ids)
            for block in re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', text):
                json.loads(block)


if __name__ == '__main__':
    unittest.main()
