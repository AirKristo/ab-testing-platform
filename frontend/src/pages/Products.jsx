/**
 * Products page — full catalog with category filter and search.
 */
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import ProductCard from '../components/ProductCard';

const CATEGORIES = [
  'All',
  'Electronics',
  'Clothing',
  'Home & Kitchen',
  'Books',
  'Sports & Outdoors',
  'Health & Beauty',
];

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const currentCategory = searchParams.get('category') || 'All';
  const currentPage = parseInt(searchParams.get('page') || '1');
  const perPage = 12;

  useEffect(() => {
    async function fetchProducts() {
      try {
        setLoading(true);
        let url = `/products?page=${currentPage}&per_page=${perPage}`;

        if (currentCategory !== 'All') {
          url += `&category=${encodeURIComponent(currentCategory)}`;
        }

        const response = await api.get(url);
        setProducts(response.data.products);
        setTotal(response.data.total);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchProducts();
  }, [currentCategory, currentPage]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setLoading(true);
      const response = await api.get(`/products/search?q=${encodeURIComponent(searchQuery)}`);
      setProducts(response.data.products);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = (category) => {
    setSearchQuery('');
    setSearchParams(category === 'All' ? {} : { category });
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Products</h1>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search products..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <button
            type="submit"
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Search
          </button>
        </div>
      </form>

      {/* Category filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {CATEGORIES.map(category => (
          <button
            key={category}
            onClick={() => handleCategoryChange(category)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              currentCategory === category
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {category}
          </button>
        ))}
      </div>

      {/* Results count */}
      <p className="text-sm text-gray-500 mb-4">{total} products</p>

      {/* Product grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(perPage)].map((_, i) => (
            <div key={i} className="bg-gray-100 rounded-lg h-64 animate-pulse" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <p className="text-gray-500 text-center py-12">No products found.</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {[...Array(totalPages)].map((_, i) => (
            <button
              key={i}
              onClick={() => setSearchParams({
                ...(currentCategory !== 'All' ? { category: currentCategory } : {}),
                page: String(i + 1),
              })}
              className={`w-8 h-8 rounded-md text-sm font-medium transition-colors ${
                currentPage === i + 1
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}