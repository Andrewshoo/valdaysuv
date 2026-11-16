# Валдайская колокольная мастерская

Сайт https://valdaysuv.ru/ — статические HTML/CSS/JS, редактируемые через Decap CMS.
Репозиторий: https://github.com/Andrewshoo/valdaysuv

## Структура

- `content/products/*.json` — товары, категории, цены, фотографии и наличие.
- `content/works/*.json` — примеры работ в галерее.
- `content/settings/site.json` — контакты и тексты мастерской.
- `content/settings/categories.json` — категории каталога.
- `templates/*.html` — HTML-шаблоны страниц; дизайн меняется здесь и в `src`.
- `src/` — CSS и JavaScript.
- `img/` — изображения, `img/uploads/` — новые загрузки из админки.
- `admin/` — Decap CMS и конфигурация.
- `scripts/build.py` — сборщик на Python без внешних зависимостей.
- `.github/workflows/pages.yml` — проверка и публикация в GitHub Pages.
- `dist/` — результат сборки, не хранится в Git.
- `index.html`, `gallery.html`, `privacy.html` в корне — снимок для локального
  просмотра и первоначального перехода. После наполнения через CMS актуальная
  версия находится в опубликованном `dist`, а не в корневых снимках.

## Сборка и проверка

Требуется Python 3.11 или новее. Из корня репозитория:

```sh
python scripts/build.py
python -m unittest discover -s tests -v
python -m http.server 8000 --directory dist
```

Откройте http://localhost:8000/.
Для обновления корневых HTML после изменения данных: `python scripts/build.py --in-place`.
Не редактируйте сгенерированные карточки вручную: меняйте JSON или CMS.

## Публикация

GitHub Settings → Pages → Source: GitHub Actions.
Push в `main` запускает сборку и публикацию. Pull request запускает проверки
без публикации. В артефакт входят только страницы, `img`, `src`, `admin`,
`CNAME`, `robots.txt`, `sitemap.xml` и `.nojekyll`.
Данные, шаблоны, тесты и служебные документы на сайт не копируются.

Настройка входа и инструкция сотруднику: [ADMIN.md](ADMIN.md).
SEO: [SEO.md](SEO.md).
