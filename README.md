# Warehouse Web

Веб-приложение для управления складом и закупками.

Проект предназначен для:
- учёта товаров
- управления закупками (Россия / Китай)
- отслеживания логистики
- оприходования партий на склад
- подготовки данных для дальнейшей реализации (Wildberries / Ozon)

---

## 🧱 Архитектура

- **FastAPI** — backend API
- **SQLAlchemy (async)** — ORM
- **PostgreSQL** — база данных
- **Alembic** — миграции
- **SQLAdmin** — веб-админка
- **Python 3.11+**

---

## 📦 Основные сущности

### Справочники
- Product — товар
- Warehouse — склад
- Supplier — поставщик

### Закупочный контур
- Supply — закупка / поставка
- SupplyItem — позиции в закупке
- SupplyEvent — логистические события
- Batch — партия товара на складе

Вся логика движения товара описана в:
- `WAREHOUSE_CANON.md`
- `WAREHOUSE_FLOW.md`

---

## 🚀 Запуск проекта

### 1. Установка зависимостей
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
