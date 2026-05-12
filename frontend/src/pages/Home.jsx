/**
 * Home page — featured products and hero section.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import ProductCard from '../components/ProductCard';

export default function Home() {
  const [featured, setFeatured] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchFeatured() {
      try {
        const response = await api.get('/products?per_page=8');
        setFeatured(response.data.products);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchFeatured();
  }, []);

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-indigo-50 to-white py-16 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            AB Store
          </h1>
          <p className="text-lg text-gray-500 mb-8 max-w-xl mx-auto">
            A demo e-commerce store powering a production-grade A/B testing platform.
            Every click generates experiment data.
          </p>
          <Link
            to="/products"
            className="inline-block bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Browse Products
          </Link>
        </div>
      </section>

      {/* Featured Products */}
      <section className="max-w-6xl mx-auto px-4 py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Featured Products</h2>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-gray-100 rounded-lg h-64 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {featured.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}