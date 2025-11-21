function getCart() {
    return JSON.parse(localStorage.getItem('cart') || '[]');
}

function saveCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCount();
}

function updateCartCount() {
    const cart = getCart();
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    const cartBadge = document.getElementById('cart-count');
    if (cartBadge) {
        cartBadge.textContent = totalItems;
        cartBadge.style.display = totalItems > 0 ? 'inline-block' : 'none';
    }
}

function addItemToCart(item) {
    let cart = getCart();
    
    const existingItem = cart.find(i => i.id === item.id);
    
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push(item);
    }
    
    saveCart(cart);
}

function removeItemFromCart(itemId) {
    let cart = getCart();
    cart = cart.filter(item => item.id !== itemId);
    saveCart(cart);
    renderCart();
}

function updateItemQuantity(itemId, newQuantity) {
    let cart = getCart();
    const item = cart.find(i => i.id === itemId);
    
    if (item) {
        if (newQuantity <= 0) {
            removeItemFromCart(itemId);
        } else {
            item.quantity = newQuantity;
            saveCart(cart);
            renderCart();
        }
    }
}

function calculateTotals() {
    const cart = getCart();
    
    const subtotal = cart.reduce((sum, item) => {
        return sum + (item.price * item.quantity);
    }, 0);
    
    const cgst = subtotal * 0.025; // 2.5%
    const sgst = subtotal * 0.025; // 2.5%
    const tax = cgst + sgst;
    const total = subtotal + tax;
    
    return { subtotal, cgst, sgst, tax, total };
}

function renderCart() {
    const cart = getCart();
    const cartItemsContainer = document.getElementById('cart-items');
    const emptyCartContainer = document.getElementById('empty-cart');
    
    if (cart.length === 0) {
        cartItemsContainer.style.display = 'none';
        emptyCartContainer.style.display = 'block';
        document.querySelector('.cart-summary').style.display = 'none';
        return;
    }
    
    cartItemsContainer.style.display = 'flex';
    emptyCartContainer.style.display = 'none';
    document.querySelector('.cart-summary').style.display = 'block';
    
    cartItemsContainer.innerHTML = cart.map(item => {
        const itemTotal = item.price * item.quantity;
        return `
            <div class="cart-item animate__animated animate__fadeInUp">
                <img src="${item.image || 'https://via.placeholder.com/100?text=' + item.name}" 
                     alt="${item.name}" 
                     class="cart-item-image">
                <div class="cart-item-details">
                    <h3 class="cart-item-name">${item.name}</h3>
                    <p class="cart-item-price">₹${item.price.toFixed(2)} each</p>
                    <div class="cart-item-controls">
                        <button class="qty-btn" onclick="updateItemQuantity('${item.id}', ${item.quantity - 1})">-</button>
                        <span class="qty-display">${item.quantity}</span>
                        <button class="qty-btn" onclick="updateItemQuantity('${item.id}', ${item.quantity + 1})">+</button>
                        <button class="remove-btn" onclick="removeItemFromCart('${item.id}')">Remove</button>
                    </div>
                </div>
                <div class="cart-item-total">
                    <strong>₹${itemTotal.toFixed(2)}</strong>
                </div>
            </div>
        `;
    }).join('');
    
    // Update summary
    const totals = calculateTotals();
    document.getElementById('subtotal').textContent = `₹${totals.subtotal.toFixed(2)}`;
    document.getElementById('cgst').textContent = `₹${totals.cgst.toFixed(2)}`;
    document.getElementById('sgst').textContent = `₹${totals.sgst.toFixed(2)}`;
    document.getElementById('total').textContent = `₹${totals.total.toFixed(2)}`;
}

function placeOrder() {
    const cart = getCart();
    
    if (cart.length === 0) {
        alert('Your cart is empty!');
        return;
    }
    
    const customerNameInput = document.getElementById('customer-name');
    let customerName = '';
    
    if (customerNameInput) {
        customerName = customerNameInput.value.trim();
        if (!customerName) {
            alert('Please enter your name!');
            customerNameInput.focus();
            return;
        }
    }
    
    const totals = calculateTotals();
    
    const orderItems = cart.map(item => ({
        id: item.id,
        name: item.name,
        price: item.price,
        quantity: item.quantity,
        total: item.price * item.quantity
    }));
    
    fetch('/place_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            customer_name: customerName || undefined,
            items: orderItems,
            subtotal: totals.subtotal,
            tax: totals.tax,
            total: totals.total
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.removeItem('cart');
            updateCartCount();
            
            window.location.href = `/bill/${data.order_id}`;
        } else {
            alert('Failed to place order. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('cart-items')) {
        renderCart();
        
        const placeOrderBtn = document.getElementById('place-order-btn');
        if (placeOrderBtn) {
            placeOrderBtn.addEventListener('click', placeOrder);
        }
    }
});
