/**
 * Product detail page with add-to-cart functionality.
 */
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { useCart } from '../context/CartContext';

export default function ProductDetail() {
  const { id } = useParams();
  const { addToCart } = useCart();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  useEffect(() => {
    async function fetchProduct() {
      try {
        setLoading(true);
        const response = await api.get(`/products/${id}`);
        setProduct(response.data);
      } catch (err) {
        setError(err.response?.status === 404 ? 'Product not found' : 'Failed to load product');
      } finally {
        setLoading(false);
      }
    }
    fetchProduct();
  }, [id]);

  const handleAddToCart = async () => {
    const success = await addToCart(product.id, quantity);
    if (success) {
      setAdded(true);
      setTimeout(() => setAdded(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="animate-pulse">
          <div className="h-6 w-32 bg-gray-200 rounded mb-8" />
          <div className="grid md:grid-cols-2 gap-8">
            <div className="aspect-square bg-gray-200 rounded-lg" />
            <div className="space-y-4">
              <div className="h-8 w-3/4 bg-gray-200 rounded" />
              <div className="h-6 w-1/4 bg-gray-200 rounded" />
              <div className="h-20 bg-gray-200 rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-gray-500 mb-4">{error}</p>
        <Link to="/products" className="text-indigo-600 hover:text-indigo-700 text-sm font-medium">
          ← Back to products
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-6">
        <Link to="/products" className="hover:text-indigo-600">Products</Link>
        <span className="mx-2">›</span>
        <span className="text-gray-900">{product.name}</span>
      </nav>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Image placeholder */}
        <div className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center">
          <span className="text-6xl">🛍️</span>
        </div>

        {/* Details */}
        <div>
          <p className="text-xs text-indigo-600 font-medium uppercase tracking-wide mb-2">
            {product.category}
          </p>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{product.name}</h1>
          <p className="text-3xl font-bold text-gray-900 mb-4">
            ${parseFloat(product.price).toFixed(2)}
          </p>

          {product.description && (
            <p className="text-sm text-gray-600 mb-6 leading-relaxed">
              {product.description}
            </p>
          )}

          {/* Quantity + Add to Cart */}
          <div className="flex items-center gap-3 mb-4">
            <label htmlFor="qty" className="text-sm text-gray-600">Qty:</label>
            <select
              id="qty"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value))}
              className="border border-gray-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {[...Array(10)].map((_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleAddToCart}
            className={`w-full py-2.5 rounded-lg text-sm font-medium transition-colors ${
              added
                ? 'bg-green-600 text-white'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            {added ? '✓ Added to Cart' : 'Add to Cart'}
          </button>
        </div>
      </div>
    </div>
  );
}