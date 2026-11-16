"""Build the static site from CMS JSON and HTML templates. Python 3.11+, no dependencies."""
import argparse
import hashlib
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
    detail_panels = []
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
        short_name = esc(product.get('short_name') or product['name'])
        picture = (f'<img class="product-img" src="{esc(image)}" alt="{name}" loading="lazy">' if image else
                   '<div class="product-placeholder"><span>Фотография скоро появится</span></div>')
        photo_items = product.get('photos', [])
        if not isinstance(photo_items, list):
            raise ValueError('Product photos must be a list')
        photos = []
        for item in photo_items:
            photo = image_path(item['image'], required=True)
            photos.append((photo, item.get('caption') or product['name']))
        if image and all(path != image for path, _ in photos):
            photos.insert(0, (image, product['name']))
        if len(photos) > 1:
            thumbs = ''.join(
                f'<button type="button" class="product-photo-button" data-photo="{esc(path)}" data-caption="{esc(caption)}" aria-label="{esc(caption)}" aria-pressed="{str(path == image).lower()}"><img src="{esc(path)}" alt="" loading="lazy"></button>'
                for path, caption in photos
            )
            picture = f'<div class="product-photos">{picture}<div class="product-photo-thumbs" aria-label="Ракурсы товара">{thumbs}</div></div>'
        badge = f'Модель №{number}' if number else next(c['name'] for c in categories if c['id'] == product['category'])
        details = ''.join(f'<p class="product-detail product-{key}">{esc(product[key])}</p>' for key in ('dimensions', 'description') if product.get(key))
        price_text = f'{price:,.0f}'.replace(',', ' ') + ' ₽' if price is not None else 'Цена по запросу'
        availability = f'<p class="product-availability">{esc(product["availability"])}</p>' if product.get('availability') else ''
        detail_button = ''
        if image and product.get('description'):
            features = product.get('features', [])
            if not isinstance(features, list) or any(not isinstance(value, str) for value in features):
                raise ValueError('Product features must be a list of text values')
            feature_list = '<ul class="product-feature-list">' + ''.join(f'<li>{esc(value)}</li>' for value in features) + '</ul>' if features else ''
            main_photo = f'<a class="product-detail-image-link" href="{esc(image)}" target="_blank" rel="noopener"><img class="product-detail-image" src="{esc(image)}" alt="{name}"></a>'
            thumbnails = ''.join(f'<button type="button" class="product-detail-thumb" data-photo="{esc(path)}" data-caption="{esc(caption)}" aria-label="{esc(caption)}" aria-pressed="{str(path == image).lower()}"><img src="{esc(path)}" alt="" loading="lazy"></button>' for path, caption in photos) if len(photos) > 1 else ''
            dimension_text = esc(product.get('dimensions') or 'Уточните у мастерской')
            availability_text = esc(product.get('availability') or 'Уточните наличие')
            note = esc(product.get('design_note') or '')
            detail_panels.append(f'''<template id="product-detail-{pid}">
<div class="product-detail-layout">
    <div class="product-detail-photos">{main_photo}<div class="product-detail-thumbnails">{thumbnails}</div></div>
    <div class="product-detail-description"><span class="eyebrow">{esc(badge)}</span><h2 class="product-dialog-title" id="product-dialog-title-{pid}">{name}</h2><p>{esc(product['description'])}</p>{feature_list}
    <dl class="product-specs"><div><dt>Размеры</dt><dd>{dimension_text}</dd></div><div><dt>Наличие</dt><dd>{availability_text}</dd></div><div><dt>Стоимость</dt><dd>{price_text}</dd></div></dl>
    <div class="product-design-note"><h3>Ваше оформление</h3><p>{note}</p></div>
    <button type="button" class="btn-primary product-detail-select" data-select-product="{pid}">Выбрать для заявки →</button><p class="product-select-note">Добавим изделие в корзину. Оформление и стоимость согласуем перед заказом.</p></div>
</div>
</template>''')
            detail_button = f'<button type="button" class="product-more" data-product-details="{pid}" hidden>Рассмотреть изделие ↗</button>'

        card = f'''<article class="product-card" id="product-{pid}" data-category="{esc(product['category'])}" data-size-number="{number}" data-product-id="{pid}" data-product-name="{name}" data-product-image="{esc(image)}">
    {picture}
    <div class="product-info"><span class="product-type">{esc(badge)}</span>
        <h4 class="product-name">{short_name}</h4>{details}
        <p class="product-price">{price_text}</p>{availability}
{detail_button}
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
    return nav + toolbar + '<div id="catalogGrid">' + '\n'.join(sections) + '</div>' + '\n'.join(detail_panels)


def gallery_html(works):
    cards = []
    for i, work in enumerate(works):
        if work['category'] not in ('classic', 'custom', 'places'):
            raise ValueError(f'Unknown gallery category: {work["category"]}')
        image = image_path(work['image'], required=True)
        caption = work.get('caption') or work['name']
        focus_x, focus_y = work.get('image_focus_x', 50), work.get('image_focus_y', 50)
        if any(type(value) not in (int, float) or not 0 <= value <= 100 for value in (focus_x, focus_y)):
            raise ValueError('Gallery image focus must be between 0 and 100')
        theme = {'classic': 'Формы и узоры', 'custom': 'Имена и события', 'places': 'Города и места'}[work['category']]
        cards.append(f'''<figure class="gallery-card" data-gallery-category="{esc(work['category'])}" style="--image-focus-x:{focus_x}%;--image-focus-y:{focus_y}%">
