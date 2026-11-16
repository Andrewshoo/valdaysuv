"""Build the static site from CMS JSON and HTML templates. Python 3.11+, no dependencies."""
import argparse
import html
import json
import re
import shutil
import zlib
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = 'https://valdaysuv.ru/'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def esc(value):
    return html.escape(str(value), quote=True)


def image_path(value, required=False):
    value = (value or '').lstrip('/')
    if not value and not required:
        return ''
    path = (ROOT / value).resolve()
    if not path.is_relative_to((ROOT / 'img').resolve()) or not path.is_file():
        raise ValueError(f'Image must exist inside img/: {value}')
    return value


def entries(folder):
    result = []
    for path in sorted((ROOT / 'content' / folder).glob('*.json')):
        item = load(path)
        if not isinstance(item.get('name'), str) or not item['name'].strip():
            raise ValueError(f'Missing name: {path}')
        if item.get('published', True):
            item['_file'] = path.stem
            result.append(item)
    return sorted(result, key=lambda item: (item.get('order', 0), item['name']))


def catalog_html(products, categories, email):
    known = {c['id'] for c in categories}
    if len(known) != len(categories) or any(not re.fullmatch(r'[a-z][a-z0-9-]*', c) for c in known):
        raise ValueError('Category IDs must be unique lowercase Latin identifiers')
    groups = {c['id']: [] for c in categories}
    ids = set()
    for product in products:
        # Existing IDs preserve saved carts; new IDs are stable across rebuilds and renames of titles.
        product['id'] = product.get('id') or (1000 + zlib.crc32(product['_file'].encode('utf-8')))
        pid = product['id']
        if type(pid) is not int or pid < 1 or pid > 9007199254740991 or pid in ids:
            raise ValueError(f'Invalid or duplicate product ID: {pid}')
        ids.add(pid)
        if product['category'] not in groups:
            raise ValueError(f'Unknown category in {product["name"]}')
        number = product.get('number') or 0
        if type(number) is not int or number < 0:
            raise ValueError('Model number must be a nonnegative integer')
        price = product.get('price')
        if price is not None and (type(price) not in (int, float) or price <= 0):
            raise ValueError('Price must be positive or empty')
        image = image_path(product.get('image'))
        name = esc(product['name'])
        picture = (f'<img class="product-img" src="{esc(image)}" alt="{name}" loading="lazy">' if image else
                   '<div class="product-placeholder"><span>Фотография скоро появится</span></div>')
        badge = f'Модель №{number}' if number else next(c['name'] for c in categories if c['id'] == product['category'])
        details = ''.join(f'<p class="product-detail">{esc(product[key])}</p>' for key in ('dimensions', 'description') if product.get(key))
        price_text = f'{price:,.0f}'.replace(',', ' ') + ' ₽' if price is not None else 'Цена по запросу'
        availability = f'<p class="product-availability">{esc(product["availability"])}</p>' if product.get('availability') else ''
        card = f'''<article class="product-card" id="product-{pid}" data-category="{esc(product['category'])}" data-size-number="{number}" data-product-id="{pid}" data-product-name="{name}" data-product-image="{esc(image)}">
    {picture}
    <div class="product-info"><span class="product-type">{esc(badge)}</span>
        <h4 class="product-name">{name}</h4>{details}
        <p class="product-price">{price_text}</p>{availability}
        <button class="btn-add" id="ba{pid}" onclick="addToCart({pid})" hidden>+ В корзину</button>
    </div>
</article>'''
        groups[product['category']].append((number, product.get('order', 0), card))
    nav = '<nav class="catalog-nav" aria-label="Категории товаров">' + ''.join(
        f'<a href="#catalog-{esc(c["id"])}">{esc(c["name"])}<span>{len(groups[c["id"]]) or ""}</span></a>' for c in categories) + '</nav>'
    toolbar = '''<div class="catalog-toolbar"><p>Колокольчики, береста и небольшие подарки из Валдая</p>
<label class="catalog-sort" id="catalogSortControl" hidden>Порядок моделей
<select id="catalogSort"><option value="number-asc">По номеру ↑</option><option value="number-desc">По номеру ↓</option><option value="name">По названию А–Я</option></select></label></div>'''
    sections = []
    for category in categories:
        slug = esc(category['id'])
        cards = '\n'.join(card for _, _, card in sorted(groups[category['id']], key=lambda item: item[:2]))
        content = f'<div class="catalog-grid catalog-group-grid">{cards}</div>' if cards else (
            '<div class="catalog-request"><p>Уточните ассортимент и наличие у мастерской.</p>'
            f'<a class="btn-primary" href="mailto:{esc(email)}?subject={quote(category["name"])}">Узнать об ассортименте ↗</a></div>')
        sections.append(f'''<section class="catalog-group" id="catalog-{slug}" aria-labelledby="heading-{slug}">
<div class="catalog-group-heading"><h3 id="heading-{slug}">{esc(category['name'])}</h3><p>{esc(category['description'])}</p></div>{content}</section>''')
    return nav + toolbar + '<div id="catalogGrid">' + '\n'.join(sections) + '</div>'


