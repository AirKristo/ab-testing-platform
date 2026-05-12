/**
 * Checkout page — review order and confirm purchase.
 */
import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';

export default function Checkout() {
  const { cart, fetchCart, checkout, loading } = useCart();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  const handleCheckout = async () => {
    setProcessing(true);
    const result = await checkout();
    if (result) {
      setOrder(result);
    }
    setProcessing(false);
  };

  // Order confirmation view
  if (order) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="text-5xl mb-4">🎉</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Order Confirmed!</h1>
        <p className="text-gray-500 mb-1">Order #{order.id}</p>
        <p className="text-lg font-semibold text-gray-900 mb-8">
          Total: ${parseFloat(order.total_amount).toFixed(2)}
        </p>

        <div className="bg-gray-50 rounded-lg p-6 mb-8 text-left">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Items Ordered</h2>
          <div className="space-y-2">
            {order.items.map(item => (
              <div key={item.id} className="flex justify-between text-sm">
                <span className="text-gray-600">
                  {item.product_name} × {item.quantity}
                </span>
                <span className="text-gray-900 font-medium">
                  ${parseFloat(item.item_total).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3 justify-center">
          <Link
            to="/products"
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Continue Shopping
          </Link>
          <Link
            to="/orders"
            className="bg-gray-100 text-gray-700 px-5 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
          >
            View Orders
          </Link>
        </div>
      </div>
    );
  }

  // Empty cart
  if (!loading && cart.items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-500 mb-4">Your cart is empty.</p>
        <Link
          to="/products"
          className="text-indigo-600 hover:text-indigo-700 text-sm font-medium"
        >
          ← Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Checkout</h1>

      {/* Order review */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Order Summary</h2>
        <div className="space-y-3">
          {cart.items.map(item => (
            <div key={item.id} className="flex justify-between text-sm">
              <span className="text-gray-600">
                {item.product_name} × {item.quantity}
              </span>
              <span className="text-gray-900 font-medium">
                ${parseFloat(item.item_total).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        <div className="border-t border-gray-200 mt-4 pt-4 flex justify-between">
          <span className="font-semibold text-gray-900">Total</span>
          <span className="text-xl font-bold text-gray-900">
            ${parseFloat(cart.cart_total).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Actions */}
      <button
        onClick={handleCheckout}
        disabled={processing}
        className={`w-full py-3 rounded-lg text-sm font-medium transition-colors ${
          processing
            ? 'bg-gray-400 text-white cursor-not-allowed'
            : 'bg-indigo-600 text-white hover:bg-indigo-700'
        }`}
      >
        {processing ? 'Processing...' : 'Place Order'}
      </button>

      <Link
        to="/cart"
        className="block text-center mt-3 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        ← Back to cart
      </Link>
    </div>
  );
}