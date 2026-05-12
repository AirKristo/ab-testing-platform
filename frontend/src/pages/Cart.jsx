/**
 * Cart page — view items, update quantities, proceed to checkout.
 */
import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';

export default function Cart() {
  const { cart, loading, fetchCart, updateQuantity, removeItem } = useCart();
  const navigate = useNavigate();

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  if (loading && cart.items.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-32 bg-gray-200 rounded" />
          <div className="h-24 bg-gray-200 rounded" />
          <div className="h-24 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (cart.items.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-4xl mb-4">🛒</p>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">Your cart is empty</h1>
        <p className="text-sm text-gray-500 mb-6">Add some products to get started.</p>
        <Link
          to="/products"
          className="inline-block bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          Browse Products
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Cart ({cart.item_count} {cart.item_count === 1 ? 'item' : 'items'})
      </h1>

      {/* Cart items */}
      <div className="space-y-4 mb-8">
        {cart.items.map(item => (
          <div
            key={item.id}
            className="flex items-center gap-4 bg-white border border-gray-200 rounded-lg p-4"
          >
            {/* Product icon */}
            <div className="w-16 h-16 bg-gray-100 rounded-md flex items-center justify-center shrink-0">
              <span className="text-2xl">🛍️</span>
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <Link
                to={`/products/${item.product_id}`}
                className="text-sm font-medium text-gray-900 hover:text-indigo-600 transition-colors"
              >
                {item.product_name}
              </Link>
              <p className="text-sm text-gray-500">
                ${parseFloat(item.product_price).toFixed(2)} each
              </p>
            </div>

            {/* Quantity */}
            <select
              value={item.quantity}
              onChange={(e) => updateQuantity(item.id, parseInt(e.target.value))}
              className="border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {[...Array(20)].map((_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}</option>
              ))}
            </select>

            {/* Item total */}
            <span className="text-sm font-semibold text-gray-900 w-20 text-right">
              ${parseFloat(item.item_total).toFixed(2)}
            </span>

            {/* Remove */}
            <button
              onClick={() => removeItem(item.id)}
              className="text-gray-400 hover:text-red-500 transition-colors"
              title="Remove item"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none"
                viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="border-t border-gray-200 pt-6">
        <div className="flex justify-between items-center mb-6">
          <span className="text-lg font-semibold text-gray-900">Total</span>
          <span className="text-2xl font-bold text-gray-900">
            ${parseFloat(cart.cart_total).toFixed(2)}
          </span>
        </div>
        <button
          onClick={() => navigate('/checkout')}
          className="w-full bg-indigo-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          Proceed to Checkout
        </button>
      </div>
    </div>
  );
}