<a class="gallery-image" href="{esc(image)}" aria-label="Увеличить: {esc(work['name'])}">
<img src="{esc(image)}" alt="{esc(caption)}" loading="{'eager' if i < 3 else 'lazy'}" decoding="async"><span class="gallery-zoom" aria-hidden="true">↗</span></a>
<figcaption><span class="gallery-theme">{theme}</span><h2>{esc(work['name'])}</h2><p>{esc(caption)}</p></figcaption></figure>''')
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
             'image': SITE_URL + 'img/shared/photo_5325715840693302141_y.jpg', 'logo': SITE_URL + 'img/shared/logo.png',
             'telephone': [settings['phone'], settings['phone_secondary']], 'email': settings['email'],
             'address': {'@type': 'PostalAddress', 'streetAddress': settings['street'], 'addressLocality': settings['city'], 'addressCountry': 'RU'},
             'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification',
                 'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                 'opens': settings['opens'], 'closes': settings['closes']}]},
            {'@type': 'WebSite', 'url': SITE_URL, 'name': settings['name'], 'inLanguage': 'ru-RU'}]}
    return '<script type="application/ld+json">\n' + json.dumps(value, ensure_ascii=False, indent=2).replace('<', '\\u003c') + '\n</script>'


def build(output, include_admin=False):
    settings = load(ROOT / 'content/settings/site.json')
    for key in ('phone', 'phone_secondary'):
        if not re.fullmatch(r'\+[0-9]{10,15}', settings[key]):
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
    inscriptions = settings.get('inscriptions', [])
    if not isinstance(inscriptions, list) or any(not isinstance(text, str) or not text.strip() for text in inscriptions):
        raise ValueError('Inscriptions must be a list of nonempty strings')
    context['inscriptions_html'] = ''.join(
        f'<blockquote class="inscription"><p>«{esc(text)}»</p></blockquote>' for text in inscriptions
    )
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
        # A changed asset gets a new URL, preventing stale mobile CSS/JS after deployment.
        def version_asset(match):
            path = match[2]
            digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:12]
            return match[1] + path + '?v=' + digest + match[3]
        page = re.sub(r'((?:src|href)=")(src/[^"?]+\.(?:css|js))(")', version_asset, page)
        (output / template.name).write_text(page, encoding='utf-8')
    if output != ROOT:
        admin_output = output / 'admin'
        if not include_admin and admin_output.exists():
            # Remove only the previous generated admin folder, never source admin/.
            if admin_output.resolve().parent != output.resolve() or admin_output.resolve() == (ROOT / 'admin').resolve():
                raise ValueError('Unsafe generated admin path')
            shutil.rmtree(admin_output)
        folders = ('img', 'src', 'admin') if include_admin else ('img', 'src')
        for folder in folders:
            destination = output / folder
            if destination.exists():
                # Recreate generated asset folders so moved/deleted files do not linger.
                if destination.resolve().parent != output.resolve() or destination.resolve() == (ROOT / folder).resolve():
                    raise ValueError('Unsafe generated asset path')
                shutil.rmtree(destination)
            shutil.copytree(ROOT / folder, destination)
        for name in ('CNAME', 'robots.txt', 'sitemap.xml'):
            shutil.copy2(ROOT / name, output / name)
        (output / '.nojekyll').touch()
    print(f'Built {len(products)} products, {len(works)} works into {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in-place', action='store_true', help='Update root HTML for local preview')
    parser.add_argument('--include-admin', action='store_true', help='Include Decap CMS for the Netlify deployment only')
    args = parser.parse_args()
    build(ROOT if args.in_place else ROOT / 'dist', include_admin=args.include_admin)
