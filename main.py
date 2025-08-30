import asyncio
import sqlite3
import os
import logging
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки
CLIENT_TOKEN = "7882205686:AAEhWPfQ7ToP0PkRSkz2-EUmpNE0MKdqi9s"
SUPPLIER_TOKEN = "7056012254:AAF4yNL7CdSw9n-do7QQ0kcLf4nGpdV-RkU"
ADMIN_TOKEN = "7626888261:AAFbPb5b-L4sNvSnk9W6Mg7r7FEmWp-6Lv8"
ADMIN_PASSWORD = "8585"  # Пароль для админа

# Наценки по категориям (с упрощенными названиями)
MARKUP_RATES = {
    "Овощи и фрукты": 1.40,
    "Мясо и птица": 1.50,
    "Рыба и морепродукты": 1.60,
    "Яйца": 1.20,
    "Грибы": 1.40,
    "Молочные продукты": 1.20,
    "Сметана и творог": 1.20,
    "Сливочное масло": 1.20,
    "Сыры": 1.40,
    "Мука и сахар": 1.20,
    "Крупы и макароны": 1.20,
    "Масла и уксус": 1.20,
    "Специи и приправы": 1.40,
    "Консервы": 1.40,
    "Орехи и сухофрукты": 1.60,
    "Бобовые": 1.20,
    "Колбасы и сосиски": 1.40,
    "Копчености": 1.50,
    "Замороженные полуфабрикаты": 1.40,
    "Мясные нарезки": 1.40,
    "Хлеб и булочки": 1.20,
    "Выпечка": 1.40,
    "Десерты": 1.60,
    "Мороженое": 1.40,
    "Тесто": 1.20,
    "Кофе": 1.60,
    "Чай": 1.40,
    "Сиропы": 1.60,
    "Соки": 1.40,
    "Вода": 1.20,
    "Газированные напитки": 1.40,
    "Молочные напитки": 1.40,
    "Фреши": 1.80,
    "Авторские напитки": 1.80,
    "Безалкогольные коктейли": 1.80,
    "Ферментированные напитки": 1.80,
    "Специальные напитки": 1.80,
    "Одноразовая посуда": 1.40,
    "Упаковка": 1.40,
    "Крышки и соломинки": 1.60,
    "Салфетки": 1.40,
    "Фильтры": 1.60,
    "Моющие средства": 1.40,
    "Средства от жира": 1.40,
    "Дезинфектанты": 1.40,
    "Средства для уборки": 1.40,
    "Дезинфекция рук": 1.40,
    "Кухонная посуда": 1.40,
    "Сервировочная посуда": 1.40,
    "Стаканы и бокалы": 1.40,
    "Столовые приборы": 1.40,
    "Барный инвентарь": 1.60,
    "Текстиль": 1.40
}

# Упрощенные категории товаров
CATEGORIES = {
    "Свежие продукты": [
        "Овощи и фрукты",
        "Мясо и птица",
        "Рыба и морепродукты",
        "Яйца",
        "Грибы"
    ],
    "Молочные продукты": [
        "Молочные продукты",
        "Сметана и творог",
        "Сливочное масло",
        "Сыры"
    ],
    "Бакалея": [
        "Мука и сахар",
        "Крупы и макароны",
        "Масла и уксус",
        "Специи и приправы",
        "Консервы",
        "Орехи и сухофрукты",
        "Бобовые"
    ],
    "Мясные изделия": [
        "Колбасы и сосиски",
        "Копчености",
        "Замороженные полуфабрикаты",
        "Мясные нарезки"
    ],
    "Хлеб и выпечка": [
        "Хлеб и булочки",
        "Выпечка",
        "Десерты",
        "Мороженое",
        "Тесто"
    ],
    "Напитки": [
        "Кофе",
        "Чай",
        "Сиропы",
        "Соки",
        "Вода",
        "Газированные напитки",
        "Молочные напитки"
    ],
    "Премиум напитки": [
        "Фреши",
        "Авторские напитки",
        "Безалкогольные коктейли",
        "Ферментированные напитки",
        "Специальные напитки"
    ],
    "Расходные материалы": [
        "Одноразовая посуда",
        "Упаковка",
        "Крышки и соломинки",
        "Салфетки",
        "Фильтры"
    ],
    "Чистящие средства": [
        "Моющие средства",
        "Средства от жира",
        "Дезинфектанты",
        "Средства для уборки",
        "Дезинфекция рук"
    ],
    "Посуда и инвентарь": [
        "Кухонная посуда",
        "Сервировочная посуда",
        "Стаканы и бокалы",
        "Столовые приборы",
        "Барный инвентарь",
        "Текстиль"
    ]
}

# Статусы заказов
ORDER_STATUSES = {
    "new": "🆕 Новый",
    "confirmed": "✅ Подтверждён",
    "on_way": "🚚 В пути",
    "delivered": "📦 Доставлен",
    "canceled": "❌ Отменён"
}

# Типы регулярных заказов
RECURRING_TYPES = {
    "daily": "Ежедневно",
    "weekly": "Еженедельно",
    "monthly": "Ежемесячно"
}

