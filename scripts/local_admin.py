"""Edit catalog prices and stock locally. Run: python scripts/local_admin.py."""
import argparse
import hashlib
import json
import os
import re
import secrets
import tempfile
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlencode, urlsplit

import build


PRODUCTS = build.ROOT / 'content/products'
PREVIEW = build.ROOT / 'dist'
INVENTORY = build.ROOT / '.local-admin'
TOKEN = secrets.token_urlsafe(32)
ESC = build.esc
STATUS_OPTIONS = ('', build.STOCK_AVAILABLE, build.STOCK_UNAVAILABLE)


def product_files():
    return {path.stem: path for path in PRODUCTS.glob('*.json')}


def variants():
    texts = build.load(build.ROOT / 'content/settings/site.json').get('inscriptions', [])
    return list(dict.fromkeys([*texts, build.MONASTERY_INSCRIPTION]))


def categories():
    return build.load(build.ROOT / 'content/settings/categories.json')['items']


def product_fields(fields):
    name = fields['name'].strip()
    short_name = fields.get('short_name', '').strip()
    if not name or len(name) > 160 or len(short_name) > 100:
        raise ValueError('Укажите название до 160 символов. Короткое название — до 100 символов.')
    price = fields.get('price', '').strip().replace(',', '.')
    if price and (not re.fullmatch(r'[0-9]{1,9}(?:\.[0-9]{1,2})?', price) or float(price) <= 0):
        raise ValueError('Укажите положительную цену с точностью до копеек или оставьте поле пустым.')
    return {
        'name': name, 'short_name': short_name,
        'price': (float(price) if '.' in price else int(price)) if price else None,
        'published': fields.get('published') == '1',
    }


def new_product(fields):
    data = product_fields(fields)
    category = fields['category']
    if category not in {item['id'] for item in categories()}:
        raise ValueError('Выберите категорию из списка.')
    number = fields.get('number', '').strip() or '0'
    if not re.fullmatch(r'[0-9]{1,9}', number):
        raise ValueError('Номер модели должен быть целым числом от нуля.')
    existing = product_files()
    products = [dict(build.load(path), _file=key) for key, path in existing.items()]
    ids = {build.product_id(product) for product in products}
    while True:
        key = 'product-' + secrets.token_hex(8)
        pid = build.product_id({'_file': key})
        if key not in existing and pid not in ids:
            break
    order = max((product.get('order', 0) for product in products), default=0) + 1
    return PRODUCTS / f'{key}.json', dict(data, id=pid, category=category, number=int(number), order=order)


def update_product(product, fields, inscriptions):
    product = dict(product, **product_fields(fields))
    if product['category'] == 'bells':
        stock = build.inscription_stock(product)
        for index, text in enumerate(inscriptions):
            value = fields[f'stock_{index}']
            if value not in STATUS_OPTIONS:
                raise ValueError('Неизвестный статус наличия.')
            if value:
                stock[text] = value
            else:
                stock.pop(text, None)
        product['inscription_stock'] = [{'text': text, 'status': value} for text, value in stock.items()]
    else:
        status = fields['availability']
        if status not in (*STATUS_OPTIONS, 'Под заказ'):
            raise ValueError('Неизвестный статус наличия.')
        product['availability'] = status or None
    return product


def status_select(name, selected, options=STATUS_OPTIONS):
    choices = ''.join(
        f'<option value="{ESC(value)}"{" selected" if value == selected else ""}>{ESC(value or "Уточнить")}</option>'
        for value in options
    )
    return f'<select name="{name}">{choices}</select>'


def inventory_fields(product):
    return variants() if product['category'] == 'bells' else ['Всего по товару']


def read_inventory(path):
    try:
        source = path.read_bytes()
    except FileNotFoundError:
        source = b'{}'
    return json.loads(source), hashlib.sha256(source).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
            temporary = file.name
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def update_inventory(counts, fields, labels):
    counts = dict(counts)
    for index, label in enumerate(labels):
        value = fields[f'quantity_{index}'].strip()
        if not value:
            counts.pop(label, None)
        elif re.fullmatch(r'[0-9]+', value):
            counts[label] = int(value)
        else:
            raise ValueError('Количество должно быть целым числом от нуля. Пустое поле означает, что остаток не указан.')
    return counts


def variant_label(text):
    return 'С изображением Иверского монастыря' if text == build.MONASTERY_INSCRIPTION else text


