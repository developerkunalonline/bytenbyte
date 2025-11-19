from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import json
from datetime import datetime
from functools import wraps
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

app = Flask(__name__)
app.secret_key = 'arun-chaudhary-canteen-project'

DATABASE = 'canteen.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS category (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT,
            FOREIGN KEY (category_id) REFERENCES category(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            items TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            datetime TEXT NOT NULL
        )
    ''')
    
    cursor.execute('SELECT * FROM admin WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO admin (username, password) VALUES (?, ?)', ('admin', 'admin123'))
    
    conn.commit()
    conn.close()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM category ORDER BY name')
    categories = cursor.fetchall()
    
    cursor.execute('''
        SELECT f.*, c.name as category_name 
        FROM food_item f 
        JOIN category c ON f.category_id = c.id
        ORDER BY c.name, f.name
    ''')
    items = cursor.fetchall()
    
    conn.close()
    
    return render_template('menu.html', categories=categories, items=items)

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    order_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO orders (customer_name, items, subtotal, tax, total, datetime)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get('customer_name', 'Guest'),
        json.dumps(data['items']),
        data['subtotal'],
        data['tax'],
        data['total'],
        order_datetime
    ))
    
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'order_id': order_id})

@app.route('/bill/<int:order_id>')
def bill(order_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    
    conn.close()
    
    if not order:
        return "Order not found", 404
    
    order_data = {
        'id': order['id'],
        'customer_name': order['customer_name'],
        'order_items': json.loads(order['items']),
        'subtotal': order['subtotal'],
        'tax': order['tax'],
        'total': order['total'],
        'datetime': order['datetime']
    }
    
    return render_template('bill.html', order=order_data)

@app.route('/download_bill/<int:order_id>')
def download_bill(order_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    
    conn.close()
    
    if not order:
        return "Order not found", 404
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a535c'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph("Canteen Order Invoice", title_style))
    elements.append(Spacer(1, 12))
    
    info_style = styles['Normal']
    elements.append(Paragraph(f"<b>Order ID:</b> #{order['id']}", info_style))
    elements.append(Paragraph(f"<b>Customer Name:</b> {order['customer_name']}", info_style))
    elements.append(Paragraph(f"<b>Date & Time:</b> {order['datetime']}", info_style))
    elements.append(Spacer(1, 20))
    
    items = json.loads(order['items'])
    table_data = [['Item', 'Qty', 'Price (₹)', 'Total (₹)']]
    
    for item in items:
        table_data.append([
            item['name'],
            str(item['quantity']),
            f"₹{item['price']:.2f}",
            f"₹{item['total']:.2f}"
        ])
    
    table_data.append(['', '', 'Subtotal:', f"₹{order['subtotal']:.2f}"])
    cgst = order['tax'] / 2
    sgst = order['tax'] / 2
    table_data.append(['', '', 'CGST (2.5%):', f"₹{cgst:.2f}"])
    table_data.append(['', '', 'SGST (2.5%):', f"₹{sgst:.2f}"])
    table_data.append(['', '', '<b>Grand Total:</b>', f"<b>₹{order['total']:.2f}</b>"])
    
    table = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4ecdc4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ff6b6b')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph("Thank you for your order!", footer_style))
    elements.append(Paragraph("Visit us again!", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'invoice_{order_id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin WHERE username = ? AND password = ?', (username, password))
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM category')
    total_categories = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM food_item')
    total_items = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM orders')
    total_orders = cursor.fetchone()['count']
    
    cursor.execute('SELECT * FROM food_item ORDER BY id DESC')
    recent_items = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_categories=total_categories,
                         total_items=total_items,
                         total_orders=total_orders,
                         recent_items=recent_items)

@app.route('/admin/add_category', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO category (name) VALUES (?)', (name,))
            conn.commit()
            conn.close()
            return redirect(url_for('admin_dashboard'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('add_category.html', error='Category already exists')
    
    return render_template('add_category.html')

@app.route('/admin/add_item', methods=['GET', 'POST'])
@admin_required
def add_item():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        name = request.form.get('name')
        price = request.form.get('price')
        image = request.form.get('image', '')
        
        cursor.execute('''
            INSERT INTO food_item (category_id, name, price, image)
            VALUES (?, ?, ?, ?)
        ''', (category_id, name, price, image))
        
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute('SELECT * FROM category ORDER BY name')
    categories = cursor.fetchall()
    conn.close()
    
    return render_template('add_item.html', categories=categories)

@app.route('/admin/edit_item/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def edit_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        name = request.form.get('name')
        price = request.form.get('price')
        image = request.form.get('image', '')
        
        cursor.execute('''
            UPDATE food_item 
            SET category_id = ?, name = ?, price = ?, image = ?
            WHERE id = ?
        ''', (category_id, name, price, image, item_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute('SELECT * FROM food_item WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    
    cursor.execute('SELECT * FROM category ORDER BY name')
    categories = cursor.fetchall()
    
    conn.close()
    
    return render_template('edit_item.html', item=item, categories=categories)

@app.route('/admin/delete_item/<int:item_id>')
@admin_required
def delete_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM food_item WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

def seed_data():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM category')
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return
    
    categories = ['Snacks', 'Drinks', 'Meals', 'Desserts']
    for cat in categories:
        cursor.execute('INSERT INTO category (name) VALUES (?)', (cat,))
    
    items = [
        (1, 'Samosa', 20, 'https://via.placeholder.com/300x200?text=Samosa'),
        (1, 'Pakora', 30, 'https://via.placeholder.com/300x200?text=Pakora'),
        (1, 'Spring Roll', 40, 'https://via.placeholder.com/300x200?text=Spring+Roll'),
        (1, 'Sandwich', 50, 'https://via.placeholder.com/300x200?text=Sandwich'),
        (2, 'Tea', 10, 'https://via.placeholder.com/300x200?text=Tea'),
        (2, 'Coffee', 15, 'https://via.placeholder.com/300x200?text=Coffee'),
        (2, 'Cold Drink', 20, 'https://via.placeholder.com/300x200?text=Cold+Drink'),
        (2, 'Fresh Juice', 40, 'https://via.placeholder.com/300x200?text=Fresh+Juice'),
        (3, 'Thali', 100, 'https://via.placeholder.com/300x200?text=Thali'),
        (3, 'Biryani', 120, 'https://via.placeholder.com/300x200?text=Biryani'),
        (3, 'Fried Rice', 80, 'https://via.placeholder.com/300x200?text=Fried+Rice'),
        (3, 'Noodles', 70, 'https://via.placeholder.com/300x200?text=Noodles'),
        (4, 'Ice Cream', 30, 'https://via.placeholder.com/300x200?text=Ice+Cream'),
        (4, 'Gulab Jamun', 25, 'https://via.placeholder.com/300x200?text=Gulab+Jamun'),
        (4, 'Cake Slice', 50, 'https://via.placeholder.com/300x200?text=Cake+Slice'),
    ]
    
    for item in items:
        cursor.execute('''
            INSERT INTO food_item (category_id, name, price, image)
            VALUES (?, ?, ?, ?)
        ''', item)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_data()
    app.run(debug=True)