# Регулярное выражение для проверки телефона
PHONE_REGEX = re.compile(r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$')

# Инициализация базы данных
def init_db():
    if os.path.exists('b2b.db'):
        os.remove('b2b.db')
    
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                name TEXT,
                role TEXT,
                company TEXT,
                phone TEXT,
                address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''') 
    
    # Таблица категорий (теперь с иерархией)
    cur.execute('''CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT,
                parent_id INTEGER DEFAULT NULL,
                FOREIGN KEY (parent_id) REFERENCES categories(id))''')
    
    # Таблица товаров (добавлены поля для цен)
    cur.execute('''CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                supplier_price REAL,  -- Цена поставщика
                final_price REAL,     -- Итоговая цена с наценкой
                category_id INTEGER,
                supplier_id INTEGER,
                approved BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'active',
                in_stock BOOLEAN DEFAULT 1,  -- Наличие товара
                quantity INTEGER DEFAULT 0,   -- Количество на складе
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (supplier_id) REFERENCES users(id))''')
    
    # Таблица корзин
    cur.execute('''CREATE TABLE cart (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                is_recurring BOOLEAN DEFAULT 0,
                recurring_type TEXT,
                next_delivery DATE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id))''')
    
    # Таблица заказов
    cur.execute('''CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                status TEXT DEFAULT 'new',
                total_amount REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_recurring BOOLEAN DEFAULT 0,
                recurring_type TEXT,
                next_delivery DATE,
                parent_order_id INTEGER DEFAULT NULL,
                FOREIGN KEY (customer_id) REFERENCES users(id),
                FOREIGN KEY (parent_order_id) REFERENCES orders(id))''')
    
    # Таблица элементов заказа
    cur.execute('''CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id))''')
    
    # Таблица статусов поставщиков для заказов
    cur.execute('''CREATE TABLE order_supplier_status (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                supplier_id INTEGER,
                status TEXT DEFAULT 'pending',
                problem_description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (supplier_id) REFERENCES users(id))''')
    
    # Добавляем фиксированные категории и подкатегории
    main_category_ids = {}
    for main_category, subcategories in CATEGORIES.items():
        # Добавляем основную категорию
        cur.execute("INSERT INTO categories (name) VALUES (?)", (main_category,))
        main_category_id = cur.lastrowid
        main_category_ids[main_category] = main_category_id
        
        # Добавляем подкатегории
        for subcategory in subcategories:
            cur.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?)", 
                       (subcategory, main_category_id))
    
    # Добавляем тестового администратора
    cur.execute("INSERT OR IGNORE INTO users (tg_id, name, role, company) VALUES (?, ?, ?, ?)",
                (123456789, "Admin User", "admin", "System"))
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована с фиксированными категориями")

# Инициализация при старте
init_db()

# Состояния
class ProductForm(StatesGroup):
    name = State()
    description = State()
    price = State()
    category = State()
    quantity = State()

class OrderForm(StatesGroup):
    address = State()
    comment = State()
    recurring = State()
    recurring_type = State()
    delivery_date = State()

class AdminAuth(StatesGroup):
    password = State()

# Состояния для регистрации
class ClientRegistration(StatesGroup):
    name = State()
    phone = State()
    address = State()

class SupplierRegistration(StatesGroup):
    name = State()
    phone = State()
    address = State()

# Состояния для редактирования профиля
class EditProfile(StatesGroup):
    name = State()
    phone = State()
    address = State()

class SupplierProblem(StatesGroup):
    description = State()

# Состояния для редактирования товара
class EditProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    category = State()
    quantity = State()
    in_stock = State()

# Состояния для поиска
class SearchForm(StatesGroup):
    query = State()

# ====================== ОБЩИЕ ФУНКЦИИ ДЛЯ БД ======================
def add_user(tg_id, name, role, company, phone=None, address=None):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (tg_id, name, role, company, phone, address) VALUES (?, ?, ?, ?, ?, ?)", 
                (tg_id, name, role, company, phone, address))
    conn.commit()
    conn.close()
    logger.info(f"Добавлен пользователь: {name} ({role})")

def update_user(tg_id, name, phone, address):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET name=?, phone=?, address=? WHERE tg_id=?", 
                (name, phone, address, tg_id))
    conn.commit()
    conn.close()
    logger.info(f"Обновлен пользователь: {name}")

def get_user(tg_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    user = cur.fetchone()
    conn.close()
    return user

def get_categories(parent_id=None):
    """Получить категории, с возможностью фильтрации по родительской категории"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    if parent_id is None:
        cur.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    else:
        cur.execute("SELECT id, name FROM categories WHERE parent_id = ?", (parent_id,))
    
    categories = cur.fetchall()
    conn.close()
    return categories

def get_category(category_id):
    """Получить информацию о категории по ID"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name, parent_id FROM categories WHERE id = ?", (category_id,))
    category = cur.fetchone()
    conn.close()
    return category

def calculate_final_price(supplier_price, category_name):
    """Рассчитать итоговую цену с наценкой и округлением"""
    markup_rate = MARKUP_RATES.get(category_name, 1.40)  # 40% по умолчанию
    final_price = supplier_price * markup_rate
    return round(final_price)  # Округляем до целого рубля

def add_product(name, description, supplier_price, category_id, supplier_id, quantity=0, approved=False):
    """Добавить товар с расчетом итоговой цены"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    # Получаем название категории для расчета наценки
    cur.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
    category_result = cur.fetchone()
    category_name = category_result[0] if category_result else ""
    
    # Рассчитываем итоговую цену
    final_price = calculate_final_price(supplier_price, category_name)
    
    in_stock = quantity > 0
    
    cur.execute("""
        INSERT INTO products (name, description, supplier_price, final_price, category_id, supplier_id, approved, quantity, in_stock) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, description, supplier_price, final_price, category_id, supplier_id, approved, quantity, in_stock))
    product_id = cur.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Добавлен товар: {name} (ID: {product_id}, Цена поставщика: {supplier_price}, Итоговая цена: {final_price}, Количество: {quantity})")
    return product_id

def update_product(product_id, name=None, description=None, supplier_price=None, category_id=None, quantity=None, in_stock=None):
    """Обновить данные товара"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    updates = []
    params = []
    
    if name:
        updates.append("name = ?")
        params.append(name)
    if description:
        updates.append("description = ?")
        params.append(description)
    if supplier_price is not None:
        updates.append("supplier_price = ?")
        params.append(supplier_price)
    if category_id:
        updates.append("category_id = ?")
        params.append(category_id)
    if quantity is not None:
        in_stock_val = quantity > 0
        updates.append("quantity = ?")
        updates.append("in_stock = ?")
        params.append(quantity)
        params.append(in_stock_val)
    elif in_stock is not None:
        updates.append("in_stock = ?")
        params.append(in_stock)
    
    # Если есть обновления
    if updates:
        # Пересчитываем итоговую цену
        if supplier_price or category_id:
            # Получаем текущие данные товара
            cur.execute("SELECT category_id FROM products WHERE id = ?", (product_id,))
            current_category_id = cur.fetchone()[0]
            
            # Если передана новая категория, используем ее
            if category_id:
                current_category_id = category_id
                
            cur.execute("SELECT name FROM categories WHERE id = ?", (current_category_id,))
            category_name = cur.fetchone()[0]
            
            # Используем новую цену если передана, иначе берем текущую
            if supplier_price is None:
                cur.execute("SELECT supplier_price FROM products WHERE id = ?", (product_id,))
                supplier_price = cur.fetchone()[0]
            
            final_price = calculate_final_price(supplier_price, category_name)
            updates.append("final_price = ?")
            params.append(final_price)
        
        # Сбрасываем статус подтверждения
        updates.append("approved = 0")
        
        # Формируем запрос
        update_str = ", ".join(updates)
        params.append(product_id)
        
        cur.execute(f"UPDATE products SET {update_str} WHERE id = ?", params)
        conn.commit()
    
    conn.close()
    return True

def approve_product(product_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("UPDATE products SET approved = 1 WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    logger.info(f"Товар подтвержден: ID {product_id}")

def reject_product(product_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    logger.info(f"Товар отклонен: ID {product_id}")

def toggle_product_stock(product_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("UPDATE products SET in_stock = NOT in_stock WHERE id = ?", (product_id,))
    conn.commit()
    cur.execute("SELECT in_stock FROM products WHERE id = ?", (product_id,))
    in_stock = cur.fetchone()[0]
    conn.close()
    return in_stock

def get_pending_products():
    """Получить все товары, ожидающие подтверждения"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE approved = 0")
    products = cur.fetchall()
    conn.close()
    return products

def add_to_cart(user_id, product_id, quantity=1, is_recurring=False, recurring_type=None, next_delivery=None):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    # Проверяем наличие товара
    cur.execute("SELECT quantity, in_stock FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()
    if not product or not product[1]:  # in_stock
        conn.close()
        return False, "Товар отсутствует в наличии"
    
    # Проверяем количество
    available_quantity = product[0]
    if available_quantity < quantity:
        conn.close()
        return False, f"Доступно только {available_quantity} шт."
    
    cur.execute("""
        SELECT id, quantity 
        FROM cart 
        WHERE user_id = ? 
          AND product_id = ? 
          AND is_recurring = ?
          AND recurring_type = ?
          AND next_delivery = ?
    """, (user_id, product_id, is_recurring, recurring_type, next_delivery))
    item = cur.fetchone()
    
    if item:
        new_quantity = item[1] + quantity
        if new_quantity > available_quantity:
            conn.close()
            return False, f"Доступно только {available_quantity} шт. У вас уже {item[1]} в корзине"
        
        cur.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_quantity, item[0]))
    else:
        cur.execute("""
            INSERT INTO cart (user_id, product_id, quantity, is_recurring, recurring_type, next_delivery) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, product_id, quantity, is_recurring, recurring_type, next_delivery))
    
    conn.commit()
    conn.close()
    return True, ""

def get_cart(user_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, p.id, p.name, p.final_price, c.quantity, 
               c.is_recurring, c.recurring_type, c.next_delivery
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ? AND p.approved = 1 AND p.in_stock = 1
    """, (user_id,))
    cart_items = cur.fetchall()
    conn.close()
    return cart_items

def clear_cart(user_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def create_order(user_id, address="", comment="", is_recurring=False, recurring_type=None, next_delivery=None, parent_order_id=None):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    cart_items = get_cart(user_id)
    if not cart_items:
        return None, "Ваша корзина пуста"
    
    # Проверяем наличие и списываем товары
    for item in cart_items:
        cart_id, product_id, name, price, quantity, _, _, _ = item
        cur.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
        available_quantity = cur.fetchone()[0]
        
        if available_quantity < quantity:
            conn.close()
            return None, f"Товар '{name}' недоступен в количестве {quantity} шт. (доступно {available_quantity} шт.)"
        
        # Уменьшаем количество
        new_quantity = available_quantity - quantity
        in_stock = new_quantity > 0
        cur.execute("UPDATE products SET quantity = ?, in_stock = ? WHERE id = ?", 
                   (new_quantity, in_stock, product_id))
    
    total_amount = sum(item[3] * item[4] for item in cart_items)  # final_price * quantity
    
    cur.execute("""
        INSERT INTO orders (customer_id, total_amount, is_recurring, recurring_type, next_delivery, parent_order_id) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, total_amount, is_recurring, recurring_type, next_delivery, parent_order_id))
    order_id = cur.lastrowid
    
    for item in cart_items:
        _, product_id, _, price, quantity, _, _, _ = item
        cur.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price) 
            VALUES (?, ?, ?, ?)
        """, (order_id, product_id, quantity, price))
    
    cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    return order_id, ""

def get_user_orders(user_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, total_amount, status, created_at, is_recurring, recurring_type, next_delivery 
        FROM orders 
        WHERE customer_id = ?
    """, (user_id,))
    orders = cur.fetchall()
    conn.close()
    return orders

def get_order_details(order_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cur.fetchone()
    
    cur.execute("""
        SELECT p.name, oi.quantity, oi.price 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE order_id = ?
    """, (order_id,))
    items = cur.fetchall()
    
    conn.close()
    return order, items

def get_supplier_products(supplier_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    # Для поставщика показываем только supplier_price
    cur.execute("""
        SELECT id, name, supplier_price, approved, in_stock, quantity 
        FROM products 
        WHERE supplier_id = ?
    """, (supplier_id,))
    products = cur.fetchall()
    conn.close()
    return products

def get_visible_products(category_id=None, offset=0, limit=10):
    """Получить все видимые товары (подтверждённые) с пагинацией"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    if category_id:
        cur.execute("""
            SELECT id, name, final_price, in_stock, quantity 
            FROM products 
            WHERE approved = 1 
              AND status = 'active'
              AND in_stock = 1
              AND category_id = ?
            LIMIT ? OFFSET ?
        """, (category_id, limit, offset))
    else:
        cur.execute("""
            SELECT id, name, final_price, in_stock, quantity 
            FROM products 
            WHERE approved = 1 
              AND status = 'active'
              AND in_stock = 1
            LIMIT ? OFFSET ?
        """, (limit, offset))
    
    products = cur.fetchall()
    conn.close()
    logger.info(f"Получено {len(products)} видимых товаров для категории {category_id}")
    return products

def get_category_products_count(category_id):
    """Получить количество товаров в категории"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM products 
        WHERE approved = 1 
          AND status = 'active'
          AND in_stock = 1
          AND category_id = ?
    """, (category_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT tg_id, name, role, company, phone, address FROM users")
    users = cur.fetchall()
    conn.close()
    return users

def get_all_orders():
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT id, customer_id, total_amount, status FROM orders")
    orders = cur.fetchall()
    conn.close()
    return orders

def get_product_details(product_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id, 
            name, 
            description, 
            supplier_price, 
            final_price, 
            category_id, 
            supplier_id, 
            approved, 
            status, 
            in_stock,
            quantity,
            created_at 
        FROM products 
        WHERE id = ?
    """, (product_id,))
    product = cur.fetchone()
    conn.close()
    return product

def get_user_by_id(tg_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    user = cur.fetchone()
    conn.close()
    return user

def get_admins():
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM users WHERE role = 'admin'")
    admins = [row[0] for row in cur.fetchall()]
    conn.close()
    return admins

def update_order_status(order_id, status):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    logger.info(f"Статус заказа #{order_id} изменен на {status}")

def create_order_supplier_status(order_id, supplier_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO order_supplier_status (order_id, supplier_id) VALUES (?, ?)", 
                (order_id, supplier_id))
    conn.commit()
    conn.close()
    logger.info(f"Создан статус для заказа #{order_id} поставщика {supplier_id}")

def update_supplier_status(order_id, supplier_id, status, problem=None):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        UPDATE order_supplier_status 
        SET status = ?, problem_description = ?
        WHERE order_id = ? AND supplier_id = ?
    """, (status, problem, order_id, supplier_id))
    conn.commit()
    conn.close()
    logger.info(f"Статус поставщика {supplier_id} для заказа #{order_id} изменен на {status}")

def update_cart_quantity(cart_id, delta):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT quantity, product_id FROM cart WHERE id = ?", (cart_id,))
    result = cur.fetchone()
    
    if result:
        quantity, product_id = result
        new_quantity = quantity + delta
        
        # Проверяем доступное количество
        cur.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
        available_quantity = cur.fetchone()[0]
        
        if new_quantity <= 0:
            cur.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
        elif new_quantity > available_quantity:
            conn.close()
            return False, f"Доступно только {available_quantity} шт."
        else:
            cur.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_quantity, cart_id))
        
        conn.commit()
        conn.close()
        return True, ""
    conn.close()
    return False, "Товар не найден"

def remove_from_cart(cart_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
    conn.commit()
    conn.close()
    logger.info(f"Товар удален из корзины: ID {cart_id}")

def get_order_suppliers(order_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT p.supplier_id 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE oi.order_id = ?
    """, (order_id,))
    supplier_ids = [row[0] for row in cur.fetchall()]
    conn.close()
    return supplier_ids

def get_supplier_orders(supplier_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT oi.order_id 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE p.supplier_id = ?
    """, (supplier_id,))
    order_ids = [row[0] for row in cur.fetchall()]
    conn.close()
    return order_ids

def get_supplier_order_status(order_id, supplier_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT status, problem_description 
        FROM order_supplier_status 
        WHERE order_id = ? AND supplier_id = ?
    """, (order_id, supplier_id))
    status = cur.fetchone()
    conn.close()
    return status

def get_supplier_order_items(order_id, supplier_id):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    # Для поставщика показываем supplier_price вместо итоговой цены
    cur.execute("""
        SELECT p.name, oi.quantity, p.supplier_price 
        FROM order_items oi 
        JOIN products p ON oi.product_id = p.id 
        WHERE oi.order_id = ? AND p.supplier_id = ?
    """, (order_id, supplier_id))
    items = cur.fetchall()
    conn.close()
    return items

def get_recurring_orders():
    """Получить все активные регулярные заказы"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, customer_id, recurring_type, next_delivery 
        FROM orders 
        WHERE is_recurring = 1 
          AND status != 'canceled'
    """)
    orders = cur.fetchall()
    conn.close()
    return orders

def create_recurring_order(parent_order_id):
    """Создать новый заказ на основе родительского регулярного заказа"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    
    # Получаем данные родительского заказа
    cur.execute("SELECT * FROM orders WHERE id = ?", (parent_order_id,))
    parent_order = cur.fetchone()
    
    if not parent_order:
        return None
    
    # Рассчитываем следующую дату доставки
    recurring_type = parent_order[6]  # recurring_type
    next_delivery = parent_order[7]   # next_delivery
    
    if recurring_type == "daily":
        new_delivery = (datetime.strptime(next_delivery, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    elif recurring_type == "weekly":
        new_delivery = (datetime.strptime(next_delivery, "%Y-%m-%d") + timedelta(weeks=1)).strftime("%Y-%m-%d")
    elif recurring_type == "monthly":
        # Простое добавление 30 дней - для демонстрации
        new_delivery = (datetime.strptime(next_delivery, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        new_delivery = next_delivery
    
    # Создаем новый заказ
    cur.execute("""
        INSERT INTO orders (customer_id, total_amount, is_recurring, recurring_type, next_delivery, parent_order_id, status) 
        VALUES (?, ?, 1, ?, ?, ?, 'new')
    """, (parent_order[1], parent_order[3], recurring_type, new_delivery, parent_order_id))
    new_order_id = cur.lastrowid
    
    # Обновляем дату следующей доставки у родительского заказа
    cur.execute("UPDATE orders SET next_delivery = ? WHERE id = ?", (new_delivery, parent_order_id))
    
    # Копируем товары из родительского заказа
    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, price)
        SELECT ?, product_id, quantity, price
        FROM order_items
        WHERE order_id = ?
    """, (new_order_id, parent_order_id))
    
    conn.commit()
    conn.close()
    
    # Уведомляем клиента
    notify_user(parent_order[1], f"✅ Создан новый регулярный заказ #{new_order_id} на {new_delivery}")
    
    return new_order_id

def search_products(query):
    """Поиск товаров по названию и описанию"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, final_price, in_stock, quantity 
        FROM products 
        WHERE approved = 1 
          AND status = 'active'
          AND in_stock = 1
          AND (name LIKE ? OR description LIKE ?)
    """, (f'%{query}%', f'%{query}%'))
    products = cur.fetchall()
    conn.close()
    return products

def check_low_stock():
    """Проверить товары с низким остатком"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, quantity, supplier_id 
        FROM products 
        WHERE quantity <= 10 AND quantity > 0
    """)
    low_stock_products = cur.fetchall()
    conn.close()
    return low_stock_products

def check_out_of_stock():
    """Проверить товары, закончившиеся на складе"""
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, supplier_id 
        FROM products 
        WHERE quantity = 0 AND in_stock = 1
    """)
    out_of_stock_products = cur.fetchall()
    conn.close()
    return out_of_stock_products

# ====================== КЛАВИАТУРЫ ======================
def client_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Каталог"), KeyboardButton(text="📦 Корзина")],
            [KeyboardButton(text="📝 Мои заказы"), KeyboardButton(text="🔄 Регулярные заказы")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

def supplier_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="📦 Мои товары"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📦 Заказы")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📚 Категории")],
            [KeyboardButton(text="🆕 Запросы на размещение")]
        ],
        resize_keyboard=True
    )

def recurring_type_keyboard():
    builder = InlineKeyboardBuilder()
    for key, value in RECURRING_TYPES.items():
        builder.add(types.InlineKeyboardButton(
            text=value,
            callback_data=f"recurring_{key}")
        )
    builder.adjust(2)
    return builder.as_markup()

def order_status_keyboard(order_id):
    builder = InlineKeyboardBuilder()
    for status_key, status_text in ORDER_STATUSES.items():
        builder.add(types.InlineKeyboardButton(
            text=status_text,
            callback_data=f"set_status_{order_id}_{status_key}")
        )
    builder.adjust(2)
    return builder.as_markup()

def help_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="📚 FAQ", callback_data="faq"))
    builder.add(types.InlineKeyboardButton(text="💬 Задать вопрос", callback_data="ask_question"))
    builder.adjust(1)
    return builder.as_markup()

def pagination_keyboard(category_id, current_page, total_pages):
    builder = InlineKeyboardBuilder()
    
    if current_page > 0:
        builder.add(types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"page_{category_id}_{current_page - 1}")
        )
    
    builder.add(types.InlineKeyboardButton(
        text=f"{current_page + 1}/{total_pages}",
        callback_data="no_action")
    )
    
    if current_page < total_pages - 1:
        builder.add(types.InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"page_{category_id}_{current_page + 1}")
        )
    
    builder.adjust(3)
    return builder.as_markup()

# ====================== УВЕДОМЛЕНИЯ ======================
async def notify_admins_about_order(order_id):
    try:
        bot = Bot(token=ADMIN_TOKEN)
        
        order, items = get_order_details(order_id)
        if not order:
            return
        
        order_id, customer_id, total, status, created_at, is_recurring, recurring_type, next_delivery, parent_order_id = order
        customer = get_user_by_id(customer_id)
        
        if not customer:
            return
        
        _, _, name, role, company, phone, address, _ = customer
        
        # Получаем список поставщиков из заказа
        supplier_ids = get_order_suppliers(order_id)
        
        # Получаем информацию о поставщиках
        suppliers_info = []
        for supplier_id in supplier_ids:
            supplier = get_user_by_id(supplier_id)
            if supplier:
                _, _, s_name, s_role, s_company, s_phone, s_address, _ = supplier
                suppliers_info.append(f"  ▪️ {s_name} ({s_company}), тел.: {s_phone}, адрес: {s_address}")
        
        # Формируем текст уведомления
        text = (
            "🆕 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
            f"🆔 <b>Заказ #{order_id}</b>\n"
            f"👤 <b>Клиент:</b> {name} ({company})\n"
            f"📱 <b>Телефон:</b> {phone}\n"
            f"🏠 <b>Адрес:</b> {address}\n"
            f"💰 <b>Сумма:</b> {total} руб.\n"
            f"📮 <b>Статус:</b> {ORDER_STATUSES.get(status, status)}\n"
        )
        
        if is_recurring:
            text += f"🔄 <b>Регулярный:</b> {RECURRING_TYPES.get(recurring_type, recurring_type)}\n"
            text += f"📅 <b>Следующая доставка:</b> {next_delivery}\n"
        
        text += "\n📦 <b>Состав заказа:</b>\n"
        
        for item in items:
            name, quantity, price = item
            text += f"  ▪️ {name} - {quantity} шт. x {price} руб.\n"
        
        if suppliers_info:
            text += "\n🏭 <b>Поставщики:</b>\n" + "\n".join(suppliers_info)
        
        # Отправляем уведомление всем администраторам
        admins = get_admins()
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    text,
                    parse_mode="HTML"
                )
            except:
                pass
    except Exception as e:
        print(f"Ошибка при отправке уведомления о заказе: {e}")
    finally:
        await bot.session.close()

async def notify_suppliers_about_order(order_id):
    try:
        bot = Bot(token=SUPPLIER_TOKEN)
        _, items = get_order_details(order_id)
        
        # Группируем товары по поставщикам с supplier_price
        supplier_items = {}
        for item in items:
            product_name, quantity, _ = item
            conn = sqlite3.connect('b2b.db')
            cur = conn.cursor()
            cur.execute("""
                SELECT p.supplier_id, p.supplier_price 
                FROM products p 
                WHERE p.name = ?
            """, (product_name,))
            result = cur.fetchone()
            if result:
                supplier_id, supplier_price = result
                if supplier_id not in supplier_items:
                    supplier_items[supplier_id] = []
                supplier_items[supplier_id].append((product_name, quantity, supplier_price))
            conn.close()
        
        # Отправляем уведомления
        for supplier_id, items in supplier_items.items():
            text = "🆕 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
            text += f"🆔 Заказ #{order_id}\n"
            text += "📦 Ваши товары:\n"
            for item in items:
                name, quantity, price = item
                text += f"  ▪️ {name} - {quantity} шт. x {price} руб.\n"
            
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="✅ Подтвердить готовность",
                callback_data=f"supplier_ready_{order_id}")
            )
            builder.add(types.InlineKeyboardButton(
                text="❌ Проблема с товаром",
                callback_data=f"supplier_problem_{order_id}")
            )
            
            await bot.send_message(
                supplier_id,
                text,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
            create_order_supplier_status(order_id, supplier_id)
    except Exception as e:
        logger.error(f"Ошибка при уведомлении поставщиков: {str(e)}")
    finally:
        await bot.session.close()

async def notify_customer_about_status(order_id, status):
    try:
        bot = Bot(token=CLIENT_TOKEN)
        
        order, items = get_order_details(order_id)
        if not order:
            return
        
        customer_id = order[1]
        status_text = ORDER_STATUSES.get(status, status)
        
        text = f"🔄 Статус вашего заказа #{order_id} изменен: <b>{status_text}</b>"
        
        await bot.send_message(
            customer_id,
            text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении клиента: {str(e)}")
    finally:
        await bot.session.close()

async def notify_admin_about_supplier_status(order_id, supplier_id, status, problem=None):
    try:
        bot = Bot(token=ADMIN_TOKEN)
        
        supplier = get_user_by_id(supplier_id)
        if not supplier:
            return
        
        _, _, name, role, company, phone, address, _ = supplier
        
        status_text = {
            'ready': "готов",
            'problem': "проблема"
        }.get(status, status)
        
        text = (
            f"🏭 <b>Обновление статуса поставщика</b>\n\n"
            f"🆔 Заказ #{order_id}\n"
            f"🏭 Поставщик: {name} ({company})\n"
            f"📮 Статус: <b>{status_text}</b>\n"
        )
        
        if problem:
            text += f"⚠️ Проблема: {problem}"
        
        # Отправляем уведомление всем администраторам
        admins = get_admins()
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    text,
                    parse_mode="HTML"
                )
            except:
                pass
    except Exception as e:
        logger.error(f"Ошибка при уведомлении администратора: {str(e)}")
    finally:
        await bot.session.close()

async def notify_admins_about_product(product_id):
    try:
        bot = Bot(token=ADMIN_TOKEN)
        
        product = get_product_details(product_id)
        if not product:
            return
        
        (_, name, description, supplier_price, final_price, 
         category_id, supplier_id, approved, status, in_stock, quantity, created_at) = product
        
        supplier = get_user_by_id(supplier_id)
        
        if not supplier:
            return
        
        _, _, s_name, s_role, s_company, s_phone, s_address, _ = supplier
        
        # Получаем название категории
        conn = sqlite3.connect('b2b.db')
        cur = conn.cursor()
        cur.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
        category_name = cur.fetchone()
        conn.close()
        category_name = category_name[0] if category_name else "Без категории"
        
        text = (
            "🆕 <b>НОВЫЙ ТОВАР НА МОДЕРАЦИИ</b>\n\n"
            f"🆔 <b>Товар #{product_id}</b>\n"
            f"📦 <b>Название:</b> {name}\n"
            f"📝 <b>Описание:</b> {description}\n"
            f"💰 <b>Цена поставщика:</b> {supplier_price} руб.\n"
            f"💰 <b>Итоговая цена:</b> {final_price} руб.\n"
            f"📚 <b>Категория:</b> {category_name}\n"
            f"🏭 <b>Поставщик:</b> {s_name} ({s_company})\n"
            f"📦 <b>Количество:</b> {quantity} шт.\n"
            f"🟢 <b>В наличии:</b> {'Да' if in_stock else 'Нет'}\n"
        )
        
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"admin_approve_{product_id}")
        )
        builder.add(types.InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"admin_reject_{product_id}")
        )
        
        # Отправляем уведомление всем администраторам
        admins = get_admins()
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id,
                    text,
                    parse_mode="HTML",
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    except Exception as e:
        print(f"Ошибка при отправке уведомления о товаре: {e}")
    finally:
        await bot.session.close()

async def notify_user(user_id, message):
    """Универсальная функция для отправки уведомлений"""
    try:
        user = get_user(user_id)
        if not user:
            return
        
        if user[3] == "customer":
            bot = Bot(token=CLIENT_TOKEN)
        elif user[3] == "supplier":
            bot = Bot(token=SUPPLIER_TOKEN)
        else:
            bot = Bot(token=ADMIN_TOKEN)
        
        await bot.send_message(user_id, message, parse_mode="HTML")
        await bot.session.close()
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {str(e)}")

async def notify_supplier_low_stock(supplier_id, product_id, product_name, quantity):
    """Уведомить поставщика о низком остатке"""
    try:
        bot = Bot(token=SUPPLIER_TOKEN)
        text = (
            f"⚠️ <b>Внимание: низкий остаток товара!</b>\n\n"
            f"📦 Товар: {product_name} (ID: {product_id})\n"
            f"📉 Остаток: {quantity} шт.\n\n"
            f"Пожалуйста, пополните склад."
        )
        await bot.send_message(supplier_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при уведомлении поставщика: {str(e)}")

async def notify_supplier_out_of_stock(supplier_id, product_id, product_name):
    """Уведомить поставщика об отсутствии товара"""
    try:
        bot = Bot(token=SUPPLIER_TOKEN)
        text = (
            f"⛔ <b>Товар закончился на складе!</b>\n\n"
            f"📦 Товар: {product_name} (ID: {product_id})\n\n"
            f"Пожалуйста, пополните склад или снимите товар с продажи."
        )
        await bot.send_message(supplier_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при уведомлении поставщика: {str(e)}")

# ====================== КЛИЕНТСКИЙ БОТ ======================
client_router = Router()

@client_router.message(Command("start"))
async def client_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if user and user[5] and user[6]:  # Если уже есть телефон и адрес
        await show_client_menu(message)
    else:
        add_user(message.from_user.id, message.from_user.full_name, "customer", "Unknown")
        await message.answer("👋 Добро пожаловать! Для регистрации введите ваше имя или название компании:", 
                            reply_markup=ReplyKeyboardRemove())
        await state.set_state(ClientRegistration.name)

async def show_client_menu(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в B2B платформу!\nВыберите действие:",
        reply_markup=client_keyboard()
    )

@client_router.message(ClientRegistration.name)
async def process_client_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("❌ Слишком длинное имя (макс. 100 символов). Введите снова:")
        return
    
    await state.update_data(name=name)
    await message.answer("📱 Введите ваш номер телефона:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ClientRegistration.phone)

@client_router.message(ClientRegistration.phone)
async def process_client_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_REGEX.match(phone):
        await message.answer("❌ Неверный формат телефона. Введите снова:")
        return
    
    await state.update_data(phone=phone)
    await message.answer("🏠 Введите ваш адрес (для доставки и забора товаров):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ClientRegistration.address)

@client_router.message(ClientRegistration.address)
async def process_client_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) > 200:
        await message.answer("❌ Слишком длинный адрес (макс. 200 символов). Введите снова:")
        return
    
    data = await state.get_data()
    update_user(
        tg_id=message.from_user.id,
        name=data.get('name', message.from_user.full_name),
        phone=data.get('phone'),
        address=address
    )
    await state.clear()
    await show_client_menu(message)

@client_router.message(F.text == "🛒 Каталог")
async def handle_catalog(message: types.Message):
    """Показать основные категории товаров"""
    categories = get_categories()  # Основные категории (parent_id IS NULL)
    
    if not categories:
        await message.answer("😔 Категории товаров пока не добавлены")
        return
    
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in categories:
        builder.add(types.InlineKeyboardButton(
            text=cat_name,
            callback_data=f"main_category_{cat_id}")
        )
    builder.row(types.InlineKeyboardButton(
        text="🔍 Поиск товаров",
        callback_data="product_search")
    )
    builder.adjust(2)
    
    await message.answer(
        "📚 Выберите основную категорию или воспользуйтесь поиском:",
        reply_markup=builder.as_markup()
    )

@client_router.callback_query(F.data.startswith("main_category_"))
async def show_main_category(callback: CallbackQuery):
    """Показать подкатегории выбранной основной категории"""
    try:
        main_category_id = int(callback.data.split("_")[2])
        subcategories = get_categories(parent_id=main_category_id)
        
        if not subcategories:
            # Если нет подкатегорий, сразу показываем товары
            await show_category_products(callback, main_category_id, 0)
            return
        
        builder = InlineKeyboardBuilder()
        for cat_id, cat_name in subcategories:
            builder.add(types.InlineKeyboardButton(
                text=cat_name,
                callback_data=f"subcategory_{cat_id}")
            )
        
        # Кнопка назад к основным категориям
        builder.row(types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main_categories")
        )
        
        builder.adjust(2)
        
        await callback.message.edit_text(
            "📚 Выберите подкатегорию:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка при показе подкатегорий: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при загрузке подкатегорий")
    finally:
        await callback.answer()

@client_router.callback_query(F.data == "back_to_main_categories")
async def back_to_main_categories(callback: CallbackQuery):
    """Вернуться к списку основных категорий"""
    await handle_catalog(callback.message)
    await callback.answer()

@client_router.callback_query(F.data.startswith("subcategory_"))
async def show_subcategory_products(callback: CallbackQuery):
    """Показать товары в выбранной подкатегории"""
    try:
        category_id = int(callback.data.split("_")[1])
        await show_category_products(callback, category_id, 0)
    except Exception as e:
        logger.error(f"Ошибка при показе товаров подкатегории: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при загрузке товаров")
    finally:
        await callback.answer()

async def show_category_products(callback: CallbackQuery, category_id: int, page: int = 0, limit: int = 10):
    """Показать товары в категории (общая функция для основных и подкатегорий)"""
    offset = page * limit
    products = get_visible_products(category_id, offset, limit)
    total_products = get_category_products_count(category_id)
    total_pages = (total_products + limit - 1) // limit
    
    builder = InlineKeyboardBuilder()
    if not products:
        # Получаем информацию о категории для кнопки назад
        category_info = get_category(category_id)
        parent_id = category_info[2] if category_info else None
        
        if parent_id:
            # Если это подкатегория, возвращаем к списку подкатегорий
            builder.add(types.InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"main_category_{parent_id}")
            )
        else:
            # Если это основная категория, возвращаем к списку категорий
            builder.add(types.InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_main_categories")
            )
        
        await callback.message.edit_text(
            "😔 В этой категории пока нет товаров",
            reply_markup=builder.as_markup()
        )
        return
    
    for product in products:
        product_id, name, price, in_stock, quantity = product
        stock_text = "✅ В наличии" if in_stock else "❌ Нет в наличии"
        builder.add(types.InlineKeyboardButton(
            text=f"{name} - {price} руб. ({stock_text})",
            callback_data=f"product_{product_id}")
        )
    
    # Кнопка назад
    category_info = get_category(category_id)
    parent_id = category_info[2] if category_info else None
    
    if parent_id:
        # Если это подкатегория, возвращаем к списку подкатегорий
        builder.row(types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"main_category_{parent_id}")
        )
    else:
        # Если это основная категория, возвращаем к списку категорий
        builder.row(types.InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main_categories")
        )
    
    # Пагинация
    if total_pages > 1:
        builder.row()
        pagination_kb = pagination_keyboard(category_id, page, total_pages)
        builder.attach(pagination_kb)
    
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"🛍️ Товары в категории (страница {page+1}/{total_pages}):",
        reply_markup=builder.as_markup()
    )

@client_router.callback_query(F.data.startswith("page_"))
async def handle_pagination(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        category_id = int(parts[1])
        page = int(parts[2])
        await show_category_products(callback, category_id, page)
    except Exception as e:
        logger.error(f"Ошибка пагинации: {str(e)}")
        await callback.answer("❌ Ошибка при загрузке страницы")
    finally:
        await callback.answer()

@client_router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[1])
        product = get_product_details(product_id)
        
        if not product or not product[7]:  # Проверяем approved (индекс 7)
            await callback.message.answer("❌ Товар не найден")
            await callback.answer()
            return
        
        name = product[1]
        description = product[2]
        price = product[4]  # Итоговая цена с наценкой (индекс 4)
        in_stock = product[9]
        quantity = product[10]
        
        stock_text = "✅ В наличии" if in_stock else "❌ Нет в наличии"
        
        builder = InlineKeyboardBuilder()
        if in_stock:
            builder.add(types.InlineKeyboardButton(
                text="➕ Добавить в корзину",
                callback_data=f"add_to_cart_{product_id}")
            )
            builder.add(types.InlineKeyboardButton(
                text="🔄 Добавить как регулярный",
                callback_data=f"add_recurring_{product_id}")
            )
        
        await callback.message.edit_text(
            f"<b>{name}</b>\n\n"
            f"{description}\n\n"
            f"💰 Цена: <b>{price} руб.</b>\n"
            f"📦 Наличие: <b>{stock_text}</b>\n"
            f"📊 Количество: <b>{quantity} шт.</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup() if builder.buttons else None
        )
    except Exception as e:
        logger.error(f"Ошибка при показе товара: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при загрузке товара")
    finally:
        await callback.answer()

@client_router.callback_query(F.data.startswith("add_to_cart_"))
async def add_product_to_cart(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[3])
        success, message = add_to_cart(callback.from_user.id, product_id)
        
        if success:
            await callback.answer("✅ Товар добавлен в корзину!")
        else:
            await callback.answer(f"❌ {message}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении в корзину: {str(e)}")
        await callback.answer("❌ Ошибка при добавлении товара")

@client_router.callback_query(F.data.startswith("add_recurring_"))
async def add_recurring_product(callback: CallbackQuery, state: FSMContext):
    try:
        product_id = int(callback.data.split("_")[2])
        product = get_product_details(product_id)
        
        if not product or not product[7]:
            await callback.answer("❌ Товар недоступен")
            return
        
        await state.update_data(product_id=product_id)
        await callback.message.answer("🔄 Выберите тип регулярного заказа:", reply_markup=recurring_type_keyboard())
        await state.set_state(OrderForm.recurring_type)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении регулярного товара: {str(e)}")
        await callback.answer("❌ Ошибка при добавлении товара")

@client_router.callback_query(F.data.startswith("recurring_"), OrderForm.recurring_type)
async def process_recurring_type(callback: CallbackQuery, state: FSMContext):
    recurring_type = callback.data.split("_")[1]
    await state.update_data(recurring_type=recurring_type)
    
    # Для простоты будем использовать завтрашнюю дату как следующую доставку
    next_delivery = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    await state.update_data(next_delivery=next_delivery)
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    # Добавляем товар как регулярный
    success, message = add_to_cart(
        callback.from_user.id, 
        product_id, 
        is_recurring=True, 
        recurring_type=recurring_type, 
        next_delivery=next_delivery
    )
    
    if success:
        await callback.message.answer(f"✅ Товар добавлен как регулярный заказ ({RECURRING_TYPES[recurring_type]})")
    else:
        await callback.message.answer(f"❌ {message}")
    
    await state.clear()
    await callback.answer()

@client_router.message(F.text == "📦 Корзина")
async def show_cart(message: types.Message):
    cart_items = get_cart(message.from_user.id)
    
    if not cart_items:
        await message.answer("🛒 Ваша корзина пуста")
        return
    
    total = 0
    cart_text = "🛒 Содержимое корзины:\n\n"
    builder = InlineKeyboardBuilder()
    
    for item in cart_items:
        cart_id, product_id, name, price, quantity, is_recurring, recurring_type, next_delivery = item
        item_total = price * quantity
        total += item_total
        
        cart_text += f"▪️ {name}\n  - {quantity} шт. x {price} руб. = {item_total} руб.\n"
        
        if is_recurring:
            cart_text += f"  🔄 Регулярный ({RECURRING_TYPES.get(recurring_type, recurring_type)}), доставка: {next_delivery}\n"
        
        builder.row(
            types.InlineKeyboardButton(
                text=f"❌ {name[:15]}...",
                callback_data=f"remove_{cart_id}"
            ),
            types.InlineKeyboardButton(
                text="➖",
                callback_data=f"decr_{cart_id}"
            ),
            types.InlineKeyboardButton(
                text=f"{quantity}",
                callback_data="no_action"
            ),
            types.InlineKeyboardButton(
                text="➕",
                callback_data=f"incr_{cart_id}"
            )
        )
    
    cart_text += f"\n💵 Итого: {total} руб."
    
    # Изменено: поменяли местами кнопки "Очистить корзину" и "Оформить заказ"
    builder.row(
        types.InlineKeyboardButton(
            text="🗑️ Очистить корзину",
            callback_data="clear_cart"
        ),
        types.InlineKeyboardButton(
            text="🚀 Оформить заказ",
            callback_data="checkout"
        )
    )
    
    await message.answer(
        cart_text,
        reply_markup=builder.as_markup()
    )

@client_router.callback_query(F.data == "no_action")
async def no_action(callback: CallbackQuery):
    await callback.answer()

@client_router.callback_query(F.data.startswith("decr_"))
async def decrease_quantity(callback: CallbackQuery):
    cart_id = int(callback.data.split("_")[1])
    success, message = update_cart_quantity(cart_id, -1)
    
    if success:
        await callback.answer("➖ Уменьшено количество")
        await show_cart(callback.message)
    else:
        await callback.answer(f"❌ {message}")

@client_router.callback_query(F.data.startswith("incr_"))
async def increase_quantity(callback: CallbackQuery):
    cart_id = int(callback.data.split("_")[1])
    success, message = update_cart_quantity(cart_id, 1)
    
    if success:
        await callback.answer("➕ Увеличено количество")
        await show_cart(callback.message)
    else:
        await callback.answer(f"❌ {message}")

@client_router.callback_query(F.data.startswith("remove_"))
async def remove_item(callback: CallbackQuery):
    cart_id = int(callback.data.split("_")[1])
    remove_from_cart(cart_id)
    await callback.answer("🗑️ Товар удален из корзины")
    await show_cart(callback.message)

@client_router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    address = user[6] if user else None
    
    if address:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="🏠 Использовать мой адрес",
            callback_data="use_my_address")
        )
        builder.add(types.InlineKeyboardButton(
            text="✏️ Ввести другой адрес",
            callback_data="enter_new_address")
        )
        
        await callback.message.answer(
            f"🏠 Ваш текущий адрес: {address}\n"
            "Выберите действие:",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.answer("🏠 Введите адрес доставки:")
        await state.set_state(OrderForm.address)
    
    await callback.answer()

@client_router.callback_query(F.data == "use_my_address")
async def use_my_address(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    if user and user[6]:
        await state.update_data(address=user[6])
        await callback.message.answer("💬 Добавьте комментарий к заказу (необязательно):")
        await state.set_state(OrderForm.comment)
    else:
        await callback.message.answer("🏠 Введите адрес доставки:")
        await state.set_state(OrderForm.address)
    
    await callback.answer()

@client_router.callback_query(F.data == "enter_new_address")
async def enter_new_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🏠 Введите новый адрес доставки:")
    await state.set_state(OrderForm.address)
    await callback.answer()

@client_router.message(OrderForm.address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) > 200:
        await message.answer("❌ Слишком длинный адрес (макс. 200 символов). Введите снова:")
        return
    
    await state.update_data(address=address)
    await message.answer("💬 Добавьте комментарий к заказу (необязательно):")
    await state.set_state(OrderForm.comment)

@client_router.message(OrderForm.comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text != "/skip" else ""
    if len(comment) > 500:
        await message.answer("❌ Слишком длинный комментарий (макс. 500 символов). Введите снова:")
        return
    
    await state.update_data(comment=comment)
    
    # Проверяем, есть ли в корзине регулярные товары
    cart_items = get_cart(message.from_user.id)
    has_recurring = any(item[5] for item in cart_items)  # is_recurring flag
    
    if has_recurring:
        await message.answer("🔄 В вашей корзине есть регулярные товары. Оформить весь заказ как регулярный? (да/нет)")
        await state.set_state(OrderForm.recurring)
    else:
        data = await state.get_data()
        await complete_order(message, data)
        await state.clear()

@client_router.message(OrderForm.recurring)
async def process_recurring_choice(message: types.Message, state: FSMContext):
    if message.text.lower() in ["да", "yes", "y"]:
        await message.answer("🔄 Выберите тип регулярного заказа:", reply_markup=recurring_type_keyboard())
        await state.set_state(OrderForm.recurring_type)
    elif message.text.lower() in ["нет", "no", "n"]:
        data = await state.get_data()
        await complete_order(message, data)
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, ответьте 'да' или 'нет'")

@client_router.callback_query(F.data.startswith("recurring_"), OrderForm.recurring_type)
async def process_recurring_type_choice(callback: CallbackQuery, state: FSMContext):
    recurring_type = callback.data.split("_")[1]
    await state.update_data(recurring_type=recurring_type)
    
    # Для простоты используем завтрашнюю дату
    next_delivery = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    await state.update_data(next_delivery=next_delivery)
    
    data = await state.get_data()
    await complete_order(callback.message, data, is_recurring=True)
    await state.clear()
    await callback.answer()

async def complete_order(message: types.Message, data, is_recurring=False):
    recurring_type = data.get('recurring_type')
    next_delivery = data.get('next_delivery')
    
    order_id, error = create_order(
        message.from_user.id,
        data.get('address', ''),
        data.get('comment', ''),
        is_recurring,
        recurring_type,
        next_delivery
    )
    
    if order_id:
        status_text = "регулярный" if is_recurring else "разовый"
        delivery_text = f"\n📅 Следующая доставка: {next_delivery}" if is_recurring else ""
        
        await message.answer(
            f"🎉 {status_text.capitalize()} заказ #{order_id} успешно оформлен!{delivery_text}"
        )
        
        # Уведомление администратора и поставщиков
        await notify_admins_about_order(order_id)
        await notify_suppliers_about_order(order_id)
    else:
        await message.answer(f"❌ Не удалось оформить заказ: {error}")

@client_router.callback_query(F.data == "clear_cart")
async def clear_user_cart(callback: CallbackQuery):
    clear_cart(callback.from_user.id)
    await callback.message.answer("🗑️ Корзина очищена")
    await callback.answer()

@client_router.message(F.text == "📝 Мои заказы")
async def handle_orders(message: types.Message):
    orders = get_user_orders(message.from_user.id)
    
    if not orders:
        await message.answer("📭 У вас пока нет заказов")
        return
    
    builder = InlineKeyboardBuilder()
    for order in orders:
        order_id, total, status, created_at, is_recurring, recurring_type, next_delivery = order
        status_text = ORDER_STATUSES.get(status, status)
        recurring_text = " 🔄" if is_recurring else ""
        builder.add(types.InlineKeyboardButton(
            text=f"Заказ #{order_id} - {total} руб. ({status_text}){recurring_text}",
            callback_data=f"order_details_{order_id}")
        )
    
    await message.answer(
        "📋 Ваши заказы:",
        reply_markup=builder.as_markup()
    )

@client_router.message(F.text == "🔄 Регулярные заказы")
async def handle_recurring_orders(message: types.Message):
    orders = get_user_orders(message.from_user.id)
    
    if not orders:
        await message.answer("📭 У вас пока нет заказов")
        return
    
    recurring_orders = [order for order in orders if order[4]]  # is_recurring
    
    if not recurring_orders:
        await message.answer("🔄 У вас пока нет регулярных заказов")
        return
    
    text = "🔄 Ваши регулярные заказы:\n\n"
    for order in recurring_orders:
        order_id, total, status, created_at, is_recurring, recurring_type, next_delivery = order
        status_text = ORDER_STATUSES.get(status, status)
        text += (
            f"▪️ <b>Заказ #{order_id}</b>\n"
            f"  - Тип: {RECURRING_TYPES.get(recurring_type, recurring_type)}\n"
            f"  - Следующая доставка: {next_delivery}\n"
            f"  - Статус: {status_text}\n"
            f"  - Сумма: {total} руб.\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")

@client_router.callback_query(F.data.startswith("order_details_"))
async def show_order_details(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order, items = get_order_details(order_id)
    
    if not order:
        await callback.message.answer("❌ Заказ не найден")
        await callback.answer()
        return
    
    _, customer_id, total, status, created_at, is_recurring, recurring_type, next_delivery, parent_order_id = order
    status_text = ORDER_STATUSES.get(status, status)
    
    order_text = (
        f"📦 <b>Заказ #{order_id}</b>\n"
        f"💳 Сумма: <b>{total} руб.</b>\n"
        f"📮 Статус: <b>{status_text}</b>\n"
        f"📅 Дата создания: <b>{created_at}</b>\n"
    )
    
    if is_recurring:
        order_text += (
            f"🔄 Тип: <b>{RECURRING_TYPES.get(recurring_type, recurring_type)}</b>\n"
            f"📅 Следующая доставка: <b>{next_delivery}</b>\n"
        )
    
    order_text += "\n🛒 Состав заказа:\n"
    
    for item in items:
        name, quantity, price = item
        order_text += f"▪️ {name} - {quantity} шт. x {price} руб.\n"
    
    await callback.message.edit_text(
        order_text,
        parse_mode="HTML"
    )
    await callback.answer()

@client_router.message(F.text == "❓ Помощь")
async def handle_help(message: types.Message):
    await message.answer(
        "Выберите раздел помощи:",
        reply_markup=help_keyboard()
    )

@client_router.callback_query(F.data == "faq")
async def show_client_faq(callback: CallbackQuery):
    faq_text = (
        "❓ <b>Часто задаваемые вопросы (Покупатель):</b>\n\n"
        "1. <b>Как сделать заказ?</b>\n"
        "   - Выберите товары в каталоге, добавьте в корзину и оформите заказ.\n\n"
        "2. <b>Как отменить заказ?</b>\n"
        "   - Отменить заказ можно только до его подтверждения. Свяжитесь с нами.\n\n"
        "3. <b>Как оформить регулярную доставку?</b>\n"
        "   - При добавлении товара в корзину выберите опцию регулярного заказа.\n\n"
        "4. <b>Как изменить адрес доставки?</b>\n"
        "   - В корзине при оформлении заказа вы можете ввести новый адрес.\n"
    )
    await callback.message.edit_text(faq_text, parse_mode="HTML")

@client_router.callback_query(F.data == "ask_question")
async def ask_question(callback: CallbackQuery):
    await callback.message.answer(
        "Если у вас остались вопросы, напишите нам: @Restiify",
        disable_web_page_preview=True
    )

@client_router.callback_query(F.data == "product_search")
async def start_product_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔍 Введите поисковый запрос:")
    await state.set_state(SearchForm.query)
    await callback.answer()

@client_router.message(SearchForm.query)
async def process_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("❌ Запрос не может быть пустым. Введите текст для поиска.")
        return
    
    products = search_products(query)
    
    if not products:
        await message.answer("😔 По вашему запросу ничего не найдено.")
        await state.clear()
        return
    
    builder = InlineKeyboardBuilder()
    for product in products:
        product_id, name, price, in_stock, quantity = product
        stock_text = "✅ В наличии" if in_stock else "❌ Нет в наличии"
        builder.add(types.InlineKeyboardButton(
            text=f"{name} - {price} руб. ({stock_text})",
            callback_data=f"product_{product_id}")
        )
    
    builder.row(types.InlineKeyboardButton(
        text="🔙 Назад в каталог",
        callback_data="back_to_main_categories")
    )
    
    await message.answer(
        f"🔍 Результаты поиска по запросу '{query}':",
        reply_markup=builder.as_markup()
    )
    await state.clear()

@client_router.message(F.text == "👤 Профиль")
async def handle_client_profile(message: types.Message):
    """Показать профиль клиента с возможностью редактирования"""
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Профиль не найден")
        return
    
    _, _, name, role, company, phone, address, _ = user
    
    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"🏢 <b>Компания:</b> {company}\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📱 <b>Телефон:</b> {phone}\n"
        f"🏠 <b>Адрес доставки:</b> {address}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="✏️ Редактировать",
        callback_data="client_edit_profile")
    )
    
    await message.answer(
        profile_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@client_router.callback_query(F.data == "client_edit_profile")
async def start_client_edit_profile(callback: CallbackQuery, state: FSMContext):
    """Начать процесс редактирования профиля клиента"""
    await callback.message.answer("✏️ Введите новое имя или название компании:")
    await state.set_state(EditProfile.name)
    await callback.answer()

@client_router.message(EditProfile.name)
async def process_client_edit_name(message: types.Message, state: FSMContext):
    """Обработать новое имя клиента"""
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("❌ Слишком длинное имя (макс. 100 символов). Введите снова:")
        return
    
    await state.update_data(name=name)
    await message.answer("📱 Введите новый номер телефона:")
    await state.set_state(EditProfile.phone)

@client_router.message(EditProfile.phone)
async def process_client_edit_phone(message: types.Message, state: FSMContext):
    """Обработать новый телефон клиента"""
    phone = message.text.strip()
    if not PHONE_REGEX.match(phone):
        await message.answer("❌ Неверный формат телефона. Введите снова:")
        return
    
    await state.update_data(phone=phone)
    await message.answer("🏠 Введите новый адрес доставки:")
    await state.set_state(EditProfile.address)

@client_router.message(EditProfile.address)
async def process_client_edit_address(message: types.Message, state: FSMContext):
    """Обработать новый адрес клиента и сохранить изменения"""
    address = message.text.strip()
    if len(address) > 200:
        await message.answer("❌ Слишком длинный адрес (макс. 200 символов). Введите снова:")
        return
    
    data = await state.get_data()
    update_user(
        tg_id=message.from_user.id,
        name=data.get('name', message.from_user.full_name),
        phone=data.get('phone'),
        address=address
    )
    await state.clear()
    await message.answer("✅ Профиль успешно обновлен!")
    await handle_client_profile(message)  # Показать обновленный профиль

# ====================== БОТ ПОСТАВЩИКА ======================
supplier_router = Router()

@supplier_router.message(Command("start"))
async def supplier_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if user and user[5] and user[6]:  # Если уже есть телефон и адрес
        await show_supplier_menu(message)
    else:
        add_user(message.from_user.id, message.from_user.full_name, "supplier", "Unknown")
        await message.answer("🏭 Добро пожаловать! Для регистрации введите ваше имя или название компании:", 
                            reply_markup=ReplyKeyboardRemove())
        await state.set_state(SupplierRegistration.name)

async def show_supplier_menu(message: types.Message):
    await message.answer(
        "🏭 Добро пожаловать, поставщик!\nВыберите действие:",
        reply_markup=supplier_keyboard()
    )

@supplier_router.message(SupplierRegistration.name)
async def process_supplier_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("❌ Слишком длинное имя (макс. 100 символов). Введите снова:")
        return
    
    await state.update_data(name=name)
    await message.answer("📱 Введите ваш номер телефона:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SupplierRegistration.phone)

@supplier_router.message(SupplierRegistration.phone)
async def process_supplier_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_REGEX.match(phone):
        await message.answer("❌ Неверный формат телефона. Введите снова:")
        return
    
    await state.update_data(phone=phone)
    await message.answer("🏠 Введите ваш адрес (для забора товаров):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SupplierRegistration.address)

@supplier_router.message(SupplierRegistration.address)
async def process_supplier_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) > 200:
        await message.answer("❌ Слишком длинный адрес (макс. 200 символов). Введите снова:")
        return
    
    data = await state.get_data()
    update_user(
        tg_id=message.from_user.id,
        name=data.get('name', message.from_user.full_name),
        phone=data.get('phone'),
        address=address
    )
    await state.clear()
    await show_supplier_menu(message)

@supplier_router.message(F.text == "👤 Профиль")
async def handle_profile(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Профиль не найден")
        return
    
    _, _, name, role, company, phone, address, _ = user
    
    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"🏢 <b>Компания:</b> {company}\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📱 <b>Телефон:</b> {phone}\n"
        f"🏠 <b>Адрес:</b> {address}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="✏️ Редактировать",
        callback_data="edit_profile")
    )
    
    await message.answer(
        profile_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@supplier_router.callback_query(F.data == "edit_profile")
async def start_edit_profile(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Введите новое имя или название компании:")
    await state.set_state(EditProfile.name)
    await callback.answer()

@supplier_router.message(EditProfile.name)
async def process_edit_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("❌ Слишком длинное имя (макс. 100 символов). Введите снова:")
        return
    
    await state.update_data(name=name)
    await message.answer("📱 Введите новый номер телефона:")
    await state.set_state(EditProfile.phone)

@supplier_router.message(EditProfile.phone)
async def process_edit_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_REGEX.match(phone):
        await message.answer("❌ Неверный формат телефона. Введите снова:")
        return
    
    await state.update_data(phone=phone)
    await message.answer("🏠 Введите новый адрес:")
    await state.set_state(EditProfile.address)

@supplier_router.message(EditProfile.address)
async def process_edit_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) > 200:
        await message.answer("❌ Слишком длинный адрес (макс. 200 символов). Введите снова:")
        return
    
    data = await state.get_data()
    update_user(
        tg_id=message.from_user.id,
        name=data.get('name', message.from_user.full_name),
        phone=data.get('phone'),
        address=address
    )
    await state.clear()
    await message.answer("✅ Профиль успешно обновлен!")
    await handle_profile(message)

@supplier_router.message(F.text == "➕ Добавить товар")
async def handle_add_product(message: types.Message, state: FSMContext):
    await message.answer("📝 Введите название товара (макс. 100 символов):")
    await state.set_state(ProductForm.name)

@supplier_router.message(ProductForm.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("❌ Слишком длинное название (макс. 100 символов). Введите снова:")
        return
    
    await state.update_data(name=name)
    await message.answer("📄 Введите описание товара (макс. 500 символов):")
    await state.set_state(ProductForm.description)

@supplier_router.message(ProductForm.description)
async def process_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if len(description) > 500:
        await message.answer("❌ Слишком длинное описание (макс. 500 символов). Введите снова:")
        return
    
    await state.update_data(description=description)
    await message.answer("💰 Введите цену товара (число):")
    await state.set_state(ProductForm.price)

@supplier_router.message(ProductForm.price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        supplier_price = float(message.text)
        if supplier_price <= 0:
            await message.answer("❌ Цена должна быть положительным числом. Введите снова:")
            return
        
        await state.update_data(price=supplier_price)
        await message.answer("📦 Введите количество товара на складе:")
        await state.set_state(ProductForm.quantity)
        
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите число:")

@supplier_router.message(ProductForm.quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity < 0:
            await message.answer("❌ Количество не может быть отрицательным. Введите снова:")
            return
        
        await state.update_data(quantity=quantity)
        
        # Показываем основные категории для выбора
        categories = get_categories()  # Основные категории
        
        if not categories:
            await message.answer("❌ Нет доступных категорий. Обратитесь к администратору.")
            await state.clear()
            return
        
        builder = InlineKeyboardBuilder()
        for cat_id, cat_name in categories:
            builder.add(types.InlineKeyboardButton(
                text=cat_name,
                callback_data=f"select_main_category_{cat_id}")
            )
        builder.adjust(2)
        
        await message.answer("📚 Выберите основную категорию товара:", reply_markup=builder.as_markup())
        await state.set_state(ProductForm.category)
        
    except ValueError:
        await message.answer("❌ Неверный формат количества. Введите целое число:")

@supplier_router.callback_query(F.data.startswith("select_main_category_"))
async def select_main_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора основной категории"""
    try:
        main_category_id = int(callback.data.split("_")[3])
        
        # Сохраняем ID основной категории в состоянии
        await state.update_data(main_category_id=main_category_id)
        
        # Получаем подкатегории для выбранной основной категории
        subcategories = get_categories(parent_id=main_category_id)
        
        if not subcategories:
            # Если нет подкатегорий, сразу переходим к завершению
            data = await state.get_data()
            await state.update_data(category_id=main_category_id)
            await complete_product_add(callback, state)
            return
        
        builder = InlineKeyboardBuilder()
        for cat_id, cat_name in subcategories:
            builder.add(types.InlineKeyboardButton(
                text=cat_name,
                callback_data=f"select_subcategory_{cat_id}")
            )
        builder.adjust(2)
        
        await callback.message.answer("📚 Выберите подкатегорию товара:", reply_markup=builder.as_markup())
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе категории: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при выборе категории")
        await callback.answer()

@supplier_router.callback_query(F.data.startswith("select_subcategory_"))
async def select_subcategory(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подкатегории"""
    try:
        subcategory_id = int(callback.data.split("_")[2])
        
        # Сохраняем ID подкатегории в состоянии
        await state.update_data(category_id=subcategory_id)
        await complete_product_add(callback, state)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе подкатегории: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при выборе подкатегории")
        await callback.answer()

async def complete_product_add(callback: CallbackQuery, state: FSMContext):
    """Завершение добавления товара"""
    try:
        data = await state.get_data()
        category_id = data.get('category_id')
        supplier_price = data.get('price')
        quantity = data.get('quantity', 0)
        
        # Добавляем товар без подтверждения
        product_id = add_product(
            name=data['name'],
            description=data['description'],
            supplier_price=supplier_price,
            category_id=category_id,
            supplier_id=callback.from_user.id,
            quantity=quantity,
            approved=False
        )
        
        # Уведомление поставщику
        await callback.message.answer(
            "⏳ Ваш товар отправлен на модерацию. "
            "Дождитесь подтверждения администратора."
        )
        
        # Уведомление администраторам
        await notify_admins_about_product(product_id)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара: {str(e)}")
        await callback.message.answer("❌ Произошла ошибка при добавлении товара")

@supplier_router.message(F.text == "📦 Мои товары")
async def handle_products(message: types.Message):
    try:
        products = get_supplier_products(message.from_user.id)
        
        if not products:
            await message.answer("📭 У вас пока нет товаров")
            return
        
        builder = InlineKeyboardBuilder()
        for product in products:
            product_id, name, supplier_price, approved, in_stock, quantity = product
            status_icon = "✅" if approved else "⏳"
            stock_icon = "🟢" if in_stock else "🔴"
            # Отображаем только supplier_price для поставщика
            builder.add(types.InlineKeyboardButton(
                text=f"{status_icon}{stock_icon} {name} - {supplier_price} руб. ({quantity} шт.)",
                callback_data=f"edit_product_{product_id}")
            )
        builder.adjust(1)
        
        await message.answer(
            "📋 Ваши товары:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении товаров: {str(e)}")

@supplier_router.callback_query(F.data.startswith("edit_product_"))
async def edit_product_menu(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    product = get_product_details(product_id)
    
    if not product:
        await callback.answer("Товар не найден")
        return
    
    # Сохраняем product_id в состоянии
    await state.update_data(product_id=product_id)
    
    # Формируем текст товара
    name = product[1]
    supplier_price = product[3]
    approved = product[7]
    in_stock = product[9]
    quantity = product[10]
    
    status_text = "✅ Одобрен" if approved else "⏳ На модерации"
    stock_text = "🟢 В наличии" if in_stock else "🔴 Нет в наличии"
    
    text = (
        f"📦 <b>{name}</b>\n\n"
        f"💰 <b>Цена поставщика:</b> {supplier_price} руб.\n"
        f"📊 <b>Количество:</b> {quantity} шт.\n"
        f"📌 <b>Статус:</b> {status_text}\n"
        f"🛒 <b>Наличие:</b> {stock_text}\n\n"
        "Выберите действие:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="✏️ Редактировать",
        callback_data=f"edit_item_{product_id}"))
    builder.add(types.InlineKeyboardButton(
        text="🔄 Изменить наличие",
        callback_data=f"toggle_stock_{product_id}"))
    builder.add(types.InlineKeyboardButton(
        text="🗑️ Удалить",
        callback_data=f"delete_item_{product_id}"))
    builder.add(types.InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="back_to_products"))
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@supplier_router.callback_query(F.data.startswith("toggle_stock_"))
async def toggle_product_stock_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    in_stock = toggle_product_stock(product_id)
    await callback.answer(f"Наличие изменено: {'В наличии' if in_stock else 'Нет в наличии'}")
    await edit_product_menu(callback, None)  # Обновляем меню

@supplier_router.callback_query(F.data.startswith("edit_item_"))
async def choose_edit_field(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.update_data(product_id=product_id)
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Название", callback_data="edit_name"))
    builder.add(types.InlineKeyboardButton(text="Описание", callback_data="edit_description"))
    builder.add(types.InlineKeyboardButton(text="Цена", callback_data="edit_price"))
    builder.add(types.InlineKeyboardButton(text="Количество", callback_data="edit_quantity"))
    builder.add(types.InlineKeyboardButton(text="Категория", callback_data="edit_category"))
    builder.add(types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_product_{product_id}"))
    builder.adjust(2)
    
    await callback.message.edit_text(
        "Что вы хотите изменить?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@supplier_router.callback_query(F.data == "edit_name")
async def edit_product_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите новое название товара (макс. 100 символов):")
    await state.set_state(EditProduct.name)
    await callback.answer()

@supplier_router.message(EditProduct.name)
async def process_edit_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 100:
        await message.answer("❌ Слишком длинное название (макс. 100 символов). Введите снова:")
        return
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    # Обновляем название
    update_product(product_id, name=name)
    
    # Уведомляем администратора
    await notify_admins_about_product(product_id)
    
    await message.answer("✅ Название обновлено! Товар снова отправлен на модерацию.")
    await state.clear()

@supplier_router.callback_query(F.data == "edit_description")
async def edit_product_description(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📄 Введите новое описание товара (макс. 500 символов):")
    await state.set_state(EditProduct.description)
    await callback.answer()

@supplier_router.message(EditProduct.description)
async def process_edit_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if len(description) > 500:
        await message.answer("❌ Слишком длинное описание (макс. 500 символов). Введите снова:")
        return
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product(product_id, description=description)
    
    await notify_admins_about_product(product_id)
    await message.answer("✅ Описание обновлено! Товар снова отправлен на модерацию.")
    await state.clear()

@supplier_router.callback_query(F.data == "edit_price")
async def edit_product_price(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Введите новую цену товара:")
    await state.set_state(EditProduct.price)
    await callback.answer()

@supplier_router.message(EditProduct.price)
async def process_edit_price(message: types.Message, state: FSMContext):
    try:
        new_price = float(message.text)
        if new_price <= 0:
            await message.answer("❌ Цена должна быть положительным числом. Введите снова:")
            return
        
        data = await state.get_data()
        product_id = data.get('product_id')
        
        # Обновляем цену
        update_product(product_id, supplier_price=new_price)
        
        await notify_admins_about_product(product_id)
        await message.answer("✅ Цена обновлена! Товар снова отправлен на модерацию.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите число:")

@supplier_router.callback_query(F.data == "edit_quantity")
async def edit_product_quantity(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📦 Введите новое количество товара на складе:")
    await state.set_state(EditProduct.quantity)
    await callback.answer()

@supplier_router.message(EditProduct.quantity)
async def process_edit_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity < 0:
            await message.answer("❌ Количество не может быть отрицательным. Введите снова:")
            return
        
        data = await state.get_data()
        product_id = data.get('product_id')
        
        # Обновляем количество
        update_product(product_id, quantity=quantity)
        
        await notify_admins_about_product(product_id)
        await message.answer("✅ Количество обновлено! Товар снова отправлен на модерацию.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат количества. Введите целое число:")

@supplier_router.callback_query(F.data == "edit_category")
async def edit_product_category(callback: CallbackQuery, state: FSMContext):
    # Показываем основные категории
    categories = get_categories()
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in categories:
        builder.add(types.InlineKeyboardButton(text=cat_name, callback_data=f"select_edit_main_category_{cat_id}"))
    builder.adjust(2)
    await callback.message.answer("Выберите основную категорию товара:", reply_markup=builder.as_markup())
    await callback.answer()

@supplier_router.callback_query(F.data.startswith("select_edit_main_category_"))
async def select_edit_main_category(callback: CallbackQuery, state: FSMContext):
    main_category_id = int(callback.data.split("_")[4])
    await state.update_data(main_category_id=main_category_id)
    
    subcategories = get_categories(parent_id=main_category_id)
    if not subcategories:
        # Если нет подкатегорий, то выбираем основную категорию
        data = await state.get_data()
        product_id = data.get('product_id')
        # Обновляем категорию товара
        update_product(product_id, category_id=main_category_id)
        
        await callback.message.answer("✅ Категория обновлена! Товар снова отправлен на модерацию.")
        await state.clear()
        await notify_admins_about_product(product_id)
        return
    
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in subcategories:
        builder.add(types.InlineKeyboardButton(text=cat_name, callback_data=f"select_edit_subcategory_{cat_id}"))
    builder.adjust(2)
    await callback.message.answer("Выберите подкатегорию товара:", reply_markup=builder.as_markup())
    await callback.answer()

@supplier_router.callback_query(F.data.startswith("select_edit_subcategory_"))
async def select_edit_subcategory(callback: CallbackQuery, state: FSMContext):
    subcategory_id = int(callback.data.split("_")[4])
    data = await state.get_data()
    product_id = data.get('product_id')
    
    # Обновляем категорию
    update_product(product_id, category_id=subcategory_id)
    
    await callback.message.answer("✅ Категория обновлена! Товар снова отправлен на модерацию.")
    await state.clear()
    await notify_admins_about_product(product_id)
    await callback.answer()

@supplier_router.callback_query(F.data.startswith("delete_item_"))
async def delete_product_confirm(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="✅ Да",
        callback_data=f"confirm_delete_{product_id}")
    )
    builder.add(types.InlineKeyboardButton(
        text="❌ Нет",
        callback_data=f"edit_product_{product_id}")
    )
    
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этот товар?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@supplier_router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_product_execute(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    await callback.message.answer("🗑️ Товар удален!")
    await callback.answer()
    # Возвращаемся к списку товаров
    await handle_products(callback.message)

@supplier_router.callback_query(F.data == "back_to_products")
async def back_to_products(callback: CallbackQuery):
    await handle_products(callback.message)
    await callback.answer()

@supplier_router.message(F.text == "📋 Мои заказы")
async def handle_supplier_orders(message: types.Message):
    try:
        order_ids = get_supplier_orders(message.from_user.id)
        if not order_ids:
            await message.answer("📭 У вас пока нет заказов")
            return
        
        builder = InlineKeyboardBuilder()
        for order_id in order_ids:
            builder.add(types.InlineKeyboardButton(
                text=f"Заказ #{order_id}",
                callback_data=f"supplier_order_{order_id}")
            )
        
        await message.answer(
            "📋 Ваши заказы:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении заказов: {str(e)}")

@supplier_router.callback_query(F.data.startswith("supplier_order_"))
async def handle_supplier_order_details(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split("_")[2])
        items = get_supplier_order_items(order_id, callback.from_user.id)
        
        if not items:
            await callback.message.answer("❌ Заказ не найден")
            return
        
        status_info = get_supplier_order_status(order_id, callback.from_user.id)
        status = status_info[0] if status_info else "pending"
        problem = status_info[1] if status_info else None
        
        status_text = {
            'pending': "ожидает обработки",
            'ready': "готов к передаче",
            'problem': "есть проблемы"
        }.get(status, status)
        
        text = (
            f"📦 <b>Заказ #{order_id}</b>\n"
            f"📮 Статус: <b>{status_text}</b>\n"
        )
        
        if problem:
            text += f"⚠️ Проблема: {problem}\n"
        
        text += "\n🛒 Ваши товары в заказе:\n"
        
        for item in items:
            name, quantity, price = item
            # Для поставщика показываем supplier_price
            text += f"▪️ {name} - {quantity} шт. x {price} руб.\n"
        
        builder = InlineKeyboardBuilder()
        if status != 'ready':
            builder.add(types.InlineKeyboardButton(
                text="✅ Подтвердить готовность",
                callback_data=f"supplier_ready_{order_id}")
            )
        if status != 'problem':
            builder.add(types.InlineKeyboardButton(
                text="❌ Сообщить о проблеме",
                callback_data=f"supplier_problem_{order_id}")
            )
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup() if builder.buttons else None
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при загрузке заказа: {str(e)}")
    finally:
        await callback.answer()

@supplier_router.callback_query(F.data.startswith("supplier_ready_"))
async def handle_supplier_ready(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    update_supplier_status(order_id, callback.from_user.id, "ready")
    await callback.message.answer("✅ Статус обновлен: Товар готов к передаче")
    await notify_admin_about_supplier_status(order_id, callback.from_user.id, "ready")
    await callback.answer()

@supplier_router.callback_query(F.data.startswith("supplier_problem_"))
async def handle_supplier_problem(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    await state.update_data(order_id=order_id)
    await callback.message.answer("📝 Опишите проблему с товаром:")
    await state.set_state(SupplierProblem.description)
    await callback.answer()

@supplier_router.message(SupplierProblem.description)
async def process_problem_description(message: types.Message, state: FSMContext):
    problem = message.text.strip()
    if len(problem) > 500:
        await message.answer("❌ Слишком длинное описание (макс. 500 символов). Введите снова:")
        return
    
    data = await state.get_data()
    order_id = data.get('order_id')
    
    update_supplier_status(order_id, message.from_user.id, "problem", problem)
    await message.answer("✅ Проблема зафиксирована. Администратор уведомлен.")
    await notify_admin_about_supplier_status(order_id, message.from_user.id, "problem", problem)
    await state.clear()

@supplier_router.message(F.text == "❓ Помощь")
async def handle_help(message: types.Message):
    await message.answer(
        "Выберите раздел помощи:",
        reply_markup=help_keyboard()
    )

@supplier_router.callback_query(F.data == "faq")
async def show_supplier_faq(callback: CallbackQuery):
    faq_text = (
        "❓ <b>Часто задаваемые вопросы (Поставщик):</b>\n\n"
        "1. <b>Как добавить товар?</b>\n"
        "   - Используйте кнопку 'Добавить товар'. Заполните данные и отправьте на модерацию.\n\n"
        "2. <b>Сколько времени занимает модерация товара?</b>\n"
        "   - Обычно до 24 часов. В случае задержки свяжитесь с администратором.\n\n"
        "3. <b>Как узнать статус заказа?</b>\n"
        "   - В разделе 'Мои заказы' вы можете отслеживать статус заказов с вашими товарами.\n\n"
        "4. <b>Как изменить данные профиля?</b>\n"
        "   - В разделе 'Профиль' нажмите 'Редактировать'.\n"
    )
    await callback.message.edit_text(faq_text, parse_mode="HTML")

@supplier_router.callback_query(F.data == "ask_question")
async def ask_question(callback: CallbackQuery):
    await callback.message.answer(
        "Если у вас остались вопросы, напишите нам: @Restiify",
        disable_web_page_preview=True
    )

# ====================== АДМИН БОТ ======================
admin_router = Router()

@admin_router.message(Command("start"))
async def admin_start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('b2b.db')
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE tg_id = ?", (message.from_user.id,))
    user = cur.fetchone()
    conn.close()
    
    if user and user[0] == "admin":
        await show_admin_menu(message)
    else:
        await message.answer("🔒 Введите пароль администратора:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminAuth.password)

@admin_router.message(AdminAuth.password)
async def check_admin_password(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        add_user(message.from_user.id, message.from_user.full_name, "admin", "System")
        await message.answer("✅ Успешная аутентификация! Доступ разрешен.")
        await show_admin_menu(message)
    else:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз или отправьте /start для отмены")
    
    await state.clear()

async def show_admin_menu(message: types.Message):
    await message.answer(
        "👑 Административная панель\nВыберите раздел:",
        reply_markup=admin_keyboard()
    )

@admin_router.message(F.text == "🆕 Запросы на размещение")
async def handle_pending_products(message: types.Message):
    try:
        products = get_pending_products()
        
        if not products:
            await message.answer("✅ Нет товаров, ожидающих подтверждения.")
            return
        
        for product in products:
            (product_id, name, description, supplier_price, final_price, 
             category_id, supplier_id, approved, status, in_stock, quantity, created_at) = product
            
            supplier = get_user_by_id(supplier_id)
            supplier_name = supplier[2] if supplier else "Неизвестный поставщик"
            company = supplier[4] if supplier else ""
            
            # Получаем название категории
            conn = sqlite3.connect('b2b.db')
            cur = conn.cursor()
            cur.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
            category_name = cur.fetchone()
            conn.close()
            category_name = category_name[0] if category_name else "Без категории"
            
            text = (
                "🆕 <b>ТОВАР НА МОДЕРАЦИИ</b>\n\n"
                f"🆔 <b>Товар #{product_id}</b>\n"
                f"📦 <b>Название:</b> {name}\n"
                f"📝 <b>Описание:</b> {description}\n"
                f"💰 <b>Цена поставщика:</b> {supplier_price} руб.\n"
                f"💰 <b>Итоговая цена:</b> {final_price} руб.\n"
                f"📚 <b>Категория:</b> {category_name}\n"
                f"🏭 <b>Поставщик:</b> {supplier_name} ({company})\n"
                f"📦 <b>Количество:</b> {quantity} шт.\n"
                f"🟢 <b>В наличии:</b> {'Да' if in_stock else 'Нет'}\n"
            )
            
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin_approve_{product_id}")
            )
            builder.add(types.InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"admin_reject_{product_id}")
            )
            
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
        
        await message.answer("Все товары на модерации показаны.")
    except Exception as e:
        logger.error(f"Ошибка при показе ожидающих товаров: {str(e)}")
        await message.answer("❌ Произошла ошибка при загрузке запросов")

@admin_router.message(F.text == "📊 Статистика")
async def handle_statistics(message: types.Message):
    try:
        conn = sqlite3.connect('b2b.db')
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
        customers = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'supplier'")
        suppliers = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*), SUM(total_amount) FROM orders")
        orders_count, orders_total = cur.fetchone()
        orders_total = orders_total or 0
        
        cur.execute("SELECT COUNT(*) FROM products")
        products_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM products WHERE approved = 0")
        pending_products = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM orders WHERE is_recurring = 1")
        recurring_orders = cur.fetchone()[0]
        
        # Товары с низким остатком
        cur.execute("SELECT COUNT(*) FROM products WHERE quantity <= 10 AND quantity > 0")
        low_stock = cur.fetchone()[0]
        
        # Товары отсутствующие
        cur.execute("SELECT COUNT(*) FROM products WHERE quantity = 0 AND in_stock = 1")
        out_of_stock = cur.fetchone()[0]
        
        conn.close()
        
        stats_text = (
            "📊 <b>Статистика платформы</b>\n\n"
            f"👥 Пользователи: <b>{total_users}</b>\n"
            f"  ▪️ Покупатели: <b>{customers}</b>\n"
            f"  ▪️ Поставщики: <b>{suppliers}</b>\n\n"
            f"📦 Заказы: <b>{orders_count}</b>\n"
            f"  ▪️ Общая сумма: <b>{orders_total:.2f} руб.</b>\n"
            f"  ▪️ Регулярные: <b>{recurring_orders}</b>\n\n"
            f"🛒 Товары: <b>{products_count}</b>\n"
            f"  ▪️ Ожидают подтверждения: <b>{pending_products}</b>\n"
            f"  ▪️ Низкий остаток (<10): <b>{low_stock}</b>\n"
            f"  ▪️ Отсутствуют: <b>{out_of_stock}</b>"
        )
        
        await message.answer(
            stats_text,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка статистики: {str(e)}")

@admin_router.message(F.text == "👥 Пользователи")
async def handle_users(message: types.Message):
    try:
        users = get_all_users()
        if not users:
            await message.answer("😔 Пользователи не найдены")
            return
        
        users_text = "👥 <b>Список пользователей</b>\n\n"
        for user in users:
            tg_id, name, role, company, phone, address = user
            role_icon = "👤" if role == "customer" else "🏭" if role == "supplier" else "👑"
            users_text += f"{role_icon} <b>{name}</b>\n"
            users_text += f"  ▪️ Роль: {role}\n"
            users_text += f"  ▪️ Компания: {company}\n"
            users_text += f"  ▪️ Телефон: {phone}\n"
            users_text += f"  ▪️ Адрес: {address}\n\n"
        
        await message.answer(
            users_text,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка пользователей: {str(e)}")

@admin_router.message(F.text == "📦 Заказы")
async def handle_orders(message: types.Message):
    try:
        orders = get_all_orders()
        if not orders:
            await message.answer("📭 Заказов пока нет")
            return
        
        builder = InlineKeyboardBuilder()
        for order in orders:
            order_id, _, _, status = order
            builder.add(types.InlineKeyboardButton(
                text=f"Заказ #{order_id} ({ORDER_STATUSES.get(status, status)})",
                callback_data=f"admin_order_{order_id}")
            )
        
        await message.answer(
            "📦 Список заказов:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка заказов: {str(e)}")

@admin_router.callback_query(F.data.startswith("admin_order_"))
async def handle_admin_order(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split("_")[2])
        order, items = get_order_details(order_id)
        
        if not order:
            await callback.message.answer("❌ Заказ не найден")
            return
        
        _, customer_id, total, status, created_at, is_recurring, recurring_type, next_delivery, parent_order_id = order
        customer = get_user_by_id(customer_id)
        customer_name = customer[2] if customer else "Неизвестный"
        
        text = (
            f"📦 <b>Заказ #{order_id}</b>\n"
            f"👤 <b>Клиент:</b> {customer_name}\n"
            f"💳 <b>Сумма:</b> {total} руб.\n"
            f"📮 <b>Статус:</b> {ORDER_STATUSES.get(status, status)}\n"
            f"📅 <b>Дата:</b> {created_at}\n"
        )
        
        if is_recurring:
            text += (
                f"🔄 <b>Регулярный:</b> {RECURRING_TYPES.get(recurring_type, recurring_type)}\n"
                f"📅 <b>Следующая доставка:</b> {next_delivery}\n"
            )
        
        text += "\n🛒 <b>Состав заказа:</b>\n"
        
        for item in items:
            name, quantity, price = item
            text += f"▪️ {name} - {quantity} шт. x {price} руб.\n"
        
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=order_status_keyboard(order_id)
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при загрузке заказа: {str(e)}")
    finally:
        await callback.answer()

@admin_router.callback_query(F.data.startswith("set_status_"))
async def handle_set_status(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        order_id = int(parts[2])
        status = parts[3]
        
        update_order_status(order_id, status)
        await callback.message.answer(f"✅ Статус заказа #{order_id} изменен на {ORDER_STATUSES.get(status, status)}")
        
        # Уведомляем клиента об изменении статуса
        await notify_customer_about_status(order_id, status)
        
        # Если это регулярный заказ и статус "Доставлен", создаем следующий заказ
        if status == "delivered":
            conn = sqlite3.connect('b2b.db')
            cur = conn.cursor()
            cur.execute("SELECT is_recurring FROM orders WHERE id = ?", (order_id,))
            is_recurring = cur.fetchone()[0]
            conn.close()
            
            if is_recurring:
                new_order_id = create_recurring_order(order_id)
                if new_order_id:
                    await callback.message.answer(f"🔄 Создан следующий регулярный заказ #{new_order_id}")
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при обновлении статуса: {str(e)}")
    finally:
        await callback.answer()

@admin_router.message(F.text == "📚 Категории")
async def handle_categories(message: types.Message):
    try:
        categories = get_categories()
        if not categories:
            await message.answer("📚 Категорий пока нет")
            return
        
        categories_text = "📚 <b>Список категорий</b>\n\n"
        for category in categories:
            category_id, name = category
            categories_text += f"▪️ <b>{name}</b> (ID: {category_id})\n"
        
        await message.answer(
            categories_text,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка категорий: {str(e)}")

# Обработчики подтверждения/отклонения товаров
@admin_router.callback_query(F.data.startswith("admin_approve_"))
async def approve_product_handler(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[2])
        approve_product(product_id)
        
        # Получаем информацию о товаре и поставщике
        product = get_product_details(product_id)
        if product:
            supplier_id = product[6]
            product_name = product[1]
            
            # Уведомляем поставщика
            try:
                bot = Bot(token=SUPPLIER_TOKEN)
                await bot.send_message(
                    supplier_id,
                    f"✅ Ваш товар \"{product_name}\" был одобрен и теперь доступен в каталоге."
                )
                await bot.session.close()
            except Exception as e:
                logger.error(f"Ошибка при уведомлении поставщика: {str(e)}")
        
        # Удаляем сообщение с запросом
        await callback.message.delete()
        await callback.answer(f"✅ Товар #{product_id} успешно подтвержден!")
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении товара: {str(e)}")
        await callback.answer("❌ Произошла ошибка при подтверждении товара")

@admin_router.callback_query(F.data.startswith("admin_reject_"))
async def reject_product_handler(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[2])
        reject_product(product_id)
        
        # Получаем информацию о товаре и поставщике
        product = get_product_details(product_id)
        if product:
            supplier_id = product[6]
            product_name = product[1]
            
            # Уведомляем поставщика
            try:
                bot = Bot(token=SUPPLIER_TOKEN)
                await bot.send_message(
                    supplier_id,
                    f"❌ Ваш товар \"{product_name}\" был отклонен администратором."
                )
                await bot.session.close()
            except Exception as e:
                logger.error(f"Ошибка при уведомлении поставщика: {str(e)}")
        
        # Удаляем сообщение с запросом
        await callback.message.delete()
        await callback.answer(f"❌ Товар #{product_id} отклонен!")
        
    except Exception as e:
        logger.error(f"Ошибка при отклонении товара: {str(e)}")
        await callback.answer("❌ Произошла ошибка при отклонении товара")

# ====================== ЗАПУСК БОТОВ ======================
async def process_recurring_orders():
    """Создает новые заказы для регулярных подписок"""
    try:
        recurring_orders = get_recurring_orders()
        today = datetime.now().strftime("%Y-%m-%d")
        
        for order in recurring_orders:
            order_id, customer_id, recurring_type, next_delivery = order
            
            if next_delivery == today:
                # Создаем новый заказ на основе этого регулярного
                new_order_id = create_recurring_order(order_id)
                if new_order_id:
                    logger.info(f"Создан новый регулярный заказ #{new_order_id} на основе #{order_id}")
                    
                    # Уведомляем клиента
                    await notify_user(customer_id, f"🔄 Создан новый регулярный заказ #{new_order_id} на {next_delivery}")
                    
                    # Уведомляем администраторов
                    admins = get_admins()
                    for admin_id in admins:
                        await notify_user(admin_id, f"🔄 Создан регулярный заказ #{new_order_id} для клиента {customer_id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке регулярных заказов: {str(e)}")

async def send_order_reminders():
    """Отправляет напоминания о предстоящих заказах"""
    try:
        # Находим заказы, которые должны быть доставлены завтра
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        conn = sqlite3.connect('b2b.db')
        cur = conn.cursor()
        cur.execute("SELECT id, customer_id FROM orders WHERE next_delivery = ?", (tomorrow,))
        orders = cur.fetchall()
        conn.close()
        
        for order in orders:
            order_id, customer_id = order
            await notify_user(customer_id, f"⏰ Напоминание: завтра доставка вашего заказа #{order_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {str(e)}")

async def check_stock_levels():
    """Проверяет уровень запасов и отправляет уведомления"""
    try:
        # Товары с низким остатком
        low_stock_products = check_low_stock()
        for product in low_stock_products:
            product_id, name, quantity, supplier_id = product
            await notify_supplier_low_stock(supplier_id, product_id, name, quantity)
        
        # Товары, закончившиеся на складе
        out_of_stock_products = check_out_of_stock()
        for product in out_of_stock_products:
            product_id, name, supplier_id = product
            await notify_supplier_out_of_stock(supplier_id, product_id, name)
    except Exception as e:
        logger.error(f"Ошибка при проверке запасов: {str(e)}")

async def scheduler():
    """Планировщик для регулярных задач"""
    while True:
        now = datetime.now()
        
        # Каждый день в 8:00 обрабатываем регулярные заказы
        if now.hour == 8 and now.minute == 0:
            await process_recurring_orders()
        
        # Каждый день в 19:00 отправляем напоминания
        if now.hour == 19 and now.minute == 0:
            await send_order_reminders()
        
        # Каждый день в 10:00 проверяем уровень запасов
        if now.hour == 10 and now.minute == 0:
            await check_stock_levels()
        
        # Проверяем каждую минуту
        await asyncio.sleep(60)

async def main():
    client_bot = Bot(token=CLIENT_TOKEN)
    supplier_bot = Bot(token=SUPPLIER_TOKEN)
    admin_bot = Bot(token=ADMIN_TOKEN)
    
    client_dp = Dispatcher()
    supplier_dp = Dispatcher()
    admin_dp = Dispatcher()
    
    client_dp.include_router(client_router)
    supplier_dp.include_router(supplier_router)
    admin_dp.include_router(admin_router)
    
    # Запускаем планировщик в фоне
    asyncio.create_task(scheduler())
    
    await asyncio.gather(
        client_dp.start_polling(client_bot),
        supplier_dp.start_polling(supplier_bot),
        admin_dp.start_polling(admin_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())