def gallery_html(works):
    cards = []
    for i, work in enumerate(works):
        if work['category'] not in ('classic', 'custom', 'places'):
            raise ValueError(f'Unknown gallery category: {work["category"]}')
        image = image_path(work['image'], required=True)
        caption = work.get('caption') or work['name']
        cards.append(f'''<figure class="gallery-card" data-gallery-category="{esc(work['category'])}">
<a class="gallery-image" href="{esc(image)}" aria-label="Увеличить: {esc(work['name'])}">
<img src="{esc(image)}" alt="{esc(caption)}" loading="{'eager' if i < 3 else 'lazy'}" decoding="async"><span class="gallery-zoom" aria-hidden="true">↗</span></a>
<figcaption><h2>{esc(work['name'])}</h2><p>{esc(caption)}</p></figcaption></figure>''')
    return '\n'.join(cards)


def structured_data(name, settings, works):
    if name == 'gallery.html':
        value = {'@context': 'https://schema.org', '@type': 'ImageGallery', 'name': 'Галерея работ — ' + settings['name'],
                 'url': SITE_URL + name, 'inLanguage': 'ru-RU', 'hasPart': [
                     {'@type': 'ImageObject', 'name': w['name'], 'caption': w.get('caption', ''),
                      'contentUrl': SITE_URL + image_path(w['image'], required=True)} for w in works]}
    else:
        value = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'LocalBusiness', '@id': SITE_URL + '#workshop', 'name': settings['name'], 'url': SITE_URL,
             'image': SITE_URL + 'img/photo_5325715840693302141_y.jpg', 'logo': SITE_URL + 'img/logo.png',
             'telephone': settings['phone'], 'email': settings['email'],
             'address': {'@type': 'PostalAddress', 'streetAddress': settings['street'], 'addressLocality': settings['city'], 'addressCountry': 'RU'},
             'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification',
                 'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                 'opens': settings['opens'], 'closes': settings['closes']}]},
            {'@type': 'WebSite', 'url': SITE_URL, 'name': settings['name'], 'inLanguage': 'ru-RU'}]}
    return '<script type="application/ld+json">\n' + json.dumps(value, ensure_ascii=False, indent=2).replace('<', '\\u003c') + '\n</script>'


def build(output):
    settings = load(ROOT / 'content/settings/site.json')
    if not re.fullmatch(r'\+[0-9]{10,15}', settings['phone']):
        raise ValueError('Phone must be international, e.g. +79992801367')
    if not re.fullmatch(r'[^\s@<>"\x00-\x1f]+@[^\s@<>"\x00-\x1f]+\.[^\s@<>"\x00-\x1f]+', settings['email']):
        raise ValueError('Invalid email')
    for key in ('opens', 'closes'):
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', settings[key]):
            raise ValueError('Hours must use HH:MM')
    products = entries('products')
    works = entries('works')
    categories = load(ROOT / 'content/settings/categories.json')['items']
    context = {key: esc(value) for key, value in settings.items()}
    context.update(site_name=esc(settings['name']), hours_display=esc(f'Ежедневно {settings["opens"]} – {settings["closes"]}'),
                   catalog=catalog_html(products, categories, settings['email']), gallery=gallery_html(works), gallery_count=str(len(works)))
    output.mkdir(parents=True, exist_ok=True)
    for template in (ROOT / 'templates').glob('*.html'):
        page_context = dict(context, structured_data=structured_data(template.name, settings, works))
        def replace(match):
            key = match[1]
            if key not in page_context:
                raise ValueError(f'Unknown template variable: {key}')
            return page_context[key]
        page = re.sub(r'{{\s*(\w+)\s*}}', replace, template.read_text(encoding='utf-8'))
        (output / template.name).write_text(page, encoding='utf-8')
    if output != ROOT:
        for folder in ('img', 'src', 'admin'):
            shutil.copytree(ROOT / folder, output / folder, dirs_exist_ok=True)
        for name in ('CNAME', 'robots.txt', 'sitemap.xml'):
            shutil.copy2(ROOT / name, output / name)
        (output / '.nojekyll').touch()
    print(f'Built {len(products)} products, {len(works)} works into {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in-place', action='store_true', help='Update root HTML for local preview')
    args = parser.parse_args()
    build(ROOT if args.in_place else ROOT / 'dist')
