/**
 * Order history page.
 */
import { useState, useEffect } from 'react';
import api from '../api/client';
import { DEMO_USER_ID } from '../context/CartContext';

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchOrders() {
      try {
        const response = await api.get(`/orders/user/${DEMO_USER_ID}`);
        setOrders(response.data.orders);
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchOrders();
  }, []);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-32 bg-gray-200 rounded" />
          <div className="h-32 bg-gray-200 rounded" />
          <div className="h-32 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-4xl mb-4">📦</p>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">No orders yet</h1>
        <p className="text-sm text-gray-500">Your order history will appear here.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Order History</h1>

      <div className="space-y-4">
        {orders.map(order => (
          <div
            key={order.id}
            className="bg-white border border-gray-200 rounded-lg p-5"
          >
            <div className="flex justify-between items-start mb-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">Order #{order.id}</p>
                <p className="text-xs text-gray-500">
                  {new Date(order.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              <span className="text-lg font-bold text-gray-900">
                ${parseFloat(order.total_amount).toFixed(2)}
              </span>
            </div>

            <div className="space-y-1">
              {order.items.map(item => (
                <div key={item.id} className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    {item.product_name} × {item.quantity}
                  </span>
                  <span className="text-gray-500">
                    ${parseFloat(item.item_total).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}