def general_fields(product):
    price = product.get('price')
    checked = ' checked' if product.get('published', True) else ''
    return f"""
        <label>Полное название<input name="name" value="{ESC(product.get('name', ''))}" maxlength="160" required></label>
        <label>Короткое название в каталоге<input name="short_name" value="{ESC(product.get('short_name') or '')}" maxlength="100"></label>
        <label>Цена за штуку, ₽<input name="price" inputmode="decimal" value="{ESC(price if price is not None else '')}"></label>
        <label class="published-field"><input type="checkbox" name="published" value="1"{checked}> Показывать в каталоге</label>"""


def create_editor(values):
    fields = values or {}
    options = ''.join(
        f'<option value="{ESC(category["id"])}"{" selected" if category["id"] == fields.get("category") else ""}>{ESC(category["name"])}</option>'
        for category in categories()
    )
    display = dict(fields, published=values is None or fields.get('published') == '1')
    return f"""<article><h2>Новая позиция</h2>
    <form method="post" action="/new">
        <input type="hidden" name="token" value="{TOKEN}">
        {general_fields(display)}
        <label>Категория<select name="category" required><option value="">Выберите категорию</option>{options}</select></label>
        <label>Номер модели (если есть)<input name="number" inputmode="numeric" pattern="[0-9]*" value="{ESC(fields.get('number', ''))}"></label>
        <button type="submit">Добавить позицию</button>
    </form></article>"""


def editor(path, product, version, inventory_open=False):
    if product['category'] == 'bells':
        stock = build.inscription_stock(product)
        rows = []
        for index, text in enumerate(variants()):
            rows.append(f'<label>{ESC(variant_label(text))}{status_select(f"stock_{index}", stock.get(text))}</label>')
        availability = ''.join(rows)
    else:
        control = status_select('availability', product.get('availability'), (*STATUS_OPTIONS, 'Под заказ'))
        availability = f'<label>Наличие{control}</label>'
    counts, inventory_version = read_inventory(INVENTORY / path.name)
    quantities = ''.join(
        f'<label>{ESC(variant_label(text))}<input name="quantity_{index}" inputmode="numeric" pattern="[0-9]*" value="{ESC(counts.get(text, ""))}"></label>'
        for index, text in enumerate(inventory_fields(product))
    )
    identity = f'<input type="hidden" name="product" value="{ESC(path.stem)}"><input type="hidden" name="token" value="{TOKEN}">'
    return f"""<article><h2>{ESC(product['name'])}</h2>
    <form method="post" action="/">
        {identity}
        <input type="hidden" name="version" value="{version}">
        {general_fields(product)}
        {availability}
        <button type="submit">Сохранить и обновить предпросмотр</button>
    </form>
    <details{' open' if inventory_open else ''}><summary>Фактическое количество, шт.</summary>
        <form method="post" action="/inventory">
            {identity}
            <input type="hidden" name="version" value="{inventory_version}">
            {quantities}
            <button type="submit">Сохранить количество</button>
        </form>
    </details></article>"""


class AdminHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PREVIEW), **kwargs)

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

    def do_GET(self):
        if not self.allowed_host():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        url = urlsplit(self.path)
        if url.path.startswith('/preview/'):
            self.path = url.path.removeprefix('/preview')
            super().do_GET()
            return
        if url.path != '/':
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        query = parse_qs(url.query)
        selected = query.get('product', [''])[0]
        saved = query.get('saved', [''])[0]
        messages = {
            'catalog': 'Изменения сохранены. Предпросмотр обновлён.',
            'inventory': 'Количество сохранено локально.',
            'new': 'Позиция добавлена. Предпросмотр обновлён.',
        }
        self.render_admin(messages.get(saved, ''), selected=selected, inventory_open=saved == 'inventory',
                          creating='new' in query)

    def list_directory(self, path):
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def render_admin(self, message='', status=HTTPStatus.OK, *, selected='', inventory_open=False,
                     creating=False, values=None):
        choices = []
        form = ''
        for path in sorted(product_files().values()):
            source = path.read_bytes()
            product = json.loads(source)
            label = product['name'] if product.get('published', True) else product['name'] + ' (скрыт)'
            choices.append((product.get('order', 0), label, path.stem))
            if path.stem == selected:
                form = editor(path, product, hashlib.sha256(source).hexdigest(), inventory_open)
        if selected and not form:
            status = HTTPStatus.NOT_FOUND
            message = 'Позиция не найдена. Выберите товар из списка.'
        if creating:
            form = create_editor(values)
        options = ''.join(
            f'<option value="{ESC(key)}"{" selected" if key == selected else ""}>{ESC(name)}</option>'
            for _, name, key in sorted(choices)
        )
        body = f"""<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Каталог мастерской</title>
<style>
body{{max-width:780px;margin:32px auto;padding:0 16px;background:#f5f1e9;color:#302e27;font:16px/1.5 Arial,sans-serif}}
h1,h2{{font-family:Georgia,serif}} h2{{margin-top:0}} a{{color:#68452f}}
article{{margin:16px 0;padding:18px;background:#fcfaf6;border:1px solid #d2c8bb;border-radius:6px}}
details{{margin-top:16px;padding-top:12px;border-top:1px solid #d2c8bb}}
summary{{cursor:pointer;color:#68452f;font-weight:bold}}
label{{display:grid;grid-template-columns:1fr minmax(150px,1fr);gap:12px;align-items:center;margin:10px 0}}
input,select,button{{box-sizing:border-box;max-width:100%;padding:9px;font:inherit}}
button{{background:#85573f;color:white;border:0;border-radius:4px;cursor:pointer}}
.product-picker{{display:flex;align-items:end;gap:12px;margin:18px 0}}
.product-picker label{{display:block;flex:1;min-width:0;margin:0}}
.product-picker select{{display:block;width:100%;margin-top:4px}}
.published-field{{display:flex;align-items:center;gap:8px}}
@media(max-width:540px){{label{{grid-template-columns:1fr;gap:4px}}}}
</style><main><h1>Каталог мастерской</h1><a href="/preview/">Открыть предпросмотр сайта</a><br>
<a href="/?new=1">Добавить позицию</a>
<form action="/" method="get" class="product-picker">
    <label>Товар<select name="product" required><option value="">Выберите позицию</option>{options}</select></label>
    <button type="submit">Открыть</button>
</form>
<p>Статус «Уточнить» отображается, пока наличие не задано. Пустая цена означает «Цена по запросу».</p>
<p>Фактическое количество хранится на этом компьютере. Плашки наличия меняются отдельно.</p>
<p role="status">{ESC(message)}</p>{form}</main></html>"""
        data = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self.allowed_host() or self.path not in ('/', '/inventory', '/new'):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        selected = ''
        is_inventory = self.path == '/inventory'
        creating = self.path == '/new'
        fields = None
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16_384 or self.headers.get_content_type() != 'application/x-www-form-urlencoded':
                raise ValueError('Некорректный запрос.')
            fields = {key: values[0] for key, values in parse_qs(
                self.rfile.read(length).decode('utf-8'), keep_blank_values=True, max_num_fields=100
            ).items()}
            if fields.get('token') != TOKEN:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if creating:
                path, product = new_product(fields)
                write_json(path, product)
            else:
                path = product_files()[fields['product']]
                selected = path.stem
                if not self.save_existing(path, fields, is_inventory):
                    return
            selected = path.stem
            if is_inventory:
                self.redirect('/?' + urlencode({'product': selected, 'saved': 'inventory'}))
                return
        except (KeyError, ValueError, OSError) as error:
            self.render_admin(f'Изменения не сохранены: {error}', HTTPStatus.BAD_REQUEST,
                              selected=selected, inventory_open=is_inventory, creating=creating, values=fields)
            return
        try:
            build.build(PREVIEW)
        except (ValueError, OSError) as error:
            self.render_admin(f'Данные сохранены. Ошибка сборки предпросмотра: {error}',
                              HTTPStatus.INTERNAL_SERVER_ERROR, selected=selected)
            return
        self.redirect('/?' + urlencode({'product': selected, 'saved': 'new' if creating else 'catalog'}))

    def save_existing(self, path, fields, is_inventory):
        snapshot = path.read_bytes()
        product = json.loads(snapshot)
        if is_inventory:
            inventory_path = INVENTORY / path.name
            counts, version = read_inventory(inventory_path)
            if fields.get('version') != version:
                self.render_admin('Количество уже изменилось. Проверьте текущие значения и сохраните снова.',
                                  HTTPStatus.CONFLICT, selected=path.stem, inventory_open=True)
                return False
            write_json(inventory_path, update_inventory(counts, fields, inventory_fields(product)))
        else:
            if fields.get('version') != hashlib.sha256(snapshot).hexdigest():
                self.render_admin('Карточка уже изменилась. Проверьте текущие значения и сохраните снова.',
                                  HTTPStatus.CONFLICT, selected=path.stem)
                return False
            write_json(path, update_product(product, fields, variants()))
        return True

    def redirect(self, location):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', location)
        self.end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    build.build(PREVIEW)
    with HTTPServer(('127.0.0.1', args.port), AdminHandler) as server:
        print(f'Админка: http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
