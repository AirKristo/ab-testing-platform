/**
 * Navigation bar with cart item count badge.
 */
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';

export default function Navbar() {
  const { cart } = useCart();

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="text-lg font-semibold text-gray-900 tracking-tight">
          AB Store
        </Link>

        <div className="flex items-center gap-6">
          <Link
            to="/products"
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            Products
          </Link>

          <Link
            to="/orders"
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            Orders
          </Link>

          <Link to="/cart" className="relative">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-gray-600 hover:text-gray-900 transition-colors"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"
              />
            </svg>
            {cart.item_count > 0 && (
              <span className="absolute -top-2 -right-2.5 bg-indigo-600 text-white text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center">
                {cart.item_count}
              </span>
            )}
          </Link>
        </div>
      </div>
    </nav>
  );
}