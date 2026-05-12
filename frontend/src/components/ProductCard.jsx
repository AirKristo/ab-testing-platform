/**
 * Reusable product card for grid displays.
 */
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useState } from 'react';

export default function ProductCard({ product }) {
  const { addToCart } = useCart();
  const [added, setAdded] = useState(false);

  const handleAddToCart = async (e) => {
    e.preventDefault(); // Prevent navigation from Link wrapper
    const success = await addToCart(product.id);
    if (success) {
      setAdded(true);
      setTimeout(() => setAdded(false), 1500);
    }
  };

  return (
    <Link
      to={`/products/${product.id}`}
      className="group bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
    >
      {/* Product image placeholder */}
      <div className="aspect-square bg-gray-100 flex items-center justify-center p-6">
        <span className="text-3xl text-gray-400 group-hover:scale-110 transition-transform">
          🛍️
        </span>
      </div>

      <div className="p-4">
        <p className="text-xs text-indigo-600 font-medium uppercase tracking-wide mb-1">
          {product.category}
        </p>
        <h3 className="text-sm font-medium text-gray-900 mb-2 line-clamp-1">
          {product.name}
        </h3>
        <div className="flex items-center justify-between">
          <span className="text-lg font-semibold text-gray-900">
            ${parseFloat(product.price).toFixed(2)}
          </span>
          <button
            onClick={handleAddToCart}
            className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
              added
                ? 'bg-green-100 text-green-700'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            {added ? '✓ Added' : 'Add'}
          </button>
        </div>
      </div>
    </Link>
  );
}